"""
pages/6_History.py
===================
Translation history, favorites, search/filter, and export.
"""

from __future__ import annotations

import streamlit as st

from ai.language_registry import language_choices
from auth.session import require_login, get_current_user
from services.history_service import HistoryService
from services.export_service import ExportService
from utils.exceptions import ALTError
from utils.logger import get_logger

logger = get_logger(__name__)

st.set_page_config(page_title="History — ALT", page_icon="🕘", layout="wide")

_PAGE_SIZE = 20


@st.cache_resource
def _history_service() -> HistoryService:
    return HistoryService()


@st.cache_resource
def _export_service() -> ExportService:
    return ExportService()


@require_login
def render() -> None:
    user = get_current_user()
    history_svc = _history_service()
    export_svc = _export_service()

    st.title("🕘 Translation History")

    stats = history_svc.get_statistics(user["id"])
    cols = st.columns(4)
    cols[0].metric("Total Translations", stats["total_translations"])
    cols[1].metric("This Week", stats.get("weekly_translations", 0))
    cols[2].metric("Favorites", stats["favorite_count"])
    cols[3].metric("Total Words", stats["total_words"])

    st.divider()

    with st.expander("Search & Filters", expanded=False):
        search = st.text_input("Search text")
        col1, col2, col3 = st.columns(3)
        choices = language_choices()
        code_options = ["Any"] + [c for c, _ in choices]
        label_map = {"Any": "Any"} | {c: label for c, label in choices}
        with col1:
            src_filter = st.selectbox("Source language", code_options, format_func=lambda c: label_map[c])
        with col2:
            tgt_filter = st.selectbox("Target language", code_options, format_func=lambda c: label_map[c])
        with col3:
            favorites_only = st.checkbox("Favorites only")

    page = st.session_state.get("history_page", 0)

    records = history_svc.list_history(
        user["id"],
        search=search or None,
        source_language=None if src_filter == "Any" else src_filter,
        target_language=None if tgt_filter == "Any" else tgt_filter,
        favorites_only=favorites_only,
        limit=_PAGE_SIZE,
        offset=page * _PAGE_SIZE,
    )
    total = history_svc.count_history(user["id"], favorites_only=favorites_only)

    if not records:
        st.info("No translations found matching your filters.")
        return

    st.caption(f"Showing {len(records)} of {total} records")

    for r in records:
        with st.container(border=True):
            col_text, col_actions = st.columns([5, 1])
            with col_text:
                st.markdown(f"**{r['source_language']} → {r['target_language']}** · {r['created_at']:%Y-%m-%d %H:%M}")
                st.text(r["source_text"][:200])
                st.text(r["translated_text"][:200])
            with col_actions:
                fav_label = "★ Unfavorite" if r["is_favorite"] else "☆ Favorite"
                if st.button(fav_label, key=f"fav_{r['id']}"):
                    try:
                        history_svc.toggle_favorite(user["id"], r["id"])
                    except ALTError as exc:
                        st.error(exc.user_message)
                    else:
                        st.rerun()
                if st.button("🗑 Delete", key=f"del_{r['id']}"):
                    try:
                        history_svc.delete_record(user["id"], r["id"])
                    except ALTError as exc:
                        st.error(exc.user_message)
                    else:
                        st.rerun()

    col_prev, col_next = st.columns(2)
    with col_prev:
        if page > 0 and st.button("← Previous page"):
            st.session_state.history_page = page - 1
            st.rerun()
    with col_next:
        if (page + 1) * _PAGE_SIZE < total and st.button("Next page →"):
            st.session_state.history_page = page + 1
            st.rerun()

    st.divider()
    st.subheader("Export")
    export_format = st.selectbox("Format", ["TXT", "CSV", "JSON", "DOCX", "PDF"])
    if st.button("Export current results"):
        try:
            exporters = {
                "TXT": (export_svc.to_txt, "text/plain", "translations.txt"),
                "CSV": (export_svc.to_csv, "text/csv", "translations.csv"),
                "JSON": (export_svc.to_json, "application/json", "translations.json"),
                "DOCX": (export_svc.to_docx, "application/vnd.openxmlformats-officedocument.wordprocessingml.document", "translations.docx"),
                "PDF": (export_svc.to_pdf, "application/pdf", "translations.pdf"),
            }
            fn, mime, filename = exporters[export_format]
            data = fn(records)
        except ALTError as exc:
            st.error(exc.user_message)
        else:
            st.download_button("Download export", data=data, file_name=filename, mime=mime)

    if st.button("Clear all history", type="secondary"):
        st.session_state.confirm_clear = True

    if st.session_state.get("confirm_clear"):
        st.warning("This will permanently delete all your translation history.")
        col_yes, col_no = st.columns(2)
        with col_yes:
            if st.button("Yes, delete everything"):
                count = history_svc.clear_history(user["id"])
                st.session_state.confirm_clear = False
                st.success(f"Deleted {count} records.")
                st.rerun()
        with col_no:
            if st.button("Cancel"):
                st.session_state.confirm_clear = False
                st.rerun()


render()
