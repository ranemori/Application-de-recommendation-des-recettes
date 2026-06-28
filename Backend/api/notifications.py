from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from db.database import get_db
from db.models import Notification

from db.schemas import NotificationOut

from core.security import require_user


router = APIRouter()


@router.get("/me", response_model=List[NotificationOut])
def list_notifications(
    limit: int = 20,
    payload=Depends(require_user),
    db: Session = Depends(get_db),
):
    user_id = int(payload["sub"])
    return (
        db.query(Notification)
        .filter(Notification.user_id == user_id)
        .order_by(Notification.created_at.desc())
        .limit(limit)
        .all()
    )


@router.get("/me/unread-count")
def unread_count(
    payload=Depends(require_user),
    db: Session = Depends(get_db),
):
    user_id = int(payload["sub"])
    count = (
        db.query(Notification)
        .filter(Notification.user_id == user_id, Notification.is_read == False)
        .count()
    )
    return {"count": count}


@router.post("/{notification_id}/read")
def mark_read(
    notification_id: int,
    payload=Depends(require_user),
    db: Session = Depends(get_db),
):
    user_id = int(payload["sub"])
    notif = (
        db.query(Notification)
        .filter(Notification.id == notification_id, Notification.user_id == user_id)
        .first()
    )
    if not notif:
        raise HTTPException(404, "Notification not found")
    notif.is_read = True
    db.commit()
    return {"message": "marked as read"}


@router.post("/me/read-all")
def mark_all_read(
    payload=Depends(require_user),
    db: Session = Depends(get_db),
):
    user_id = int(payload["sub"])
    db.query(Notification).filter(
        Notification.user_id == user_id, Notification.is_read == False
    ).update({"is_read": True})
    db.commit()
    return {"message": "all marked as read"}
