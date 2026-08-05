"""tests/test_admin_service.py"""

from __future__ import annotations

import pytest

from auth.service import register_user
from services.admin_service import AdminService
from config import Roles
from utils.exceptions import ValidationError


@pytest.fixture
def two_users():
    u1 = register_user("Alice", "alice@example.com", "Str0ng!Pass", "Str0ng!Pass")
    u2 = register_user("Bob", "bob@example.com", "Str0ng!Pass", "Str0ng!Pass")
    return u1, u2


def test_system_overview(two_users):
    svc = AdminService()
    overview = svc.system_overview()
    assert overview["total_users"] == 2
    assert overview["active_users"] == 2


def test_search_users(two_users):
    svc = AdminService()
    results = svc.list_users(search="alice")
    assert len(results) == 1
    assert results[0]["email"] == "alice@example.com"


def test_promote_and_demote(two_users):
    u1, _ = two_users
    svc = AdminService()
    svc.set_user_role(u1.id, Roles.ADMIN)
    assert svc.list_users(search="alice")[0]["role"] == Roles.ADMIN

    svc.set_user_role(u1.id, Roles.USER)
    assert svc.list_users(search="alice")[0]["role"] == Roles.USER


def test_invalid_role_rejected(two_users):
    u1, _ = two_users
    svc = AdminService()
    with pytest.raises(ValidationError):
        svc.set_user_role(u1.id, "superadmin")


def test_disable_enable_user(two_users):
    _, u2 = two_users
    svc = AdminService()
    svc.set_user_active(u2.id, False)
    assert svc.list_users(search="bob")[0]["is_active"] is False

    svc.set_user_active(u2.id, True)
    assert svc.list_users(search="bob")[0]["is_active"] is True


def test_nonexistent_user_rejected():
    svc = AdminService()
    with pytest.raises(ValidationError):
        svc.set_user_active(999999, True)


def test_delete_user(two_users):
    _, u2 = two_users
    svc = AdminService()
    svc.delete_user(u2.id)
    assert svc.system_overview()["total_users"] == 1
