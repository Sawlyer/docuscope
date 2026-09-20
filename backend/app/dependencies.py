from fastapi import Depends, HTTPException, Request, status

from .config import settings
from .database import session_scope
from .repositories import UserRepository
from .security import decode_token
from .store import User

def current_user(request: Request) -> User:
    token = request.cookies.get(settings.session_cookie_name)
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentification requise")
    try:
        email = decode_token(token)["sub"]
        with session_scope() as session:
            user = UserRepository(session).get_by_email(email)
        if user is None:
            raise KeyError(email)
        return user
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session expirée ou jeton invalide") from exc


def admin_user(user: User = Depends(current_user)) -> User:
    if user.role != "ADMIN":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Rôle administrateur requis")
    return user
