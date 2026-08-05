"""
app.py
======
Entry point for the ALT (AI Language Translator) Streamlit application.

This module is intentionally thin: it configures the page, ensures the
database is initialized, and delegates to page modules under `pages/`.
Business logic belongs in `services/`, not here.
"""

from __future__ import annotations

import streamlit as st

from config import settings
from database.base import init_db
from utils.logger import get_logger

logger = get_logger(__name__)


def configure_page() -> None:
    """Set global Streamlit page configuration. Must be the first
    Streamlit call made in the app."""
    st.set_page_config(
        page_title=settings.app_name,
        page_icon="🌐",
        layout="wide",
        initial_sidebar_state="expanded",
    )


def bootstrap() -> None:
    """One-time application startup tasks: DB schema creation, session
    state defaults. Safe to call on every rerun — each step is idempotent."""
    init_db()

    if "bootstrapped" not in st.session_state:
        st.session_state.bootstrapped = True
        st.session_state.user = None
        st.session_state.auth_token = None
        logger.info("ALT application session bootstrapped")


def render_landing() -> None:
    """Render the landing view shown before/after login. Streamlit's
    built-in multipage sidebar (from the `pages/` directory) handles
    actual navigation — this view orients the user and links to the
    most relevant next step for their auth state."""
    from auth.session import get_current_user

    st.title(f"🌐 {settings.app_name}")
    st.caption("AI-powered multilingual translation — including Yoruba, Hausa, and Igbo.")

    user = get_current_user()

    if user is None:
        st.info("Log in or create an account to start translating.")
        col1, col2 = st.columns(2)
        with col1:
            st.page_link("pages/1_Login.py", label="🔐 Log In", use_container_width=True)
        with col2:
            st.page_link("pages/2_Register.py", label="📝 Create Account", use_container_width=True)
    else:
        st.success(f"Welcome back, {user['full_name'].split()[0]}!")
        cols = st.columns(4)
        with cols[0]:
            st.page_link("pages/10_Dashboard.py", label="📊 Dashboard", use_container_width=True)
        with cols[1]:
            st.page_link("pages/5_Translate.py", label="🌐 Translate", use_container_width=True)
        with cols[2]:
            st.page_link("pages/6_History.py", label="🕘 History", use_container_width=True)
        with cols[3]:
            st.page_link("pages/12_Settings.py", label="⚙️ Settings", use_container_width=True)

        if user.get("role") == "admin":
            st.page_link("pages/11_Admin.py", label="🛡️ Admin Panel")

    with st.expander("About this project"):
        st.write(
            "ALT supports 50+ languages including Yoruba, Hausa, and Igbo, "
            "powered by Meta's NLLB-200 model with automatic fallback."
        )
        st.write(f"**Environment:** {settings.environment}")
        st.write(f"**Primary model:** {settings.primary_model_name}")


def main() -> None:
    configure_page()
    bootstrap()
    render_landing()


if __name__ == "__main__":
    main()
