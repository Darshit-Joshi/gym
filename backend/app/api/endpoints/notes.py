from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.api.deps import (
    get_db,
    get_current_trainer,
    verify_client_access,
)
from app.models.note import TrainerNote
from app.schemas.note import (
    TrainerNoteCreate,
    TrainerNoteUpdate,
    TrainerNoteResponse,
)

router = APIRouter()


def _format_note_response(n: TrainerNote) -> TrainerNoteResponse:
    return TrainerNoteResponse(
        id=n.id,
        client_id=n.client_id,
        trainer_id=n.trainer_id,
        trainer_name=n.trainer.name if n.trainer else "Trainer",
        note=n.note,
        created_at=n.created_at,
        updated_at=n.updated_at,
    )


@router.get("/client/{client_id}", response_model=List[TrainerNoteResponse])
def get_client_notes(
    client_id: int,
    db: Session = Depends(get_db),
    trainer_data=Depends(get_current_trainer),
):
    _, trainer = trainer_data
    verify_client_access(client_id, trainer.user, db)
    notes = (
        db.query(TrainerNote)
        .filter(TrainerNote.client_id == client_id, TrainerNote.trainer_id == trainer.id)
        .order_by(TrainerNote.created_at.desc())
        .all()
    )
    return [_format_note_response(n) for n in notes]


@router.post("/client/{client_id}", response_model=TrainerNoteResponse, status_code=status.HTTP_201_CREATED)
def create_client_note(
    client_id: int,
    note_in: TrainerNoteCreate,
    db: Session = Depends(get_db),
    trainer_data=Depends(get_current_trainer),
):
    _, trainer = trainer_data
    # Verify client exists
    verify_client_access(client_id, trainer.user, db)

    note = TrainerNote(
        client_id=client_id,
        trainer_id=trainer.id,
        note=note_in.note.strip(),
    )
    db.add(note)
    db.commit()
    db.refresh(note)
    return _format_note_response(note)


@router.put("/{note_id}", response_model=TrainerNoteResponse)
def update_note(
    note_id: int,
    note_in: TrainerNoteUpdate,
    db: Session = Depends(get_db),
    trainer_data=Depends(get_current_trainer),
):
    _, trainer = trainer_data
    note = db.query(TrainerNote).filter(TrainerNote.id == note_id).first()
    if not note:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Note with id {note_id} not found",
        )

    if note.trainer_id != trainer.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only edit your own notes",
        )

    note.note = note_in.note.strip()
    db.commit()
    db.refresh(note)
    return _format_note_response(note)


@router.delete("/{note_id}")
def delete_note(
    note_id: int,
    db: Session = Depends(get_db),
    trainer_data=Depends(get_current_trainer),
):
    _, trainer = trainer_data
    note = db.query(TrainerNote).filter(TrainerNote.id == note_id).first()
    if not note:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Note with id {note_id} not found",
        )

    if note.trainer_id != trainer.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only delete your own notes",
        )

    db.delete(note)
    db.commit()
    return {"message": "Trainer note deleted successfully"}
