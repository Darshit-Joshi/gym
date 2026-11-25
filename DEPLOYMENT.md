# Deploying OneCountry Fitness

The app runs as three Docker containers:

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

## Local development (without Docker for the app)

```bash
docker compose up -d db                       # just the database, on localhost:5433
cd backend && pip install -r requirements-dev.txt
uvicorn app.main:app --reload --port 8000     # reads DATABASE_URL from .env
cd frontend && npm install && npm run dev     # http://localhost:5173
pytest                                         # from backend/
```
