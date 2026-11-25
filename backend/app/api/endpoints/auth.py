import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.api.deps import get_db, get_current_user
from app.core.config import settings
from app.core.security import verify_password, create_access_token, get_password_hash
from app.models.user import User, UserRole
from app.models.trainer import Trainer
from app.schemas.auth import (
    LoginRequest,
    TokenResponse,
    ChangePasswordRequest,
    RegisterTrainerRequest,
    SetupStatusResponse,
    UpdateProfileRequest,
    ResetTrainerPasswordRequest,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/login", response_model=TokenResponse)
def login(login_data: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == login_data.email.lower().strip()).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    if not verify_password(login_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    if user.role != UserRole.TRAINER.value:
        # Client records exist for record keeping only; only the trainer signs in.
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the trainer account can sign in.",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive.",
        )

    token = create_access_token(subject=user.id, role=user.role)

    name = "User"
    trainer_id = None
    client_id = None
    trainer = db.query(Trainer).filter(Trainer.user_id == user.id).first()
    if trainer:
        name = trainer.name
        trainer_id = trainer.id

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        role=user.role,
        user_id=user.id,
        name=name,
        trainer_id=trainer_id,
        client_id=client_id,
    )


@router.get("/me")
def get_current_user_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    profile = {
        "id": current_user.id,
        "email": current_user.email,
        "role": current_user.role,
        "is_active": current_user.is_active,
    }
    if current_user.role == UserRole.TRAINER.value:
        trainer = db.query(Trainer).filter(Trainer.user_id == current_user.id).first()
        if trainer:
            profile.update({
                "trainer_id": trainer.id,
                "name": trainer.name,
                "phone": trainer.phone,
                "profile_image": trainer.profile_image,
            })
    return profile


@router.post("/logout")
def logout():
    return {"message": "Successfully logged out"}


@router.post("/change-password")
def change_password(
    data: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not verify_password(data.current_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password does not match",
        )
    if len(data.new_password) < 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be at least 6 characters long",
        )
    current_user.password_hash = get_password_hash(data.new_password)
    db.commit()
    return {"message": "Password changed successfully"}


def is_demo_trainer(trainer: Trainer) -> bool:
    if not trainer:
        return False
    return bool(getattr(trainer, "is_demo", False))


@router.get("/setup-status", response_model=SetupStatusResponse)
def get_setup_status(db: Session = Depends(get_db)):
    trainers = db.query(Trainer).all()
    has_real_trainer = any(not is_demo_trainer(t) for t in trainers)

    return SetupStatusResponse(
        is_setup_completed=has_real_trainer,
        has_trainer=has_real_trainer,
        can_register_trainer=settings.ALLOW_TRAINER_REGISTRATION,
    )


@router.post(
    "/register-trainer",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a trainer account",
)
@router.post(
    "/setup-trainer",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    include_in_schema=False,
)
def register_trainer(data: RegisterTrainerRequest, db: Session = Depends(get_db)):
    if not settings.ALLOW_TRAINER_REGISTRATION:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="New trainer sign-ups are closed. Ask the administrator for access.",
        )
    trainers = db.query(Trainer).all()

    # Check for duplicate email
    clean_email = data.email.lower().strip()
    existing_user = db.query(User).filter(User.email == clean_email).first()

    demo_trainer = next((t for t in trainers if is_demo_trainer(t)), None)

    # If email is already taken by a different user, reject
    if existing_user and (not demo_trainer or existing_user.id != demo_trainer.user_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email address already exists. Please choose a different email or sign in.",
        )

    # Handle demo trainer migration vs fresh creation
    if demo_trainer:
        # Safely migrate existing demo trainer placeholder to real trainer
        user = demo_trainer.user
        user.email = clean_email
        user.password_hash = get_password_hash(data.password)
        user.is_active = True
        user.activation_token = None
        user.activation_expires = None

        demo_trainer.name = data.name.strip()
        demo_trainer.phone = data.phone.strip() if data.phone else None
        demo_trainer.is_demo = False

        db.commit()
        db.refresh(demo_trainer)
        trainer = demo_trainer
        logger.info(f"Successfully migrated demo trainer placeholder to real trainer: {clean_email}")
    else:
        # Create fresh user and trainer
        user = User(
            email=clean_email,
            password_hash=get_password_hash(data.password),
            role=UserRole.TRAINER.value,
            is_active=True,
        )
        db.add(user)
        db.flush()

        trainer = Trainer(
            user_id=user.id,
            name=data.name.strip(),
            phone=data.phone.strip() if data.phone else None,
            is_demo=False,
        )
        db.add(trainer)
        try:
            db.commit()
            db.refresh(trainer)
        except IntegrityError:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="An account with this email address already exists.",
            )

    token = create_access_token(subject=user.id, role=user.role)
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        role=user.role,
        user_id=user.id,
        name=trainer.name,
        trainer_id=trainer.id,
        client_id=None,
    )


@router.put("/profile")
def update_profile(
    data: UpdateProfileRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.role == UserRole.TRAINER.value:
        trainer = db.query(Trainer).filter(Trainer.user_id == current_user.id).first()
        if not trainer:
            raise HTTPException(status_code=404, detail="Trainer profile not found")
        if data.name is not None:
            trainer.name = data.name.strip()
        if data.phone is not None:
            trainer.phone = data.phone.strip()
        if data.profile_image is not None:
            trainer.profile_image = data.profile_image
        db.commit()
        db.refresh(trainer)
        return {
            "message": "Profile updated successfully",
            "name": trainer.name,
            "phone": trainer.phone,
            "profile_image": trainer.profile_image,
        }
    return {"message": "Profile updated"}


@router.post("/reset-trainer-password")
def reset_trainer_password(
    data: ResetTrainerPasswordRequest,
    db: Session = Depends(get_db),
):
    if not settings.ADMIN_RECOVERY_KEY or data.recovery_key.strip() != settings.ADMIN_RECOVERY_KEY.strip():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid administrative recovery key.",
        )

    user = db.query(User).filter(
        User.email == data.email.lower().strip(),
        User.role == UserRole.TRAINER.value,
    ).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Trainer account not found with this email.",
        )

    user.password_hash = get_password_hash(data.new_password)
    db.commit()
    return {"message": "Trainer password reset successfully."}
