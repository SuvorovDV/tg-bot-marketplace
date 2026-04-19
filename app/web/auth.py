"""SQLAdmin auth: everyone sees the panel; password unlocks edit mode.

`authenticate()` always returns True, so anonymous users get through
`@login_required`. Whether CRUD buttons render is controlled by a
contextvar populated from the session flag — see `admin_views.py`.
"""
from __future__ import annotations

from contextvars import ContextVar

from sqladmin.authentication import AuthenticationBackend
from starlette.requests import Request

from app.config import settings

# Per-request flag read by ModelView.can_create/edit/delete properties.
is_editor_mode: ContextVar[bool] = ContextVar("is_editor_mode", default=False)


class AdminAuth(AuthenticationBackend):
    async def login(self, request: Request) -> bool:
        form = await request.form()
        username = (form.get("username") or "").strip()
        password = (form.get("password") or "").strip()
        if (
            username == settings.web_admin_login
            and password == settings.web_admin_password
        ):
            request.session["admin"] = True
            return True
        return False

    async def logout(self, request: Request) -> bool:
        request.session.clear()
        return True

    async def authenticate(self, request: Request) -> bool:
        is_editor_mode.set(bool(request.session.get("admin")))
        return True
