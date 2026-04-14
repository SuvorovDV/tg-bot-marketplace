"""SQLAdmin authentication backend: single-password login."""
from __future__ import annotations

from sqladmin.authentication import AuthenticationBackend
from starlette.requests import Request
from starlette.responses import RedirectResponse

from app.config import settings


class AdminAuth(AuthenticationBackend):
    async def login(self, request: Request) -> bool:
        form = await request.form()
        password = (form.get("password") or "").strip()
        if password and password == settings.web_admin_password:
            request.session["admin"] = True
            return True
        return False

    async def logout(self, request: Request) -> bool:
        request.session.clear()
        return True

    async def authenticate(self, request: Request) -> bool | RedirectResponse:
        return bool(request.session.get("admin"))


class OpenAuth(AuthenticationBackend):
    """Always-pass backend so SQLAdmin's internal calls don't trip the
    `self.authentication_backend is not None` assertion when running two
    Admin instances side-by-side."""

    async def login(self, request: Request) -> bool:  # pragma: no cover
        return True

    async def logout(self, request: Request) -> bool:  # pragma: no cover
        return True

    async def authenticate(self, request: Request) -> bool:
        return True
