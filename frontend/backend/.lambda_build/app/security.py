from fastapi import HTTPException, Request, status

from app.schemas import UserContext


def _parse_roles(raw_roles: str | None) -> list[str]:
    if not raw_roles:
        return []
    return [role.strip() for role in raw_roles.split(",") if role.strip()]


async def get_current_user(request: Request) -> UserContext:
    """Build user context from the frontend-authenticated Clerk session headers."""

    user_id = request.headers.get("x-user-id")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing frontend-authenticated user context.",
        )

    user_context = UserContext(
        user_id=user_id,
        email=request.headers.get("x-user-email"),
        org_id=request.headers.get("x-org-id"),
        roles=_parse_roles(request.headers.get("x-user-roles")),
        raw_claims={},
    )
    request.state.user_context = user_context
    return user_context
