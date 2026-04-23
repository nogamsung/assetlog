"""Auth router — signup, login, logout, and current-user endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Response, status

from app.core.config import settings
from app.core.deps import AuthServiceDep, CurrentUser, DbSession
from app.core.security import create_access_token
from app.schemas.auth import ErrorResponse, UserCreate, UserLogin, UserResponse

router = APIRouter(prefix="/api/auth", tags=["auth"])

_COOKIE_KEY = "access_token"


def _set_auth_cookie(response: Response, token: str) -> None:
    """Attach the JWT access token as an httpOnly cookie."""
    response.set_cookie(
        key=_COOKIE_KEY,
        value=token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,  # type: ignore[arg-type]  # Literal type from settings str
        max_age=settings.jwt_access_token_expire_minutes * 60,
        path="/",
    )


@router.post(
    "/signup",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user account",
    responses={
        409: {"model": ErrorResponse, "description": "Email already registered"},
        422: {"model": ErrorResponse, "description": "Validation error"},
    },
)
async def signup(
    data: UserCreate,
    response: Response,
    session: DbSession,
    auth_service: AuthServiceDep,
) -> UserResponse:
    """Create a new user and return the profile with an httpOnly auth cookie."""
    user = await auth_service.register(session, data)
    token = create_access_token(subject=user.id)
    _set_auth_cookie(response, token)
    return UserResponse.model_validate(user)


@router.post(
    "/login",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Authenticate and receive an access token cookie",
    responses={
        401: {"model": ErrorResponse, "description": "Invalid credentials"},
        422: {"model": ErrorResponse, "description": "Validation error"},
    },
)
async def login(
    data: UserLogin,
    response: Response,
    session: DbSession,
    auth_service: AuthServiceDep,
) -> UserResponse:
    """Verify credentials and set an httpOnly auth cookie on success."""
    user = await auth_service.authenticate(session, data)
    token = create_access_token(subject=user.id)
    _set_auth_cookie(response, token)
    return UserResponse.model_validate(user)


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Clear the auth cookie and end the session",
    responses={204: {"description": "Successfully logged out"}},
)
async def logout(response: Response) -> None:
    """Delete the access_token cookie to invalidate the client session."""
    response.delete_cookie(key=_COOKIE_KEY, path="/", domain=None)


@router.get(
    "/me",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Return the currently authenticated user",
    responses={
        401: {"model": ErrorResponse, "description": "Not authenticated"},
    },
)
async def me(current_user: CurrentUser) -> UserResponse:
    """Return profile information for the bearer of the current auth token."""
    return UserResponse.model_validate(current_user)
