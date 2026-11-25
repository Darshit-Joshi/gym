import secrets
from datetime import date
from typing import List, Optional, Union
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, status
from fastapi.responses import Response
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from app.api.deps import (
    get_db,
    get_current_user,
    get_current_user_with_media_token,
    get_current_trainer,
    verify_client_access,
)
from app.core.security import get_password_hash
from app.core.timezone import today_gym
from app.models.billing import FeeRecord, FeeStatus
from app.services.billing import ZERO, compute_fee_status, outstanding, unpaid_clause
from app.services.trainer_settings import get_or_create_settings
from app.services.storage import (
    validate_and_save_image,
    read_image,
    delete_secure_file,
)
from app.models.user import User, UserRole
from app.models.client import Client, ClientStatus, NO_LOGIN_EMAIL_DOMAIN
from app.schemas.client import (
    ClientListItem,
    ClientCreate,
    ClientUpdate,
    ClientResponse,
    PaginatedClientResponse,
)

router = APIRouter()

EDITABLE_STATUSES = {ClientStatus.ACTIVE.value, ClientStatus.INACTIVE.value, ClientStatus.ARCHIVED.value}
# Columns that may be cleared, but never set to null
NOT_NULLABLE = {"name", "status"}


def _age_on(dob: date, today: date) -> int:
    return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))


def _get_trainer_client(db: Session, client_id: int, trainer_id: int) -> Client:
    client = db.query(Client).filter(Client.id == client_id, Client.trainer_id == trainer_id).first()
    if not client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Client with id {client_id} not found",
        )
    return client


@router.get("", response_model=Union[PaginatedClientResponse, List[ClientResponse]])
def get_clients(
    search: Optional[str] = Query(None, description="Search by name, email, or phone"),
    status: Optional[str] = Query(None, description="Filter by status (Active, Inactive, Archived), or 'current' for everyone not archived"),
    goal: Optional[str] = Query(None, description="Filter by fitness goal"),
    page: Optional[int] = Query(None, ge=1, description="Page number for pagination"),
    page_size: Optional[int] = Query(None, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db),
    trainer_data=Depends(get_current_trainer),
):
    _, trainer = trainer_data
    query = (
        db.query(Client)
        .join(User, Client.user_id == User.id)
        .filter(Client.trainer_id == trainer.id)
    )

    if status and status.lower() == "current":
        query = query.filter(Client.status != ClientStatus.ARCHIVED.value)
    elif status and status.lower() != "all":
        query = query.filter(Client.status.ilike(status))

    if goal and goal.lower() != "all":
        query = query.filter(Client.fitness_goal.ilike(goal))

    if search:
        search_pattern = f"%{search.strip()}%"
        query = query.filter(
            or_(
                Client.name.ilike(search_pattern),
                Client.phone.ilike(search_pattern),
                # Never match the hidden placeholder emails of clients added without one
                and_(
                    User.email.ilike(search_pattern),
                    ~User.email.ilike(f"%@{NO_LOGIN_EMAIL_DOMAIN}"),
                ),
            )
        )

    query = query.order_by(Client.created_at.desc())

    if page is None:
        # Unpaginated mode (backward compatible)
        return [ClientResponse.model_validate(c) for c in query.all()]

    limit = page_size or 20
    total = query.count()
    clients = query.offset((page - 1) * limit).limit(limit).all()
    return PaginatedClientResponse(
        items=_with_payment_status(db, trainer.id, clients),
        total=total,
        page=page,
        page_size=limit,
        total_pages=(total + limit - 1) // limit if total > 0 else 1,
    )


def _with_payment_status(db: Session, trainer_id: int, clients: List[Client]) -> List[ClientListItem]:
    """Adds each client's fee standing, with one query for the whole page."""
    ids = [c.id for c in clients]
    unpaid = (
        db.query(FeeRecord).filter(FeeRecord.client_id.in_(ids), unpaid_clause()).all() if ids else []
    )
    billed_ids = (
        {cid for (cid,) in db.query(FeeRecord.client_id).filter(FeeRecord.client_id.in_(ids)).distinct()} if ids else set()
    )
    grace = get_or_create_settings(db, trainer_id).fee_grace_days
    today = today_gym()
    by_client = {}
    for fee in unpaid:
        by_client.setdefault(fee.client_id, []).append(fee)

    items = []
    for c in clients:
        fees = by_client.get(c.id, [])
        statuses = {compute_fee_status(f, today, grace) for f in fees}
        if FeeStatus.OVERDUE in statuses:
            pay = "OVERDUE"
        elif statuses & {FeeStatus.PENDING, FeeStatus.PARTIAL}:
            pay = "DUE"
        elif c.membership_plan_id or c.id in billed_ids:
            pay = "CLEAR"
        else:
            pay = "NO_PLAN"
        item = ClientListItem.model_validate(c)
        item.payment_status = pay
        item.outstanding_amount = float(sum((outstanding(f) for f in fees), ZERO))
        items.append(item)
    return items


@router.post("", response_model=ClientResponse, status_code=status.HTTP_201_CREATED)
def create_client(
    client_in: ClientCreate,
    db: Session = Depends(get_db),
    trainer_data=Depends(get_current_trainer),
):
    _, trainer = trainer_data

    if client_in.email:
        email = client_in.email.lower().strip()
        if db.query(User.id).filter(User.email == email).first():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A client with this email address already exists",
            )
    else:
        email = f"client-{secrets.token_hex(8)}@{NO_LOGIN_EMAIL_DOMAIN}"

    # Clients don't sign in: the user row only stores the email, with an unusable password.
    user = User(
        email=email,
        password_hash=get_password_hash(secrets.token_hex(24)),
        role=UserRole.CLIENT.value,
        is_active=False,
    )
    db.add(user)
    db.flush()

    age = client_in.age
    if client_in.date_of_birth and not age:
        age = _age_on(client_in.date_of_birth, today_gym())

    client = Client(
        user_id=user.id,
        trainer_id=trainer.id,
        name=client_in.name.strip(),
        phone=client_in.phone.strip() if client_in.phone else None,
        date_of_birth=client_in.date_of_birth,
        age=age,
        gender=client_in.gender,
        height=client_in.height,
        current_weight=client_in.current_weight,
        fitness_goal=client_in.fitness_goal or "General Fitness",
        status=client_in.status or ClientStatus.ACTIVE.value,
        profile_photo=client_in.profile_photo,
        emergency_contact=client_in.emergency_contact.strip() if client_in.emergency_contact else None,
        joined_date=client_in.joined_date or today_gym(),
        training_preferences=client_in.training_preferences.strip() if client_in.training_preferences else None,
    )
    db.add(client)
    db.commit()
    db.refresh(client)
    return ClientResponse.model_validate(client)


@router.get("/{client_id}", response_model=ClientResponse)
def get_client(
    client_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return ClientResponse.model_validate(verify_client_access(client_id, current_user, db))


@router.put("/{client_id}", response_model=ClientResponse)
def update_client(
    client_id: int,
    update_data: ClientUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    client = verify_client_access(client_id, current_user, db)
    data = update_data.model_dump(exclude_unset=True)

    for key in NOT_NULLABLE:
        if key in data and data[key] is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"{key} cannot be empty")
    if "status" in data and data["status"] not in EDITABLE_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Status must be one of: {', '.join(sorted(EDITABLE_STATUSES))}",
        )

    if "email" in data:
        email = data.pop("email")
        if email:
            email = email.lower().strip()
            taken = db.query(User.id).filter(User.email == email, User.id != client.user_id).first()
            if taken:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="A client with this email address already exists",
                )
            client.user.email = email
        elif client.email:
            # Clearing the email: fall back to a hidden placeholder (the column is required)
            client.user.email = f"client-{secrets.token_hex(8)}@{NO_LOGIN_EMAIL_DOMAIN}"

    for key in ("name", "phone", "emergency_contact", "training_preferences"):
        if isinstance(data.get(key), str):
            data[key] = data[key].strip() or (None if key != "name" else data[key])

    for key, value in data.items():
        setattr(client, key, value)

    # Keep age in step with the date of birth
    if "date_of_birth" in data and client.date_of_birth and "age" not in data:
        client.age = _age_on(client.date_of_birth, today_gym())

    db.commit()
    db.refresh(client)
    return ClientResponse.model_validate(client)


@router.post("/{client_id}/archive")
def archive_client(
    client_id: int,
    db: Session = Depends(get_db),
    trainer_data=Depends(get_current_trainer),
):
    _, trainer = trainer_data
    client = _get_trainer_client(db, client_id, trainer.id)
    client.status = ClientStatus.ARCHIVED.value
    db.commit()
    return {"message": f"Client {client.name} archived successfully. Historical records preserved."}


@router.delete("/{client_id}")
def deactivate_client(
    client_id: int,
    db: Session = Depends(get_db),
    trainer_data=Depends(get_current_trainer),
):
    _, trainer = trainer_data
    client = _get_trainer_client(db, client_id, trainer.id)
    client.status = ClientStatus.INACTIVE.value
    db.commit()
    return {"message": f"Client {client.name} deactivated successfully"}


@router.delete("/{client_id}/permanent")
def delete_client_permanently(
    client_id: int,
    db: Session = Depends(get_db),
    trainer_data=Depends(get_current_trainer),
):
    """Permanently removes an archived client and all of their history.

    Only archived clients can be deleted, so a client is always archived (and kept)
    first; this is for clearing out mistakes and duplicates.
    """
    _, trainer = trainer_data
    client = _get_trainer_client(db, client_id, trainer.id)
    if client.status != ClientStatus.ARCHIVED.value:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Archive the client before deleting them permanently",
        )
    name = client.name
    files = [client.profile_photo] + [p.photo_path for p in client.progress_photos]
    # Deleting the login-disabled user row cascades to the client and all of their records
    db.delete(client.user)
    db.commit()
    for key in files:
        if key:
            delete_secure_file(key, db)
    return {"message": f"{name} and all of their records were deleted"}


@router.post("/{client_id}/photo")
async def upload_client_photo(
    client_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Upload or replace client profile photo.
    Validates file bytes, strips EXIF metadata, saves unique file, and cleans up previous file.
    """
    client = verify_client_access(client_id, current_user, db)

    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty.",
        )

    # Save new image securely
    storage_key, _ = validate_and_save_image(file_bytes, subfolder="profiles", db=db)

    # If previous photo existed, delete the old file
    if client.profile_photo and client.profile_photo != storage_key:
        delete_secure_file(client.profile_photo, db)

    client.profile_photo = storage_key
    db.commit()
    db.refresh(client)

    return {
        "message": "Profile photo updated successfully.",
        "profile_photo": storage_key,
        "photo_url": f"/api/clients/{client.id}/photo",
    }


@router.get("/{client_id}/photo")
def get_client_photo(
    client_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_with_media_token),
):
    """
    Access-controlled image streaming endpoint.
    Verifies that the authenticated user has authorization to view this client.
    """
    client = verify_client_access(client_id, current_user, db)

    if not client.profile_photo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client has no profile photo.",
        )

    content, media_type = read_image(client.profile_photo, db)
    # private: only the signed-in browser may cache it, never a CDN or proxy in between
    return Response(
        content=content,
        media_type=media_type,
        headers={"Cache-Control": "private, max-age=86400"},
    )


@router.delete("/{client_id}/photo")
def delete_client_photo(
    client_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Removes client profile photo safely without affecting other files.
    """
    client = verify_client_access(client_id, current_user, db)

    if client.profile_photo:
        delete_secure_file(client.profile_photo, db)
        client.profile_photo = None
        db.commit()

    return {"message": "Profile photo removed successfully."}
