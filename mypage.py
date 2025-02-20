
import streamlit as st
from datetime import datetime, timedelta
from db_utils import load_reports

def my_page():
    if "user" not in st.session_state or st.session_state["user"] is None:
        st.error("ログインしてください。")
        return

    st.title("👤 マイページ")

    reports = load_reports()
    my_reports = [r for r in reports if r["投稿者"] == st.session_state["user"]["name"]]

    st.subheader("📅 今週の投稿")
    now = datetime.utcnow()
    start_of_week = now - timedelta(days=now.weekday())
    end_of_week = start_of_week + timedelta(days=4)
    weekly_reports = [
        r for r in my_reports 
        if start_of_week.date() <= datetime.strptime(r["実行日"], "%Y-%m-%d").date() <= end_of_week.date()
    ]

    for report in weekly_reports:
        st.write(f"- {report['実行日']}: {report['カテゴリ']} / {report['場所']}")
