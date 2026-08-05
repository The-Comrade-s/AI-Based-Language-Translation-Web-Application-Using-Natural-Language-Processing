"""
pages/4_Profile.py
===================
Authenticated user's profile: view details, edit basic info, change
password. Requires login via the require_login decorator.
"""

from __future__ import annotations

from sqlalchemy import select

import streamlit as st

from auth.session import require_login, get_current_user, clear_current_user, set_current_user
from auth.service import change_password, logout_user
from database.base import get_session
from models.user import User
from utils.exceptions import ValidationError, AuthenticationError
from utils.security import sanitize_text_input
from utils.logger import get_logger

logger = get_logger(__name__)

st.set_page_config(page_title="Profile — ALT", page_icon="👤")


@require_login
def render() -> None:
    user = get_current_user()
    st.title("👤 Your Profile")

    tab_view, tab_edit, tab_password = st.tabs(["Overview", "Edit Profile", "Change Password"])

    with tab_view:
        with get_session() as session:
            db_user = session.get(User, user["id"])
            if db_user is None:
                st.error("Account not found.")
                return
            st.write(f"**Full name:** {db_user.full_name}")
            st.write(f"**Email:** {db_user.email}")
            st.write(f"**Username:** {db_user.username or '—'}")
            st.write(f"**Phone:** {db_user.phone or '—'}")
            st.write(f"**Role:** {db_user.role}")
            st.write(f"**Member since:** {db_user.created_at:%Y-%m-%d}")
            st.write(f"**Last login:** {db_user.last_login:%Y-%m-%d %H:%M} UTC" if db_user.last_login else "**Last login:** —")

        if st.button("Log Out"):
            logout_user(user["id"])
            clear_current_user()
            st.success("Logged out.")
            st.rerun()

    with tab_edit:
        with st.form("edit_profile_form"):
            full_name = st.text_input("Full Name", value=user["full_name"])
            phone = st.text_input("Phone Number")
            submitted = st.form_submit_button("Save Changes")

        if submitted:
            try:
                with get_session() as session:
                    db_user = session.get(User, user["id"])
                    if db_user is None:
                        raise AuthenticationError("User not found.", user_message="Account not found.")
                    db_user.full_name = sanitize_text_input(full_name, max_length=150) or db_user.full_name
                    db_user.phone = sanitize_text_input(phone, max_length=30) or db_user.phone
            except Exception:
                logger.exception("Error updating profile for user id=%s", user["id"])
                st.error("Could not update your profile. Please try again.")
            else:
                updated_user = dict(user)
                updated_user["full_name"] = full_name
                set_current_user(updated_user)
                st.success("Profile updated.")
                st.rerun()

    with tab_password:
        with st.form("change_password_form"):
            current_password = st.text_input("Current Password", type="password")
            new_password = st.text_input("New Password", type="password")
            confirm_password = st.text_input("Confirm New Password", type="password")
            submitted_pw = st.form_submit_button("Update Password")

        if submitted_pw:
            try:
                change_password(user["id"], current_password, new_password, confirm_password)
            except (ValidationError, AuthenticationError) as exc:
                st.error(exc.user_message)
            except Exception:
                logger.exception("Error changing password for user id=%s", user["id"])
                st.error("Something went wrong. Please try again.")
            else:
                st.success("Password updated successfully.")


render()
