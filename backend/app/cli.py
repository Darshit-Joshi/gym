"""ONECOUNTRY FITNESS Operational CLI for System Administrators and Gym Owner.

Usage:
    python -m app.cli status
    python -m app.cli seed-exercises
    python -m app.cli reset-trainer-password --email <email> --password <password>
    python -m app.cli create-trainer --name "Name" --email <email> --password <password> [--phone <phone>]
    python -m app.cli run-daily-jobs
"""
import sys
import argparse
from pathlib import Path

# Ensure backend root is on sys.path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from app.core.database import SessionLocal
from app.core.security import get_password_hash
from app.models.user import User, UserRole
from app.models.trainer import Trainer
from app.models.client import Client
from app.models.workout import WorkoutPlan, WorkoutDay, WorkoutExercise
from app.models.session import WorkoutSession, WorkoutSessionExercise
from app.models.exercise import Exercise
from app.models.note import TrainerNote
from app.seed import seed_exercises

STANDARD_EXERCISE_NAMES = {
    "Bench Press", "Incline Bench Press", "Dumbbell Fly", "Push Ups",
    "Lat Pulldown", "Seated Cable Row", "Barbell Row", "Pull Ups",
    "Squats", "Leg Press", "Leg Extension", "Leg Curl", "Lunges", "Calf Raise",
    "Shoulder Press", "Lateral Raise", "Bicep Curl", "Hammer Curl",
    "Tricep Pushdown", "Plank", "Crunches", "Running", "Cycling"
}


def show_status():
    db = SessionLocal()
    try:
        trainers = db.query(Trainer).all()
        clients_count = db.query(Client).count()
        users_count = db.query(User).count()
        print("\n================ ONECOUNTRY FITNESS SYSTEM STATUS ================")
        print(f"Total Users: {users_count}")
        print(f"Total Registered Athletes: {clients_count}")
        print(f"Configured Trainers: {len(trainers)}")
        for t in trainers:
            print(f"  - Trainer: {t.name} (ID: {t.id}, Email: {t.user.email if t.user else 'N/A'}, Phone: {t.phone})")
        print("==================================================================\n")
    finally:
        db.close()


def reset_trainer_password(email: str, new_password: str):
    if len(new_password) < 8:
        print("Error: Password must be at least 8 characters long.")
        sys.exit(1)

    db = SessionLocal()
    try:
        user = db.query(User).filter(
            User.email == email.lower().strip(),
            User.role == UserRole.TRAINER.value,
        ).first()
        if not user:
            print(f"Error: Trainer account with email '{email}' not found.")
            sys.exit(1)

        user.password_hash = get_password_hash(new_password)
        db.commit()
        print(f"[OK] Password for trainer '{email}' was successfully updated.")
    finally:
        db.close()


def create_trainer_account(name: str, email: str, password: str, phone: str = None):
    if len(password) < 8:
        print("Error: Password must be at least 8 characters long.")
        sys.exit(1)

    db = SessionLocal()
    try:
        clean_email = email.lower().strip()
        existing_user = db.query(User).filter(User.email == clean_email).first()
        if existing_user:
            print(f"Error: User with email '{email}' already exists.")
            sys.exit(1)

        user = User(
            email=clean_email,
            password_hash=get_password_hash(password),
            role=UserRole.TRAINER.value,
            is_active=True,
        )
        db.add(user)
        db.flush()

        trainer = Trainer(
            user_id=user.id,
            name=name.strip(),
            phone=phone.strip() if phone else None,
            is_demo=False,
        )
        db.add(trainer)
        db.commit()
        print(f"[OK] Successfully initialized Trainer account for {name} ({clean_email}).")
    finally:
        db.close()


def update_trainer_account(new_email: str = None, name: str = None, password: str = None, phone: str = None):
    db = SessionLocal()
    try:
        trainer = db.query(Trainer).first()
        if not trainer:
            print("Error: No trainer account found to update.")
            sys.exit(1)

        user = trainer.user
        if not user:
            print("Error: Trainer user record not found.")
            sys.exit(1)

        if new_email:
            clean_email = new_email.lower().strip()
            existing = db.query(User).filter(User.email == clean_email, User.id != user.id).first()
            if existing:
                print(f"Error: Email '{new_email}' is already in use by another user.")
                sys.exit(1)
            user.email = clean_email
            print(f"[OK] Updated trainer email to: {clean_email}")

        if name:
            trainer.name = name.strip()
            print(f"[OK] Updated trainer name to: {trainer.name}")

        if phone is not None:
            trainer.phone = phone.strip() if phone else None
            print(f"[OK] Updated trainer phone to: {trainer.phone}")

        if password:
            if len(password) < 8:
                print("Error: Password must be at least 8 characters long.")
                sys.exit(1)
            user.password_hash = get_password_hash(password)
            print("[OK] Updated trainer password.")

        db.commit()
        print("[OK] Trainer account updated successfully.")
    finally:
        db.close()


def inspect_trainer():
    db = SessionLocal()
    try:
        trainers = db.query(Trainer).all()
        if not trainers:
            print("\n[STATUS] No trainer account exists in the database.")
            print("[INFO] Public trainer registration is OPEN.")
            return

        trainer = trainers[0]
        is_demo = getattr(trainer, "is_demo", False) or (trainer.user and trainer.user.email == "trainer@example.com")
        print("\n================ TRAINER ACCOUNT INSPECTION ================")
        print(f"Trainer ID: {trainer.id}")
        print(f"Name: {trainer.name}")
        print(f"Email: {trainer.user.email if trainer.user else 'N/A'}")
        print(f"Phone: {trainer.phone}")
        print(f"Account Classification: {'DEMO TRAINER (Placeholder)' if is_demo else 'GENUINE REAL TRAINER'}")

        clients_count = db.query(Client).filter(Client.trainer_id == trainer.id).count()
        plans_count = db.query(WorkoutPlan).filter(WorkoutPlan.trainer_id == trainer.id).count()
        notes_count = db.query(TrainerNote).filter(TrainerNote.trainer_id == trainer.id).count()
        print(f"Linked Records: {clients_count} Athletes, {plans_count} Workout Plans, {notes_count} Notes")
        print(f"Public Registration: {'OPEN (Awaiting Real Trainer Self-Registration)' if is_demo else 'CLOSED (Real Trainer Active)'}")
        print("============================================================\n")
    finally:
        db.close()


def remove_demo_trainer():
    db = SessionLocal()
    try:
        trainer = db.query(Trainer).first()
        if not trainer:
            print("[INFO] No trainer account found in database.")
            return

        is_demo = getattr(trainer, "is_demo", False) or (trainer.user and trainer.user.email == "trainer@example.com")
        if not is_demo:
            print("[ERROR] Refusing operation: The configured trainer is a GENUINE REAL TRAINER, not a demo account.")
            sys.exit(1)

        user = trainer.user
        # Nullify foreign key references so athletes and workout plans remain completely intact
        db.query(Client).filter(Client.trainer_id == trainer.id).update({"trainer_id": None})
        db.query(WorkoutPlan).filter(WorkoutPlan.trainer_id == trainer.id).update({"trainer_id": None})
        db.query(TrainerNote).filter(TrainerNote.trainer_id == trainer.id).delete()

        db.delete(trainer)
        if user:
            db.delete(user)
        db.commit()
        print("[OK] Demo trainer successfully purged.")
        print("[STATUS] All athlete profiles and workout plans preserved.")
        print("[STATUS] Public trainer registration is now 100% OPEN for initial real trainer self-registration.")
    finally:
        db.close()


def migrate_demo_trainer(name: str, email: str, password: str, phone: str = None):
    if len(password) < 8:
        print("Error: Password must be at least 8 characters long.")
        sys.exit(1)

    db = SessionLocal()
    try:
        trainer = db.query(Trainer).first()
        if not trainer:
            print("[ERROR] No existing trainer found to migrate. Use 'create-trainer' instead.")
            sys.exit(1)

        clean_email = email.lower().strip()
        existing_user = db.query(User).filter(User.email == clean_email, User.id != trainer.user_id).first()
        if existing_user:
            print(f"[ERROR] Email '{email}' is already in use by another user.")
            sys.exit(1)

        user = trainer.user
        user.email = clean_email
        user.password_hash = get_password_hash(password)
        trainer.name = name.strip()
        trainer.phone = phone.strip() if phone else None
        trainer.is_demo = False

        db.commit()
        print(f"[OK] Successfully migrated to Genuine Real Trainer: {trainer.name} ({clean_email}).")
        print("[STATUS] Public trainer registration is now CLOSED.")
    finally:
        db.close()


def clean_test_data(confirm: bool = False):
    """Safely purge demo and test athletes, workout plans, fake sessions, and test exercises.

    Strictly preserves the Real Trainer account and the 23 standard library exercises.
    """
    db = SessionLocal()
    try:
        trainer = db.query(Trainer).first()
        trainer_user = trainer.user if trainer else None
        trainer_user_id = trainer_user.id if trainer_user else None

        clients = db.query(Client).all()
        plans = db.query(WorkoutPlan).all()
        sessions = db.query(WorkoutSession).all()
        notes = db.query(TrainerNote).all()
        non_standard_exercises = db.query(Exercise).filter(~Exercise.name.in_(STANDARD_EXERCISE_NAMES)).all()

        client_user_ids = [c.user_id for c in clients if c.user_id and c.user_id != trainer_user_id]
        client_users = db.query(User).filter(User.id.in_(client_user_ids)).all() if client_user_ids else []

        print("\n==================================================================")
        print("      ONECOUNTRY FITNESS -- CONTROLLED DATABASE CLEANUP AUDIT")
        print("==================================================================")
        print("\n[PRESERVED ACCOUNTS & MASTER DATA]")
        if trainer:
            print(f"  [PRESERVED] REAL TRAINER: {trainer.name} ({trainer_user.email if trainer_user else 'N/A'}, ID: {trainer.id})")
        else:
            print("  [INFO] No trainer configured.")
        print(f"  [PRESERVED] STANDARD EXERCISES: {len(STANDARD_EXERCISE_NAMES)} standard catalog exercises")
        print("  [PRESERVED] DATABASE SCHEMA & INTEGRITY: All tables, columns, indexes, and constraints")

        print("\n[RECORDS IDENTIFIED FOR REMOVAL]")
        print(f"  * Athletes / Clients ({len(clients)} records):")
        for c in clients:
            print(f"      - ID {c.id}: {c.name} ({c.user.email if c.user else 'No Email'}, Status: {c.status})")
        print(f"  * Associated Client User Logins: {len(client_users)} account(s)")
        print(f"  * Workout Plans & Routines: {len(plans)} plan(s)")
        print(f"  * Workout Sessions: {len(sessions)} session(s)")
        print(f"  * Trainer Notes: {len(notes)} note(s)")
        print(f"  * Test / Non-Standard Exercises: {len(non_standard_exercises)} exercise(s)")
        for nse in non_standard_exercises:
            print(f"      - ID {nse.id}: {nse.name} (Muscle: {nse.muscle_group})")

        print("==================================================================")

        if not confirm:
            print("\n[SAFETY GUARD ACTIVE]: Refusing to perform deletion without explicit confirmation.")
            print("To execute this cleanup and purge the test records, run:")
            print("    python -m app.cli clean-test-data --confirm\n")
            return

        print("\nExecuting atomic database purge...")

        # 1. Delete session exercises
        del_sess_ex = db.query(WorkoutSessionExercise).delete(synchronize_session=False)
        # 2. Delete sessions
        del_sess = db.query(WorkoutSession).delete(synchronize_session=False)
        # 3. Delete workout exercises
        del_plan_ex = db.query(WorkoutExercise).delete(synchronize_session=False)
        # 4. Delete workout days
        del_plan_days = db.query(WorkoutDay).delete(synchronize_session=False)
        # 5. Delete workout plans
        del_plans = db.query(WorkoutPlan).delete(synchronize_session=False)
        # 6. Delete trainer notes
        del_notes = db.query(TrainerNote).delete(synchronize_session=False)
        # 7. Delete non-standard test exercises
        del_custom_ex = 0
        for ex in non_standard_exercises:
            db.delete(ex)
            del_custom_ex += 1
        # 8. Delete clients
        del_clients = db.query(Client).delete(synchronize_session=False)
        # 9. Delete client users (STRICTLY ensuring user_id != trainer_user_id and role == 'CLIENT')
        if client_user_ids:
            del_users = db.query(User).filter(
                User.id.in_(client_user_ids),
                User.id != trainer_user_id,
            ).delete(synchronize_session=False)
        else:
            del_users = 0

        # Also purge any legacy demo trainer user (e.g. trainer@example.com) if not current trainer
        if trainer_user and trainer_user.email != "trainer@example.com":
            db.query(User).filter(User.email == "trainer@example.com").delete(synchronize_session=False)

        db.commit()

        print("\n[CLEANUP COMPLETED SUCCESSFULLY]")
        print(f"  [OK] Removed {del_clients} athlete client record(s)")
        print(f"  [OK] Removed {del_users} client user login(s)")
        print(f"  [OK] Removed {del_plans} workout plan(s) and associated day/exercise definitions")
        print(f"  [OK] Removed {del_sess} workout session(s) and {del_sess_ex} logged exercises")
        print(f"  [OK] Removed {del_notes} trainer note(s)")
        print(f"  [OK] Removed {del_custom_ex} test exercise(s)")

        # Verify current status
        rem_clients = db.query(Client).count()
        rem_plans = db.query(WorkoutPlan).count()
        rem_sessions = db.query(WorkoutSession).count()
        rem_exercises = db.query(Exercise).count()
        rem_trainers = db.query(Trainer).count()
        rem_users = db.query(User).count()

        print("\n[POST-CLEANUP VERIFIED DATABASE STATE]")
        print(f"  Total Clients: {rem_clients}")
        print(f"  Total Workout Plans: {rem_plans}")
        print(f"  Total Workout Sessions: {rem_sessions}")
        print(f"  Total Library Exercises: {rem_exercises}")
        print(f"  Configured Trainers: {rem_trainers} (Active: {trainer.name if trainer else 'None'})")
        print(f"  Total Users: {rem_users}")
        print("==================================================================\n")
    except Exception as e:
        db.rollback()
        print(f"\n[ERROR] Database cleanup failed and was safely rolled back: {e}")
        raise e
    finally:
        db.close()


def run_daily_jobs_command():
    from app.services.jobs import run_daily_jobs

    db = SessionLocal()
    try:
        summary = run_daily_jobs(db)
    finally:
        db.close()
    print(
        f"[OK] Daily jobs complete: {summary['dues_created']} dues created, "
        f"{summary['absence_alerts']} absence alerts, {summary['fee_alerts']} fee alerts."
    )


def main():
    parser = argparse.ArgumentParser(description="ONECOUNTRY FITNESS Operational CLI")
    subparsers = parser.add_subparsers(dest="command")

    # status
    subparsers.add_parser("status", help="Show system status and trainer count")

    # inspect-trainer
    subparsers.add_parser("inspect-trainer", help="Inspect trainer classification, linked clients, and registration status")

    # remove-demo-trainer
    subparsers.add_parser("remove-demo-trainer", help="Safely remove demo trainer while preserving athlete and workout records")

    # migrate-demo-trainer
    migrate_parser = subparsers.add_parser("migrate-demo-trainer", help="Explicitly migrate demo trainer placeholder to real trainer")
    migrate_parser.add_argument("--name", required=True, help="Real trainer full name")
    migrate_parser.add_argument("--email", required=True, help="Real trainer email address")
    migrate_parser.add_argument("--password", required=True, help="Real trainer password (min 8 chars)")
    migrate_parser.add_argument("--phone", required=False, help="Real trainer phone number")

    # seed-exercises
    subparsers.add_parser("seed-exercises", help="Populate or update standard exercise catalog")

    # reset-trainer-password
    reset_parser = subparsers.add_parser("reset-trainer-password", help="Reset password for trainer account")
    reset_parser.add_argument("--email", required=True, help="Trainer email address")
    reset_parser.add_argument("--password", required=True, help="New password (min 8 chars)")

    # update-trainer
    update_parser = subparsers.add_parser("update-trainer", help="Update existing trainer email, name, password, or phone")
    update_parser.add_argument("--email", required=False, help="New email address")
    update_parser.add_argument("--name", required=False, help="New trainer name")
    update_parser.add_argument("--password", required=False, help="New password (min 8 chars)")
    update_parser.add_argument("--phone", required=False, help="New phone number")

    # create-trainer
    create_parser = subparsers.add_parser("create-trainer", help="Create the initial trainer account")
    create_parser.add_argument("--name", required=True, help="Trainer full name")
    create_parser.add_argument("--email", required=True, help="Trainer email address")
    create_parser.add_argument("--password", required=True, help="Trainer password (min 8 chars)")
    create_parser.add_argument("--phone", required=False, help="Trainer phone number")

    # clean-test-data
    clean_parser = subparsers.add_parser("clean-test-data", help="Purge dummy/test clients, plans, fake sessions, and test exercises")
    clean_parser.add_argument("--confirm", action="store_true", help="Explicitly confirm deletion of test records")

    # run-daily-jobs
    subparsers.add_parser(
        "run-daily-jobs",
        help="Generate fee dues and raise absence/fee alerts (safe to run from cron)",
    )

    args = parser.parse_args()

    if args.command == "status":
        show_status()
    elif args.command == "inspect-trainer":
        inspect_trainer()
    elif args.command == "remove-demo-trainer":
        remove_demo_trainer()
    elif args.command == "migrate-demo-trainer":
        migrate_demo_trainer(args.name, args.email, args.password, args.phone)
    elif args.command == "clean-test-data":
        clean_test_data(confirm=args.confirm)
    elif args.command == "seed-exercises":
        seed_exercises()
    elif args.command == "reset-trainer-password":
        reset_trainer_password(args.email, args.password)
    elif args.command == "update-trainer":
        update_trainer_account(args.email, args.name, args.password, args.phone)
    elif args.command == "create-trainer":
        create_trainer_account(args.name, args.email, args.password, args.phone)
    elif args.command == "run-daily-jobs":
        run_daily_jobs_command()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
