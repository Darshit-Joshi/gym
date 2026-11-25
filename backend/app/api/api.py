from fastapi import APIRouter
from app.api.endpoints import (
    auth,
    clients,
    exercises,
    sessions,
    notes,
    dashboard,
    attendance,
    fees,
    notifications,
    progress_photos,
)

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(clients.router, prefix="/clients", tags=["Clients"])
api_router.include_router(exercises.router, prefix="/exercises", tags=["Exercises"])
api_router.include_router(sessions.router, prefix="/sessions", tags=["Exercise Log"])
api_router.include_router(notes.router, prefix="/notes", tags=["Trainer Notes"])
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["Dashboard"])
api_router.include_router(attendance.router, prefix="/attendance", tags=["Attendance"])
api_router.include_router(fees.router, prefix="/fees", tags=["Fees & Memberships"])
api_router.include_router(notifications.router, prefix="/notifications", tags=["Notifications"])
api_router.include_router(progress_photos.router, prefix="/progress-photos", tags=["Progress Photos"])
