import sys
import os
import time
import streamlit as st
import pandas as pd
from datetime import datetime
from db_utils import (init_db, authenticate_user, load_notices, save_report, load_reports,
    update_likes, add_comment, edit_report, delete_report, mark_notice_as_read
)


# ✅ SQLite 初期化（データを消さない）
init_db(keep_existing=True)

# ✅ ログイン状態を管理（ログイン状態を記録するセッション変数）
if "user" not in st.session_state:
    st.session_state["user"] = None
if "page" not in st.session_state:
    st.session_state["page"] = "ログイン"

# ✅ ページ遷移関数（修正版：rerun削除）
def switch_page(page_name):
    """
    セッション状態のページを変更する関数。
    """
    st.session_state["page"] = page_name

# ✅ ナビゲーションバー
def top_navigation():
    st.markdown("""
    <style>
        .nav-bar {
            position: fixed;
            top: 60px;
            left: 0;
            width: 100%;
            background-color: #ffffff;
            display: flex;
            justify-content: space-around;
            padding: 10px 0;
            border-top: 1px solid #ccc;
            box-shadow: 0 -2px 5px rgba(0, 0, 0, 0.1);
            z-index: 9999;
        }
        .nav-item {
            text-align: center;
            flex: 1;
        }
        .nav-item button {
            background: none;
            border: none;
            color: #555;
            font-size: 14px;
            cursor: pointer;
            padding: 5px 10px;
        }
        .nav-item button:hover {
            color: #000;
        }
        .nav-item img {
            width: 28px;
            height: 28px;
        }
    </style>
    """, unsafe_allow_html=True)

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        if st.button("🏠 タイムライン"):
            switch_page("タイムライン")
    with col2:
        if st.button("✏️ 日報投稿"):
            switch_page("日報投稿")
    with col3:
        if st.button("🔔 お知らせ"):
            switch_page("お知らせ")
    with col4:
        if st.button("👤 マイページ"):
            switch_page("マイページ")

# ✅ ログイン機能（ログイン成功後にタイムラインへ遷移）
def login():
    st.title("🔑 ログイン")
    employee_code = st.text_input("社員コード")
    password = st.text_input("パスワード", type="password")
    login_button = st.button("ログイン")

    if login_button:
        user = authenticate_user(employee_code, password)
        if user:
            st.session_state["user"] = user
            st.success(f"ようこそ、{user['name']} さん！（{', '.join(user['depart'])}）")
            time.sleep(1)  # ログイン成功後少し待機
            switch_page("タイムライン")  # タイムラインへ遷移
        else:
            st.error("社員コードまたはパスワードが間違っています。")

# ✅ 日報投稿
def post_report():
    if "user" not in st.session_state or st.session_state["user"] is None:
        st.error("ログインしてください。")
        return

    st.title("📝 日報投稿")
    top_navigation()

    category = st.text_input("📋 カテゴリ")
    location = st.text_input("📍 場所")
    content = st.text_area("📝 実施内容")
    remarks = st.text_area("💬 所感")

    submit_button = st.button("📤 投稿する")
    if submit_button:
        save_report({
            "投稿者": st.session_state["user"]["name"],
            "実行日": datetime.utcnow().strftime("%Y-%m-%d"),
            "カテゴリ": category,
            "場所": location,
            "実施内容": content,
            "所感": remarks,
            "コメント": []
        })
        st.success("✅ 日報を投稿しました！")
        time.sleep(1)  # 投稿成功メッセージを表示するため少し待機
        switch_page("タイムライン")  # 投稿後にタイムラインへ遷移

# ✅ タイムライン
def timeline():
    if "user" not in st.session_state or st.session_state["user"] is None:
        st.error("ログインしてください。")
        return

    st.title("📜 タイムライン")
    top_navigation()

    reports = load_reports()  # データベースから日報を取得

    if not reports:
        st.info("📭 表示する投稿がありません。")
        return

    for report in reports:
        st.subheader(f"{report[1]} さんの日報 ({report[2]})")  # 投稿者と実行日
        st.write(f"🏷 **カテゴリ:** {report[3]}")
        st.write(f"📍 **場所:** {report[4]}")
        st.write(f"📝 **実施内容:** {report[5]}")
        st.write(f"💬 **所感:** {report[6]}")
        st.markdown(f"❤️ {report[7]} 👍 {report[8]}")
        st.write("----")

# ✅ メニュー管理（ログイン後に自動でタイムラインへ）
if st.session_state["user"] is None:
    login()
else:
    if st.session_state["page"] == "タイムライン":
        timeline()
    elif st.session_state["page"] == "日報投稿":
        post_report()
    elif st.session_state["page"] == "お知らせ":
        show_notices()
    elif st.session_state["page"] == "マイページ":
        my_page()
