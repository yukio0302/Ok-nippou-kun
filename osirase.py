
import streamlit as st
from db_utils import load_notices, mark_notice_as_read

def show_notices():
    if "user" not in st.session_state or st.session_state["user"] is None:
        st.error("ログインしてください。")
        return

    st.title("🔔 お知らせ")

    notices = load_notices()

    for notice in notices:
        status = "未読" if notice["既読"] == 0 else "既読"
        st.subheader(f"{notice['タイトル']} - {status}")
        st.write(f"📅 {notice['日付']}")
        st.write(f"{notice['内容']}")
        if notice["既読"] == 0:
            if st.button(f"既読にする ({notice['id']})"):
                mark_notice_as_read(notice["id"])
                st.experimental_rerun()
