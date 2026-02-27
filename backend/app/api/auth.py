from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from jose import jwt, JWTError

from ..db import get_db
from ..models.user import User
from ..core.security import verify_password, create_access_token, create_refresh_token
from ..core.config import settings
from ..core.cache import get_redis
from ..core.rate_limit import limiter
from ..schemas.doc_schemas import Token, TokenRefreshRequest, UserLogin, UserResponse

router = APIRouter(prefix="/auth", tags=["auth"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login", auto_error=False)

_BLACKLIST_PREFIX = "blacklist:"


async def get_current_user(
    request: Request,
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    token = token or request.query_params.get("token")
    if not token:
        raise credentials_exception

    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    # Controlla blacklist token (logout server-side)
    if redis:
        try:
            if await redis.get(f"{_BLACKLIST_PREFIX}{token}"):
                raise credentials_exception
        except HTTPException:
            raise
        except Exception:
            pass  # Redis non disponibile: procedi senza blacklist

    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if user is None:
        raise credentials_exception
    return user


@router.post("/login", response_model=Token)
@limiter.limit("10/minute")
async def login(request: Request, login_data: UserLogin, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == login_data.email))
    user = result.scalar_one_or_none()

    if not user or not verify_password(login_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email o password non corretti.",
        )

    access_token = create_access_token(subject=user.email)
    refresh_token = create_refresh_token(subject=user.email)
    return {"access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer"}

@router.post("/refresh", response_model=Token)
@limiter.limit("5/minute")
async def refresh(request: Request, refresh_data: TokenRefreshRequest, db: AsyncSession = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token di refresh non valido o scaduto",
    )
    try:
        payload = jwt.decode(refresh_data.refresh_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        email: str = payload.get("sub")
        token_type: str = payload.get("type")
        if email is None or token_type != "refresh":
            raise credentials_exception
    except JWTError:
        raise credentials_exception
        
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if user is None or not user.is_active:
        raise credentials_exception

    new_access_token = create_access_token(subject=user.email)
    new_refresh_token = create_refresh_token(subject=user.email)
    
    return {"access_token": new_access_token, "refresh_token": new_refresh_token, "token_type": "bearer"}


@router.post("/logout")
@limiter.limit("30/minute")
async def logout(
    request: Request,
    token: str = Depends(oauth2_scheme),
    redis=Depends(get_redis),
):
    """
    Invalida il token JWT inserendolo nella blacklist Redis con TTL pari al
    tempo residuo. Anche senza Redis il client rimuove il token localmente.
    """
    token = token or request.query_params.get("token")
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    if redis:
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
            exp = payload.get("exp")
            if exp:
                remaining_ttl = int(exp - datetime.now(tz=timezone.utc).timestamp())
                if remaining_ttl > 0:
                    await redis.setex(f"{_BLACKLIST_PREFIX}{token}", remaining_ttl, "1")
        except Exception:
            pass  # Token già scaduto o Redis non disponibile

    return {"message": "Logout effettuato con successo."}


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    """Restituisce le informazioni dell'utente autenticato (incluso il ruolo)."""
    return current_user
