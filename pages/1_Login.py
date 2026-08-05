"""
pages/1_Login.py
=================
Login page. Streamlit auto-discovers this as a sidebar nav entry.
"""

from __future__ import annotations

import streamlit as st

from auth.service import login_user
from auth.session import set_current_user, is_authenticated
from utils.exceptions import AuthenticationError, AccountLockedError
from utils.logger import get_logger

logger = get_logger(__name__)

st.set_page_config(page_title="Login — ALT", page_icon="🔐")


def render() -> None:
    st.title("🔐 Log In")

    if is_authenticated():
        st.success("You're already logged in.")
        st.page_link("pages/4_Profile.py", label="Go to your profile →")
        return

    with st.form("login_form", clear_on_submit=False):
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        remember_me = st.checkbox("Remember me", value=True)
        submitted = st.form_submit_button("Log In", use_container_width=True)

    if submitted:
        if not email or not password:
            st.warning("Please enter both email and password.")
            return

        try:
            user = login_user(email=email, password=password)
        except AccountLockedError as exc:
            st.error(exc.user_message)
        except AuthenticationError as exc:
            st.error(exc.user_message)
        except Exception:
            logger.exception("Unexpected error during login")
            st.error("Something went wrong while logging in. Please try again.")
        else:
            set_current_user(user)
            st.session_state.remember_me = remember_me
            st.success(f"Welcome back, {user['full_name']}!")
            st.rerun()

    st.divider()
    col1, col2 = st.columns(2)
    with col1:
        st.page_link("pages/2_Register.py", label="Create an account →")
    with col2:
        st.page_link("pages/3_Forgot_Password.py", label="Forgot password? →")


render()
