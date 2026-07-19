import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.crud import user as user_crud
from app.database import get_db
from app.models.user import User
from app.services.ai_client import AIClient

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def get_ai_client() -> AIClient:
    """Fournit le client du service IA. Injecté par dépendance pour que les tests puissent
    le remplacer par un faux client (sans dépendre du vrai dataset du service)."""
    return AIClient()


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Résout l'utilisateur courant à partir du JWT. 401 si absent, invalide ou expiré."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Identifiants invalides",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = decode_access_token(token)
    except jwt.PyJWTError:
        raise credentials_exception

    user_id = payload.get("sub")
    if user_id is None:
        raise credentials_exception

    user = user_crud.get_by_id(db, int(user_id))
    if user is None:
        raise credentials_exception

    return user


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """Réserve un endpoint aux administrateurs. 403 sinon."""
    if not current_user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Réservé aux administrateurs.")
    return current_user
