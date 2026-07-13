from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app import crud
from app.database import get_db
from app.schemas.award import AwardRead

router = APIRouter(prefix="/awards", tags=["récompenses"])


@router.get("", response_model=list[AwardRead])
def list_awards(db: Session = Depends(get_db)) -> list:
    """Liste les catégories de récompenses et leur date limite."""
    return crud.award.list_all(db)
