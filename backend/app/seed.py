import sys
from datetime import date, timedelta
from pathlib import Path

# Add backend directory to path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from app.core.config import settings
from app.core.database import SessionLocal
from app.core.security import get_password_hash
from app.models.user import User, UserRole
from app.models.trainer import Trainer
from app.models.client import Client, ClientStatus, FitnessGoal
from app.models.exercise import Exercise, MuscleGroup
from app.models.workout import WorkoutPlan, WorkoutDay, WorkoutExercise
from app.models.session import WorkoutSession, WorkoutSessionExercise
from app.models.note import TrainerNote


def seed_exercises(db=None):
    """Safely seed the 23 standard library exercises without creating any demo users or sessions."""
    close_at_end = False
    if db is None:
        db = SessionLocal()
        close_at_end = True

    try:
        exercises_data = [
            # Chest
            ("Bench Press", MuscleGroup.CHEST.value, "Barbell", "Intermediate", "Barbell horizontal chest press"),
            ("Incline Bench Press", MuscleGroup.CHEST.value, "Barbell", "Intermediate", "Upper chest incline barbell or dumbbell press"),
            ("Dumbbell Fly", MuscleGroup.CHEST.value, "Dumbbell", "Beginner", "Isolated chest fly using dumbbells"),
            ("Push Ups", MuscleGroup.CHEST.value, "Bodyweight", "Beginner", "Bodyweight chest and tricep push"),
            # Back
            ("Lat Pulldown", MuscleGroup.BACK.value, "Cable", "Beginner", "Cable pulldown targeting latissimus dorsi"),
            ("Seated Cable Row", MuscleGroup.BACK.value, "Cable", "Beginner", "Horizontal cable pull for mid-back thickness"),
            ("Barbell Row", MuscleGroup.BACK.value, "Barbell", "Intermediate", "Bent over barbell row for back strength"),
            ("Pull Ups", MuscleGroup.BACK.value, "Bodyweight", "Advanced", "Bodyweight upper body pulling exercise"),
            # Legs
            ("Squats", MuscleGroup.LEGS.value, "Barbell", "Intermediate", "Barbell back or front squat targeting quads and glutes"),
            ("Leg Press", MuscleGroup.LEGS.value, "Machine", "Beginner", "Machine plate loaded leg press"),
            ("Leg Extension", MuscleGroup.LEGS.value, "Machine", "Beginner", "Isolated machine quad extension"),
            ("Leg Curl", MuscleGroup.LEGS.value, "Machine", "Beginner", "Isolated hamstring curl"),
            ("Lunges", MuscleGroup.LEGS.value, "Dumbbell", "Beginner", "Walking or stationary dumbbell lunges"),
            ("Calf Raise", MuscleGroup.LEGS.value, "Machine", "Beginner", "Standing or seated calf raises"),
            # Shoulders
            ("Shoulder Press", MuscleGroup.SHOULDERS.value, "Dumbbell", "Intermediate", "Overhead barbell or dumbbell press"),
            ("Lateral Raise", MuscleGroup.SHOULDERS.value, "Dumbbell", "Beginner", "Dumbbell lateral deltoid raises"),
            # Biceps
            ("Bicep Curl", MuscleGroup.BICEPS.value, "Dumbbell", "Beginner", "Standing dumbbell or barbell bicep curls"),
            ("Hammer Curl", MuscleGroup.BICEPS.value, "Dumbbell", "Beginner", "Neutral grip dumbbell curls targeting brachialis"),
            # Triceps
            ("Tricep Pushdown", MuscleGroup.TRICEPS.value, "Cable", "Beginner", "Cable pushdown using rope or straight bar"),
            # Core
            ("Plank", MuscleGroup.CORE.value, "Bodyweight", "Beginner", "Static core isometric hold"),
            ("Crunches", MuscleGroup.CORE.value, "Bodyweight", "Beginner", "Floor abdominal crunch"),
            # Cardio
            ("Running", MuscleGroup.CARDIO.value, "Cardio Machine", "Beginner", "Treadmill or outdoor steady-state running"),
            ("Cycling", MuscleGroup.CARDIO.value, "Cardio Machine", "Beginner", "Stationary spin bike or road cycling"),
        ]

        exercise_map = {}
        for name, group, eq, diff, desc in exercises_data:
            ex = db.query(Exercise).filter(Exercise.name == name).first()
            if not ex:
                ex = Exercise(name=name, muscle_group=group, equipment=eq, difficulty=diff, description=desc)
                db.add(ex)
                db.flush()
            else:
                ex.equipment = eq
                ex.difficulty = diff
                db.flush()
            exercise_map[name] = ex
        db.commit()
        print(f"[OK] Seeded {len(exercise_map)} exercises in library")
        return exercise_map
    except Exception as e:
        db.rollback()
        raise e
    finally:
        if close_at_end:
            db.close()


def seed_database(force: bool = False, db=None):
    if getattr(settings, "ENVIRONMENT", "development").lower() == "production" and not force:
        raise RuntimeError(
            "ACCIDENTAL DEMO SEED PREVENTED: Cannot seed demo data in a production environment. "
            "Use --exercises-only to populate the exercise catalog or --force-demo if strictly required."
        )

    close_at_end = False
    if db is None:
        db = SessionLocal()
        close_at_end = True
    print("Starting database seed...")

    try:
        # 1. Create or get Trainer
        trainer_user = db.query(User).filter(User.email == "trainer@example.com").first()
        if not trainer_user:
            trainer_user = User(
                email="trainer@example.com",
                password_hash=get_password_hash("ChangeMe123!"),
                role=UserRole.TRAINER.value,
                is_active=True,
            )
            db.add(trainer_user)
            db.flush()

            trainer = Trainer(
                user_id=trainer_user.id,
                name="Demo Trainer",
                phone="+1-555-0100",
                profile_image=None,
                is_demo=True,
            )
            db.add(trainer)
            db.flush()
            print("[OK] Created Demo Trainer (trainer@example.com / ChangeMe123!)")
        else:
            trainer = db.query(Trainer).filter(Trainer.user_id == trainer_user.id).first()
            print("[*] Demo Trainer already exists")

        # 2. Seed Common Exercises (library items)
        exercise_map = seed_exercises(db)

        # 3. Seed Demo Clients
        clients_data = [
            {
                "name": "Rahul Sharma",
                "email": "rahul@example.com",
                "phone": "9876543210",
                "password": "Client123!",
                "age": 24,
                "gender": "Male",
                "height": 178.0,
                "current_weight": 78.0,
                "goal": FitnessGoal.MUSCLE_GAIN.value,
            },
            {
                "name": "Priya Sharma",
                "email": "priya@example.com",
                "phone": "9876543211",
                "password": "Client123!",
                "age": 27,
                "gender": "Female",
                "height": 165.0,
                "current_weight": 62.0,
                "goal": FitnessGoal.WEIGHT_LOSS.value,
            },
            {
                "name": "Aman Verma",
                "email": "aman@example.com",
                "phone": "9876543212",
                "password": "Client123!",
                "age": 29,
                "gender": "Male",
                "height": 182.0,
                "current_weight": 84.0,
                "goal": FitnessGoal.STRENGTH.value,
            },
        ]

        seeded_clients = {}
        for cd in clients_data:
            user = db.query(User).filter(User.email == cd["email"]).first()
            if not user:
                user = User(
                    email=cd["email"],
                    password_hash=get_password_hash(cd["password"]),
                    role=UserRole.CLIENT.value,
                    is_active=True,
                )
                db.add(user)
                db.flush()

                client = Client(
                    user_id=user.id,
                    trainer_id=trainer.id,
                    name=cd["name"],
                    phone=cd["phone"],
                    age=cd["age"],
                    gender=cd["gender"],
                    height=cd["height"],
                    current_weight=cd["current_weight"],
                    fitness_goal=cd["goal"],
                    status=ClientStatus.ACTIVE.value,
                )
                db.add(client)
                db.flush()
                seeded_clients[cd["email"]] = client
                print(f"[OK] Created Client: {cd['name']} ({cd['email']} / {cd['password']})")
            else:
                client = db.query(Client).filter(Client.user_id == user.id).first()
                seeded_clients[cd["email"]] = client
                print(f"[*] Client already exists: {cd['name']}")

        # 4. Create Workout Plans for Clients
        rahul = seeded_clients["rahul@example.com"]
        if not db.query(WorkoutPlan).filter(WorkoutPlan.client_id == rahul.id).first():
            plan_rahul = WorkoutPlan(
                name="Muscle Gain — 5 Day Split",
                description="Hypertrophy split targeting all major muscle groups",
                client_id=rahul.id,
                trainer_id=trainer.id,
                start_date=date.today() - timedelta(days=14),
                is_active=True,
            )
            db.add(plan_rahul)
            db.flush()

            # Monday: Chest + Triceps
            day1 = WorkoutDay(workout_plan_id=plan_rahul.id, day_name="Chest + Triceps", day_order=1)
            db.add(day1)
            db.flush()
            db.add(WorkoutExercise(workout_day_id=day1.id, exercise_id=exercise_map["Bench Press"].id, sets=4, reps=10, weight=60.0, rest_seconds=90, instructions="Keep controlled tempo", order_index=1))
            db.add(WorkoutExercise(workout_day_id=day1.id, exercise_id=exercise_map["Incline Bench Press"].id, sets=3, reps=12, weight=22.0, rest_seconds=60, instructions="Full stretch at bottom", order_index=2))
            db.add(WorkoutExercise(workout_day_id=day1.id, exercise_id=exercise_map["Dumbbell Fly"].id, sets=3, reps=15, weight=14.0, rest_seconds=60, instructions="Focus on contraction", order_index=3))
            db.add(WorkoutExercise(workout_day_id=day1.id, exercise_id=exercise_map["Tricep Pushdown"].id, sets=4, reps=12, weight=25.0, rest_seconds=60, instructions="Keep elbows pinned to sides", order_index=4))

            # Tuesday: Back + Biceps
            day2 = WorkoutDay(workout_plan_id=plan_rahul.id, day_name="Back + Biceps", day_order=2)
            db.add(day2)
            db.flush()
            db.add(WorkoutExercise(workout_day_id=day2.id, exercise_id=exercise_map["Lat Pulldown"].id, sets=4, reps=10, weight=55.0, rest_seconds=90, instructions="Pull to upper chest", order_index=1))
            db.add(WorkoutExercise(workout_day_id=day2.id, exercise_id=exercise_map["Barbell Row"].id, sets=4, reps=8, weight=50.0, rest_seconds=90, instructions="Flat back posture", order_index=2))
            db.add(WorkoutExercise(workout_day_id=day2.id, exercise_id=exercise_map["Bicep Curl"].id, sets=3, reps=12, weight=12.5, rest_seconds=60, instructions="No swinging", order_index=3))
            db.add(WorkoutExercise(workout_day_id=day2.id, exercise_id=exercise_map["Hammer Curl"].id, sets=3, reps=12, weight=12.5, rest_seconds=60, instructions="Forearm focus", order_index=4))

            # Wednesday: Rest
            day3 = WorkoutDay(workout_plan_id=plan_rahul.id, day_name="Rest Day", day_order=3, is_rest_day=True)
            db.add(day3)

            # Thursday: Legs
            day4 = WorkoutDay(workout_plan_id=plan_rahul.id, day_name="Legs", day_order=4)
            db.add(day4)
            db.flush()
            db.add(WorkoutExercise(workout_day_id=day4.id, exercise_id=exercise_map["Squats"].id, sets=4, reps=8, weight=80.0, rest_seconds=120, instructions="Deep squat below parallel", order_index=1))
            db.add(WorkoutExercise(workout_day_id=day4.id, exercise_id=exercise_map["Leg Press"].id, sets=3, reps=12, weight=140.0, rest_seconds=90, instructions="Controlled descent", order_index=2))
            db.add(WorkoutExercise(workout_day_id=day4.id, exercise_id=exercise_map["Leg Extension"].id, sets=3, reps=15, weight=40.0, rest_seconds=60, instructions="Squeeze at top", order_index=3))
            db.add(WorkoutExercise(workout_day_id=day4.id, exercise_id=exercise_map["Calf Raise"].id, sets=4, reps=20, weight=50.0, rest_seconds=45, instructions="Full extension", order_index=4))

            # Friday: Shoulders + Core
            day5 = WorkoutDay(workout_plan_id=plan_rahul.id, day_name="Shoulders + Core", day_order=5)
            db.add(day5)
            db.flush()
            db.add(WorkoutExercise(workout_day_id=day5.id, exercise_id=exercise_map["Shoulder Press"].id, sets=4, reps=10, weight=20.0, rest_seconds=90, instructions="Strict overhead press", order_index=1))
            db.add(WorkoutExercise(workout_day_id=day5.id, exercise_id=exercise_map["Lateral Raise"].id, sets=4, reps=15, weight=8.0, rest_seconds=60, instructions="Slight lean forward", order_index=2))
            db.add(WorkoutExercise(workout_day_id=day5.id, exercise_id=exercise_map["Plank"].id, sets=3, reps=60, weight=0.0, rest_seconds=60, instructions="Hold for 60 seconds", order_index=3))
            db.add(WorkoutExercise(workout_day_id=day5.id, exercise_id=exercise_map["Crunches"].id, sets=3, reps=25, weight=0.0, rest_seconds=45, instructions="Exhale on contraction", order_index=4))

            print("[OK] Assigned 5-Day Workout Plan to Rahul Sharma")

        # 5. Priya's Workout Plan
        priya = seeded_clients["priya@example.com"]
        if not db.query(WorkoutPlan).filter(WorkoutPlan.client_id == priya.id).first():
            plan_priya = WorkoutPlan(
                name="Weight Loss & Conditioning",
                description="High intensity circuit & resistance training",
                client_id=priya.id,
                trainer_id=trainer.id,
                start_date=date.today() - timedelta(days=10),
                is_active=True,
            )
            db.add(plan_priya)
            db.flush()
            p_day1 = WorkoutDay(workout_plan_id=plan_priya.id, day_name="Full Body HIIT", day_order=1)
            db.add(p_day1)
            db.flush()
            db.add(WorkoutExercise(workout_day_id=p_day1.id, exercise_id=exercise_map["Push Ups"].id, sets=3, reps=12, rest_seconds=45, instructions="Bodyweight form", order_index=1))
            db.add(WorkoutExercise(workout_day_id=p_day1.id, exercise_id=exercise_map["Lunges"].id, sets=3, reps=15, weight=8.0, rest_seconds=45, instructions="Walking lunges", order_index=2))
            db.add(WorkoutExercise(workout_day_id=p_day1.id, exercise_id=exercise_map["Running"].id, sets=1, reps=20, rest_seconds=60, instructions="20 minutes interval run", order_index=3))
            print("[OK] Assigned Conditioning Plan to Priya Sharma")

        # 6. Aman's Workout Plan
        aman = seeded_clients["aman@example.com"]
        if not db.query(WorkoutPlan).filter(WorkoutPlan.client_id == aman.id).first():
            plan_aman = WorkoutPlan(
                name="Strength Mastery",
                description="Heavy compound lifts focusing on strength progression",
                client_id=aman.id,
                trainer_id=trainer.id,
                start_date=date.today() - timedelta(days=20),
                is_active=True,
            )
            db.add(plan_aman)
            db.flush()
            a_day1 = WorkoutDay(workout_plan_id=plan_aman.id, day_name="Back + Biceps", day_order=1)
            db.add(a_day1)
            db.flush()
            db.add(WorkoutExercise(workout_day_id=a_day1.id, exercise_id=exercise_map["Barbell Row"].id, sets=5, reps=5, weight=75.0, rest_seconds=120, instructions="Explosive pull", order_index=1))
            db.add(WorkoutExercise(workout_day_id=a_day1.id, exercise_id=exercise_map["Pull Ups"].id, sets=4, reps=8, weight=0.0, rest_seconds=90, instructions="Dead hang to chin over bar", order_index=2))
            print("[OK] Assigned Strength Plan to Aman Verma")

        # 7. Seed Daily Workout Sessions
        today = date.today()
        # Today's session for Rahul
        if not db.query(WorkoutSession).filter(WorkoutSession.client_id == rahul.id, WorkoutSession.date == today).first():
            sess_rahul = WorkoutSession(
                client_id=rahul.id,
                trainer_id=trainer.id,
                workout_name="Chest + Triceps",
                date=today,
                duration_minutes=60,
                notes="Good performance today. High energy throughout.",
                status="COMPLETED",
            )
            db.add(sess_rahul)
            db.flush()
            db.add(WorkoutSessionExercise(session_id=sess_rahul.id, exercise_id=exercise_map["Bench Press"].id, sets_completed=4, reps=10, weight_used=60.0, notes="Smooth bar path"))
            db.add(WorkoutSessionExercise(session_id=sess_rahul.id, exercise_id=exercise_map["Incline Bench Press"].id, sets_completed=3, reps=12, weight_used=22.0, notes="Increased reps on last set"))
            db.add(WorkoutSessionExercise(session_id=sess_rahul.id, exercise_id=exercise_map["Dumbbell Fly"].id, sets_completed=3, reps=15, weight_used=14.0, notes="Strict form"))
            db.add(WorkoutSessionExercise(session_id=sess_rahul.id, exercise_id=exercise_map["Tricep Pushdown"].id, sets_completed=4, reps=12, weight_used=25.0, notes="Strong tricep burnout"))

            # Yesterday session for Rahul
            sess_rahul_prev = WorkoutSession(
                client_id=rahul.id,
                trainer_id=trainer.id,
                workout_name="Back + Biceps",
                date=today - timedelta(days=1),
                duration_minutes=65,
                notes="Great lat activation. Biceps fatigued well.",
                status="COMPLETED",
            )
            db.add(sess_rahul_prev)
            db.flush()
            db.add(WorkoutSessionExercise(session_id=sess_rahul_prev.id, exercise_id=exercise_map["Lat Pulldown"].id, sets_completed=4, reps=10, weight_used=55.0))
            db.add(WorkoutSessionExercise(session_id=sess_rahul_prev.id, exercise_id=exercise_map["Barbell Row"].id, sets_completed=4, reps=8, weight_used=50.0))

            print("[OK] Seeded workout sessions for Rahul Sharma")

        # Today's session for Priya
        if not db.query(WorkoutSession).filter(WorkoutSession.client_id == priya.id, WorkoutSession.date == today).first():
            sess_priya = WorkoutSession(
                client_id=priya.id,
                trainer_id=trainer.id,
                workout_name="Legs & Cardio",
                date=today,
                duration_minutes=50,
                notes="Crushed cardio intervals today.",
                status="COMPLETED",
            )
            db.add(sess_priya)
            db.flush()
            db.add(WorkoutSessionExercise(session_id=sess_priya.id, exercise_id=exercise_map["Lunges"].id, sets_completed=3, reps=15, weight_used=8.0))
            db.add(WorkoutSessionExercise(session_id=sess_priya.id, exercise_id=exercise_map["Running"].id, sets_completed=1, reps=20, notes="Interval sprint finish"))
            print("[OK] Seeded today's workout session for Priya Sharma")

        # Today's session for Aman
        if not db.query(WorkoutSession).filter(WorkoutSession.client_id == aman.id, WorkoutSession.date == today).first():
            sess_aman = WorkoutSession(
                client_id=aman.id,
                trainer_id=trainer.id,
                workout_name="Back + Biceps",
                date=today,
                duration_minutes=65,
                notes="Heavy deadlifts and pull ups.",
                status="COMPLETED",
            )
            db.add(sess_aman)
            db.flush()
            db.add(WorkoutSessionExercise(session_id=sess_aman.id, exercise_id=exercise_map["Barbell Row"].id, sets_completed=5, reps=5, weight_used=75.0))
            print("[OK] Seeded today's workout session for Aman Verma")

        # 8. Seed Trainer Notes
        notes_to_seed = [
            (rahul.id, "Good performance today. Increase bench press weight next week."),
            (rahul.id, "Target 80kg bodyweight by end of month. Maintain protein intake at 160g."),
            (priya.id, "Great stamina improvement on treadmill intervals. Keep hydration up."),
            (aman.id, "Squat depth is consistent now. We will try for a PR next session."),
        ]
        for cid, note_text in notes_to_seed:
            existing_note = db.query(TrainerNote).filter(TrainerNote.client_id == cid, TrainerNote.note == note_text).first()
            if not existing_note:
                tn = TrainerNote(client_id=cid, trainer_id=trainer.id, note=note_text)
                db.add(tn)
        print("[OK] Seeded trainer notes for clients")

        db.commit()
        print("\nDatabase seed completed successfully!")
    except Exception as e:
        db.rollback()
        print(f"Error seeding database: {e}")
        raise
    finally:
        if close_at_end:
            db.close()


if __name__ == "__main__":
    if "--force-demo" in sys.argv:
        print("Explicit demo seeding requested via --force-demo...")
        seed_database(force=True)
    else:
        print("Default seed execution: populating standard exercise library catalog only.")
        seed_exercises()
