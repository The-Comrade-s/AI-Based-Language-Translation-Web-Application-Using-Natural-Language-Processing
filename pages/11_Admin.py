"""
pages/11_Admin.py
==================
Administrator panel: system overview, user management, activity logs,
and system health monitoring. Gated entirely behind require_admin.
"""

from __future__ import annotations

import streamlit as st
import pandas as pd

from auth.session import require_admin, get_current_user
from config import Roles
from services.admin_service import AdminService
from services.monitoring_service import MonitoringService
from utils.exceptions import ALTError
from utils.logger import get_logger

logger = get_logger(__name__)

st.set_page_config(page_title="Admin — ALT", page_icon="🛡️", layout="wide")


@st.cache_resource
def _admin_service() -> AdminService:
    return AdminService()


@st.cache_resource
def _monitoring_service() -> MonitoringService:
    return MonitoringService()


@require_admin
def render() -> None:
    current_admin = get_current_user()
    admin_svc = _admin_service()
    monitoring_svc = _monitoring_service()

    st.title("🛡️ Administrator Panel")

    tab_overview, tab_users, tab_logs, tab_monitor = st.tabs(
        ["Overview", "User Management", "Activity Logs", "System Health"]
    )

    with tab_overview:
        overview = admin_svc.system_overview()
        cols = st.columns(5)
        cols[0].metric("Total Users", overview["total_users"])
        cols[1].metric("Active Users", overview["active_users"])
        cols[2].metric("Disabled Users", overview["disabled_users"])
        cols[3].metric("Total Translations", overview["total_translations"])
        cols[4].metric("Translations Today", overview["translations_today"])

    with tab_users:
        search = st.text_input("Search users (name, email, username)")
        users = admin_svc.list_users(search=search or None, limit=100)

        if not users:
            st.info("No users found.")
        else:
            for u in users:
                with st.container(border=True):
                    col_info, col_actions = st.columns([3, 2])
                    with col_info:
                        status = "🟢 Active" if u["is_active"] else "🔴 Disabled"
                        st.markdown(f"**{u['full_name']}** ({u['email']}) — {u['role']} — {status}")
                        st.caption(f"Joined {u['created_at']:%Y-%m-%d} · Last login: {u['last_login'] or '—'}")
                    with col_actions:
                        is_self = u["id"] == current_admin["id"]
                        btn_cols = st.columns(3)
                        with btn_cols[0]:
                            toggle_label = "Disable" if u["is_active"] else "Enable"
                            if st.button(toggle_label, key=f"toggle_{u['id']}", disabled=is_self):
                                try:
                                    admin_svc.set_user_active(u["id"], not u["is_active"])
                                except ALTError as exc:
                                    st.error(exc.user_message)
                                else:
                                    st.rerun()
                        with btn_cols[1]:
                            new_role = Roles.USER if u["role"] == Roles.ADMIN else Roles.ADMIN
                            role_label = "Demote" if u["role"] == Roles.ADMIN else "Promote"
                            if st.button(role_label, key=f"role_{u['id']}", disabled=is_self):
                                try:
                                    admin_svc.set_user_role(u["id"], new_role)
                                except ALTError as exc:
                                    st.error(exc.user_message)
                                else:
                                    st.rerun()
                        with btn_cols[2]:
                            if st.button("Delete", key=f"delete_{u['id']}", disabled=is_self):
                                try:
                                    admin_svc.delete_user(u["id"])
                                except ALTError as exc:
                                    st.error(exc.user_message)
                                else:
                                    st.rerun()

    with tab_logs:
        logs = admin_svc.list_activity_logs(limit=100)
        if not logs:
            st.info("No activity recorded yet.")
        else:
            df = pd.DataFrame(
                [
                    {
                        "Time": log["created_at"].strftime("%Y-%m-%d %H:%M:%S"),
                        "User ID": log["user_id"],
                        "Action": log["action"],
                        "IP": log["ip_address"] or "—",
                    }
                    for log in logs
                ]
            )
            st.dataframe(df, use_container_width=True, hide_index=True)

    with tab_monitor:
        health = monitoring_svc.get_system_health()
        cache = monitoring_svc.get_cache_stats()

        cols = st.columns(4)
        cols[0].metric("CPU", f"{health['cpu_percent']}%" if health["cpu_percent"] is not None else "—")
        cols[1].metric("Memory", f"{health['memory_percent']}%" if health["memory_percent"] is not None else "—")
        cols[2].metric("Disk", f"{health['disk_percent']}%" if health["disk_percent"] is not None else "—")
        cols[3].metric("DB Size", f"{health['database_size_mb']} MB" if health["database_size_mb"] is not None else "—")

        st.caption(
            f"Model cache: {cache['model_cache_mb']} MB · Temp files: {cache['temp_files_mb']} MB"
        )


render()
