"""
pages/3_Forgot_Password.py
===========================
Forgot-password request and reset-password completion, combined into one
page for simplicity. Token delivery (email) is left pluggable: today the
token is shown on-screen for local development, but `request_password_reset`
already returns exactly what an email-sending integration would need.
"""

from __future__ import annotations

import streamlit as st

from auth.service import request_password_reset, reset_password
from utils.exceptions import ValidationError
from utils.logger import get_logger

logger = get_logger(__name__)

st.set_page_config(page_title="Forgot Password — ALT", page_icon="🔑")

st.title("🔑 Forgot Password")

tab_request, tab_reset = st.tabs(["Request Reset", "I have a reset token"])

with tab_request:
    with st.form("forgot_password_form"):
        email = st.text_input("Registered Email")
        submitted = st.form_submit_button("Send Reset Instructions", use_container_width=True)

    if submitted:
        if not email:
            st.warning("Please enter your email address.")
        else:
            try:
                token = request_password_reset(email)
            except Exception:
                logger.exception("Unexpected error requesting password reset")
                st.error("Something went wrong. Please try again.")
            else:
                # Always show the same message regardless of whether the
                # account exists, to avoid leaking which emails are registered.
                st.success("If that email is registered, reset instructions have been sent.")
                if token:
                    st.caption("Development mode — no email service configured yet:")
                    st.code(token, language=None)

with tab_reset:
    with st.form("reset_password_form"):
        token_input = st.text_input("Reset Token")
        new_password = st.text_input("New Password", type="password")
        confirm_password = st.text_input("Confirm New Password", type="password")
        reset_submitted = st.form_submit_button("Reset Password", use_container_width=True)

    if reset_submitted:
        try:
            reset_password(token_input, new_password, confirm_password)
        except ValidationError as exc:
            st.error(exc.user_message)
        except Exception:
            logger.exception("Unexpected error resetting password")
            st.error("Something went wrong. Please try again.")
        else:
            st.success("Password reset successfully. You can now log in.")
            st.page_link("pages/1_Login.py", label="Go to Login →")
