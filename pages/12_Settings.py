"""
pages/12_Settings.py
=====================
User settings: translation preferences, theme, notifications, offline
mode status, cache management, and personal data export.
"""

from __future__ import annotations

import json

import streamlit as st

from ai.language_registry import language_choices
from auth.session import require_login, get_current_user
from services.settings_service import SettingsService
from services.offline_service import OfflineService
from services.cache_service import CacheManager
from utils.exceptions import ALTError
from utils.logger import get_logger

logger = get_logger(__name__)

st.set_page_config(page_title="Settings — ALT", page_icon="⚙️")


@st.cache_resource
def _settings_service() -> SettingsService:
    return SettingsService()


@st.cache_resource
def _offline_service() -> OfflineService:
    return OfflineService()


@st.cache_resource
def _cache_manager() -> CacheManager:
    return CacheManager()


@require_login
def render() -> None:
    user = get_current_user()
    settings_svc = _settings_service()

    st.title("⚙️ Settings")

    tab_prefs, tab_appearance, tab_offline, tab_data = st.tabs(
        ["Translation Preferences", "Appearance & Accessibility", "Offline Mode", "Data & Privacy"]
    )

    current = settings_svc.get_settings(user["id"])
    choices = language_choices()
    code_labels = {c: label for c, label in choices}

    with tab_prefs:
        with st.form("prefs_form"):
            default_source = st.selectbox(
                "Default source language",
                ["auto"] + list(code_labels),
                index=(["auto"] + list(code_labels)).index(current["preferred_source_language"])
                if current["preferred_source_language"] in (["auto"] + list(code_labels)) else 0,
                format_func=lambda c: "Auto-detect" if c == "auto" else code_labels[c],
            )
            default_target = st.selectbox(
                "Default target language",
                list(code_labels),
                index=list(code_labels).index(current["preferred_target_language"])
                if current["preferred_target_language"] in code_labels else 0,
                format_func=lambda c: code_labels[c],
            )
            notifications = st.checkbox("Enable notifications", value=current["notifications_enabled"])
            submitted = st.form_submit_button("Save Preferences")

        if submitted:
            try:
                settings_svc.update_settings(
                    user["id"],
                    preferred_source_language=default_source,
                    preferred_target_language=default_target,
                    notifications_enabled=notifications,
                )
            except ALTError as exc:
                st.error(exc.user_message)
            else:
                st.success("Preferences saved.")
                st.rerun()

    with tab_appearance:
        with st.form("appearance_form"):
            theme = st.radio("Theme", ["light", "dark", "system"], index=["light", "dark", "system"].index(current["theme"]))
            high_contrast = st.checkbox(
                "High contrast mode", value=current["accessibility_options"].get("high_contrast", False)
            )
            larger_text = st.checkbox(
                "Larger text", value=current["accessibility_options"].get("larger_text", False)
            )
            reduced_motion = st.checkbox(
                "Reduced motion", value=current["accessibility_options"].get("reduced_motion", False)
            )
            submitted_theme = st.form_submit_button("Save Appearance Settings")

        if submitted_theme:
            try:
                settings_svc.update_settings(
                    user["id"],
                    theme=theme,
                    accessibility_options={
                        "high_contrast": high_contrast,
                        "larger_text": larger_text,
                        "reduced_motion": reduced_motion,
                    },
                )
            except ALTError as exc:
                st.error(exc.user_message)
            else:
                st.success("Appearance settings saved. Some changes may require a page refresh.")

    with tab_offline:
        offline_svc = _offline_service()
        cache_mgr = _cache_manager()

        readiness = offline_svc.offline_readiness()
        if readiness["offline_ready"]:
            st.success(f"Primary model ({readiness['primary_model']}) is cached locally — offline translation is available.")
        else:
            st.warning(
                f"Primary model ({readiness['primary_model']}) is not yet downloaded. "
                "It will be fetched automatically on first use (requires internet access)."
            )

        if readiness["cached_models"]:
            st.subheader("Cached Models")
            for m in readiness["cached_models"]:
                col_name, col_size, col_action = st.columns([3, 1, 1])
                col_name.write(m["name"])
                col_size.write(f"{m['size_mb']} MB")
                if col_action.button("Remove", key=f"remove_{m['name']}"):
                    offline_svc.delete_cached_model(m["name"])
                    st.rerun()

        st.divider()
        st.subheader("Cache Management")
        if st.button("Clear temporary files"):
            count = cache_mgr.clear_temp_files()
            st.success(f"Cleared {count} temporary file(s).")

    with tab_data:
        st.subheader("Export Your Data")
        st.write("Download a copy of your profile, settings, and translation history.")
        if st.button("Generate Export"):
            try:
                data = settings_svc.export_user_data(user["id"])
            except ALTError as exc:
                st.error(exc.user_message)
            else:
                st.download_button(
                    "Download JSON export",
                    data=json.dumps(data, indent=2, ensure_ascii=False),
                    file_name="alt_my_data.json",
                    mime="application/json",
                )


render()
