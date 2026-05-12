from enum import StrEnum

from fastapi import Depends, HTTPException

from app.deps import get_current_user


class Role(StrEnum):
    ADMIN = "admin"
    OPERATOR = "operator"
    USER = "user"
    DEVICE = "device"


ROLE_LEVEL = {
    Role.USER: 10,
    Role.DEVICE: 10,
    Role.OPERATOR: 50,
    Role.ADMIN: 100,
}


def require_roles(*roles: Role):
    allowed = {role.value for role in roles}

    def dependency(user=Depends(get_current_user)):
        if user.role not in allowed:
            raise HTTPException(status_code=403, detail="Permission denied")
        return user

    return dependency


def require_min_role(role: Role):
    required = ROLE_LEVEL[role]

    def dependency(user=Depends(get_current_user)):
        try:
            user_role = Role(user.role)
        except ValueError:
            raise HTTPException(status_code=403, detail="Permission denied") from None

        if ROLE_LEVEL.get(user_role, 0) < required:
            raise HTTPException(status_code=403, detail="Permission denied")
        return user

    return dependency
