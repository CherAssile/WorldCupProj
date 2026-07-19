import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.config import settings
from app.core.security import create_access_token, hash_password, verify_password
from app.crud import password_reset as password_reset_crud
from app.crud import user as user_crud
from app.database import get_db
from app.deps import get_current_user
from app.models.user import User
from app.schemas.user import (
    ForgotPasswordRequest,
    Message,
    ResetPasswordRequest,
    Token,
    UserCreate,
    UserRead,
)
from app.services.email import get_email_sender

router = APIRouter(prefix="/auth", tags=["auth"])

RESET_TOKEN_TTL = timedelta(hours=1)

# Toujours la même réponse, e-mail connu ou non : une réponse différenciée permettrait
# d'énumérer les comptes existants.
_FORGOT_PASSWORD_MESSAGE = "Si un compte existe pour cet e-mail, un lien de réinitialisation a été envoyé."


def _hash_reset_token(token: str) -> str:
    """SHA-256 hexadécimal : le jeton en clair ne touche jamais la base."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def register(user_in: UserCreate, db: Session = Depends(get_db)) -> User:
    """Crée un compte utilisateur. 409 si l'e-mail est déjà utilisé."""
    if user_crud.get_by_email(db, user_in.email) is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Cet e-mail est déjà utilisé.")
    return user_crud.create_user(db, user_in)


@router.post("/login", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)) -> Token:
    """Authentifie l'utilisateur et renvoie un JWT.

    Compatible avec le flux OAuth2 attendu par le bouton "Authorize" de Swagger :
    le champ `username` du formulaire contient en réalité l'e-mail de l'utilisateur.
    """
    user = user_crud.get_by_email(db, form_data.username)
    if user is None or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="E-mail ou mot de passe incorrect.",
        )
    return Token(access_token=create_access_token(subject=str(user.id)))


@router.get("/me", response_model=UserRead)
def me(current_user: User = Depends(get_current_user)) -> User:
    """Renvoie le profil de l'utilisateur authentifié."""
    return current_user


@router.post("/forgot-password", response_model=Message)
def forgot_password(payload: ForgotPasswordRequest, db: Session = Depends(get_db)) -> Message:
    """Demande de réinitialisation : jeton aléatoire à usage unique, valable 1 heure.

    Répond TOUJOURS 200 avec le même message, que l'e-mail existe ou non : toute
    différence de réponse permettrait d'énumérer les comptes (règle anti-énumération).
    """
    user = user_crud.get_by_email(db, payload.email)
    if user is not None:
        token = secrets.token_urlsafe(32)
        password_reset_crud.create(
            db,
            user_id=user.id,
            token_hash=_hash_reset_token(token),
            expires_at=datetime.now(timezone.utc) + RESET_TOKEN_TTL,
        )
        reset_url = f"{settings.frontend_base_url}/reinitialiser?token={token}"
        get_email_sender().send_password_reset(to_email=user.email, reset_url=reset_url)

    return Message(message=_FORGOT_PASSWORD_MESSAGE)


@router.post("/reset-password", response_model=Message)
def reset_password(payload: ResetPasswordRequest, db: Session = Depends(get_db)) -> Message:
    """Consomme un jeton de réinitialisation et remplace le mot de passe (bcrypt).

    400 si le jeton est inconnu, expiré ou déjà utilisé — même message dans les trois
    cas, pour ne rien révéler de l'état du jeton.
    """
    reset_token = password_reset_crud.get_by_hash(db, _hash_reset_token(payload.token))
    now = datetime.now(timezone.utc)

    if reset_token is None or reset_token.used_at is not None or reset_token.expires_at <= now:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Jeton invalide ou expiré."
        )

    user = user_crud.get_by_id(db, reset_token.user_id)
    user.hashed_password = hash_password(payload.new_password)
    reset_token.used_at = now
    db.commit()

    return Message(message="Mot de passe réinitialisé. Tu peux te connecter.")
