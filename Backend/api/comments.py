from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from db.database import get_db
from db.models import Comment, Recipe

from db.schemas import CommentCreate, CommentOut

from core.security import require_user


router = APIRouter()


@router.get("/recipe/{recipe_id}", response_model=list[CommentOut])
def list_comments(
    recipe_id: int,
    db: Session = Depends(get_db),
):
    """Public — list all comments on a recipe, most recent first."""
    recipe = db.query(Recipe).filter(Recipe.id == recipe_id).first()
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")

    comments = (
        db.query(Comment)
        .filter(Comment.recipe_id == recipe_id)
        .order_by(Comment.created_at.desc())
        .all()
    )
    return comments


@router.post("/", response_model=CommentOut)
def add_comment(
    data: CommentCreate,
    payload=Depends(require_user),
    db: Session = Depends(get_db),
):
    recipe = db.query(Recipe).filter(Recipe.id == data.recipe_id).first()
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")

    comment = Comment(
        user_id=int(payload["sub"]),
        recipe_id=data.recipe_id,
        content=data.content,
    )
    db.add(comment)
    db.commit()
    db.refresh(comment)
    return comment


@router.delete("/{comment_id}")
def delete_comment(
    comment_id: int,
    payload=Depends(require_user),
    db: Session = Depends(get_db),
):
    comment = db.query(Comment).filter(Comment.id == comment_id).first()
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")

    is_owner = comment.user_id == int(payload["sub"])
    is_admin = payload.get("role") == "admin"
    if not (is_owner or is_admin):
        raise HTTPException(status_code=403, detail="Not allowed to delete this comment")

    db.delete(comment)
    db.commit()
    return {"message": "comment deleted"}
