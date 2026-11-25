# Deploying OneCountry Fitness

Two supported setups:

- **One server with Docker** (below): database, API, web app and photos all on one VPS.
- **Render + Vercel + Neon**: free managed services, no server to look after.
  See [Render + Vercel + Neon](#render--vercel--neon).

The Docker setup runs as three containers:

| Service   | What it is                                   | Image              |
|-----------|----------------------------------------------|--------------------|
| `db`      | PostgreSQL 16 database                       | `postgres:16-alpine` |
| `backend` | FastAPI API (runs migrations on start)       | built from `backend/` |
| `web`     | Nginx serving the React app, proxying `/api` | built from `frontend/` |

Only `web` is exposed (port `APP_PORT`, default 8080). The database listens on
`127.0.0.1` only, so it can't be reached from outside the server.

## First deployment

Requirements: a Linux server with Docker Engine and the Compose plugin.

```bash
git clone <your repo> gym && cd gym
cp .env.example .env
```

Edit `.env` and set at least:

- `POSTGRES_PASSWORD`: a long random password
- `JWT_SECRET_KEY`: generate with `openssl rand -hex 32`
- `TIMEZONE`, `DEFAULT_CURRENCY` if you're not in India

Then start everything:

```bash
docker compose up -d --build
docker compose ps          # all three should say "healthy"
```

Open `http://<server>:8080`, create your trainer account, then lock sign-ups:

```bash
# in .env
ALLOW_TRAINER_REGISTRATION=false
docker compose up -d       # applies the change
```

Or create the account from the command line instead of the web page:

```bash
docker compose exec backend python -m app.cli create-trainer \
  --name "Your Name" --email you@example.com --password '<password>'
```

## HTTPS

Put HTTPS in front of port 8080 before using the app over the internet, since
logins and client details travel over this connection. Common options: Caddy or
Nginx with Let's Encrypt on the same server, or your cloud provider's load balancer.
A minimal Caddy setup is one line in a `Caddyfile`:

```
gym.example.com {
    reverse_proxy localhost:8080
}
```

## Updating

```bash
git pull
docker compose up -d --build
```

Database migrations run automatically when the backend starts.

## Data and backups

Two Docker volumes hold everything that matters:

- `gym_postgres_data`: the database
- `gym_uploads`: client profile and progress photos

Back up the database:

```bash
docker compose exec -T db pg_dump -U postgres gym_db | gzip > gym-$(date +%F).sql.gz
```

Restore it:

```bash
gunzip -c gym-YYYY-MM-DD.sql.gz | docker compose exec -T db psql -U postgres gym_db
```

Back up photos:

```bash
docker run --rm -v gym_uploads:/data -v "$PWD":/backup alpine tar czf /backup/uploads-$(date +%F).tgz -C /data .
```

## Useful commands

```bash
docker compose logs -f backend                         # API logs
docker compose exec backend python -m app.cli status   # system status
docker compose exec backend python -m app.cli reset-trainer-password \
  --email you@example.com --password '<new password>'  # forgotten password
```

## Render + Vercel + Neon

| Piece    | Service         | Holds                                              |
|----------|-----------------|----------------------------------------------------|
| Web app  | Vercel          | the React app; forwards `/api/*` to Render          |
| API      | Render (Docker) | FastAPI; runs migrations on every deploy            |
| Database | Neon            | all tables **and the photos** (`STORAGE_BACKEND=database`) |

Render's disk is wiped on every deploy, so photos are kept in the database instead of on
disk. Only signed-in users can load them: the API checks the login and streams each photo.

### 1. Neon (database)

1. Create a project in region **AWS Asia Pacific (Singapore)**, next to the API.
2. Copy the connection string with **"Connection pooling" turned off** (the host must *not*
   contain `-pooler`). The background job relies on a database lock the pooler doesn't keep.
   Paste it as-is, `?sslmode=require&channel_binding=require` included; the API handles it.

### 2. Render (API)

1. Render → **New** → **Blueprint** → choose this GitHub repo. It reads [`render.yaml`](render.yaml).
2. Paste the Neon connection string as `DATABASE_URL`. `JWT_SECRET_KEY` is generated for you.
3. Wait for the deploy, then open `https://<service>.onrender.com/health`; it should say `healthy`.
   Note the exact URL; Render adds a suffix if `onecountry-gym-api` is taken.

### 3. Vercel (web app)

1. If the Render URL is not `https://onecountry-gym-api.onrender.com`, change the `/api`
   rewrite in [`frontend/vercel.json`](frontend/vercel.json) to the real URL and push.
2. Vercel → **Add New Project** → import this repo → set **Root Directory** to `frontend`.
   Build settings come from `vercel.json`. No environment variables needed.
3. Open the Vercel URL, create your trainer account, then in Render set
   `ALLOW_TRAINER_REGISTRATION` to `false` (Render redeploys by itself).

### Space on Neon's free plan (500 MB)

Photos are resized before they are stored: profile photos to 800 px, progress photos to
1280 px, usually 50–250 KB each. That is room for a few thousand photos next to the tables.
The app sends the trainer an in-app alert at 80% and again at 95% full
(`DATABASE_SIZE_LIMIT_MB=500` in `render.yaml`). To free space, permanently delete archived
clients you no longer need (their photos go with them). If it still runs out, either upgrade
Neon or move new photos to a bucket (`STORAGE_BACKEND=s3`, see `.env.example`).

### Things to know on the free plans

- **Render free instances sleep after 15 minutes without traffic**; the next visit takes about
  a minute to wake up, and the first request can time out while it does. The hourly background
  job (monthly dues, absence and fee alerts) also only runs while it's awake; it catches up when
  the app is next opened. Render's Starter plan ($7/month) stays awake.
- Neon's free plan also pauses the database when idle; it wakes up again within a few seconds.

### Backups

Neon keeps a short restore history (point-in-time restore). For your own copy, which includes
the photos, run from any machine with the Postgres client:

```bash
pg_dump "<neon connection string>" | gzip > gym-$(date +%F).sql.gz
```

## Local development (without Docker for the app)

```bash
docker compose up -d db                       # just the database, on localhost:5433
cd backend && pip install -r requirements-dev.txt
uvicorn app.main:app --reload --port 8000     # reads DATABASE_URL from .env
cd frontend && npm install && npm run dev     # http://localhost:5173
pytest                                         # from backend/
```
