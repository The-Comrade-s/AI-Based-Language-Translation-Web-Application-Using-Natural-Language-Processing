"""
pages/2_Register.py
====================
Registration page.
"""

from __future__ import annotations

import streamlit as st

from auth.service import register_user
from auth.session import is_authenticated
from utils.exceptions import ValidationError
from utils.logger import get_logger

logger = get_logger(__name__)

st.set_page_config(page_title="Register — ALT", page_icon="📝")


def render() -> None:
    st.title("📝 Create Your Account")

    if is_authenticated():
        st.info("You're already logged in.")
        return

    with st.form("register_form"):
        full_name = st.text_input("Full Name *")
        col1, col2 = st.columns(2)
        with col1:
            email = st.text_input("Email *")
        with col2:
            username = st.text_input("Username (optional)")
        phone = st.text_input("Phone Number (optional)")
        col3, col4 = st.columns(2)
        with col3:
            password = st.text_input("Password *", type="password")
        with col4:
            confirm_password = st.text_input("Confirm Password *", type="password")
        accepted_terms = st.checkbox("I accept the Terms & Conditions")
        submitted = st.form_submit_button("Create Account", use_container_width=True)

    if submitted:
        if not accepted_terms:
            st.warning("You must accept the Terms & Conditions to register.")
            return

        try:
            user = register_user(
                full_name=full_name,
                email=email,
                password=password,
                confirm_password=confirm_password,
                username=username or None,
                phone=phone or None,
            )
        except ValidationError as exc:
            st.error(exc.user_message)
        except Exception:
            logger.exception("Unexpected error during registration")
            st.error("Something went wrong while creating your account. Please try again.")
        else:
            st.success(f"Account created for {user.full_name}! You can now log in.")
            st.page_link("pages/1_Login.py", label="Go to Login →")

    st.divider()
    st.page_link("pages/1_Login.py", label="Already have an account? Log in →")


render()
