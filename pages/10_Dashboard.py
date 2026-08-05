"""
pages/10_Dashboard.py
======================
Personal dashboard: overview metrics, quick actions, recent activity,
and usage charts.
"""

from __future__ import annotations

import streamlit as st
import pandas as pd

from auth.session import require_login, get_current_user
from services.history_service import HistoryService

st.set_page_config(page_title="Dashboard — ALT", page_icon="📊", layout="wide")


@st.cache_resource
def _history_service() -> HistoryService:
    return HistoryService()


@require_login
def render() -> None:
    user = get_current_user()
    history_svc = _history_service()

    st.title(f"📊 Welcome back, {user['full_name'].split()[0]}")

    stats = history_svc.get_statistics(user["id"])

    cols = st.columns(5)
    cols[0].metric("Total Translations", stats["total_translations"])
    cols[1].metric("Today", stats.get("today_translations", 0))
    cols[2].metric("This Week", stats.get("weekly_translations", 0))
    cols[3].metric("Favorites", stats["favorite_count"])
    cols[4].metric("Total Words", stats["total_words"])

    st.divider()

    st.subheader("Quick Actions")
    qa_cols = st.columns(4)
    with qa_cols[0]:
        st.page_link("pages/5_Translate.py", label="🌐 New Translation")
    with qa_cols[1]:
        st.page_link("pages/7_Document_Translation.py", label="📄 Translate Document")
    with qa_cols[2]:
        st.page_link("pages/8_OCR_Translation.py", label="🖼️ Translate Image")
    with qa_cols[3]:
        st.page_link("pages/6_History.py", label="🕘 View History")

    st.divider()

    st.subheader("Recent Activity")
    recent = history_svc.list_history(user["id"], limit=10)
    if not recent:
        st.info("No translations yet — head to the Translate page to get started.")
    else:
        df = pd.DataFrame(
            [
                {
                    "Date": r["created_at"].strftime("%Y-%m-%d %H:%M"),
                    "From": r["source_language"],
                    "To": r["target_language"],
                    "Text": r["source_text"][:60],
                }
                for r in recent
            ]
        )
        st.dataframe(df, use_container_width=True, hide_index=True)

    if stats.get("most_used_target_language"):
        st.caption(f"Most translated-to language: **{stats['most_used_target_language']}**")


render()
