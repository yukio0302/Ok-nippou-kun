import streamlit as st
from db_utils import init_db

# ページモジュールをインポート
from loguin import login
from timeline import timeline
from toukou import post_report
from osirase import show_notices
from mypage import my_page

# SQLite 初期化（データを消さない）
init_db(keep_existing=True)

# セッション状態の初期化
if "user" not in st.session_state:
    st.session_state["user"] = None
if "page" not in st.session_state:
    st.session_state["page"] = "ログイン"

# ページナビゲーション
def switch_page(page_name):
    st.session_state["page"] = page_name

# ナビゲーションバー
def top_navigation():
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        if st.button("🏠 タイムライン"):
            switch_page("タイムライン")
            st.experimental_rerun()
    with col2:
        if st.button("✏️ 日報投稿"):
            switch_page("日報投稿")
            st.experimental_rerun()
    with col3:
        if st.button("🔔 お知らせ"):
            switch_page("お知らせ")
            st.experimental_rerun()
    with col4:
        if st.button("👤 マイページ"):
            switch_page("マイページ")
            st.experimental_rerun()

# ページ表示
if st.session_state["user"] is None:
    login()
else:
    top_navigation()
    if st.session_state["page"] == "タイムライン":
        timeline()
    elif st.session_state["page"] == "日報投稿":
        post_report()
    elif st.session_state["page"] == "お知らせ":
        show_notices()
    elif st.session_state["page"] == "マイページ":
        my_page()
