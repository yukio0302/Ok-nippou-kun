import sys
import os
import time
import streamlit as st
import pandas as pd
from datetime import datetime
from db_utils import (
    init_db, authenticate_user, load_notices, save_report, load_reports,
    update_likes, add_comment, edit_report, delete_report, mark_notice_as_read
)

# ✅ SQLite 初期化（データを消さない）
init_db(keep_existing=True)

# ✅ ログイン状態を管理（ログイン状態を記録するセッション変数）
if "user" not in st.session_state:
    st.session_state["user"] = None
if "page" not in st.session_state:
    st.session_state["page"] = "ログイン"

# ✅ ページ遷移関数
def switch_page(page_name):
    st.session_state["page"] = page_name
    st.rerun()

# ✅ ナビゲーションバー（スマホ対応・少し下に表示）
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
        .nav-bar a {
            text-decoration: none;
            color: #555;
            font-size: 14px;
            text-align: center;
            flex: 1;
        }
        .nav-bar img {
            width: 28px;
            height: 28px;
        }
    </style>
    <div class="nav-bar">
        <a href="タイムライン" onclick="switch_page('タイムライン')"><img src="https://img.icons8.com/ios-filled/50/000000/home.png"/><br>タイムライン</a>
        <a href="日報投稿" onclick="switch_page('日報投稿')"><img src="https://img.icons8.com/ios-filled/50/000000/add.png"/><br>日報投稿</a>
        <a href="お知らせ" onclick="switch_page('お知らせ')"><img src="https://img.icons8.com/ios-filled/50/000000/notification.png"/><br>お知らせ</a>
        <a href="マイページ" onclick="switch_page('マイページ')"><img src="https://img.icons8.com/ios-filled/50/000000/user.png"/><br>マイページ</a>
    </div>
    """, unsafe_allow_html=True)

# ✅ ログイン機能（ログイン成功後にタイムラインへ自動遷移）
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
            time.sleep(1)  # ← ここで1秒待機（エラー防止）
            switch_page("タイムライン")  # 自動でタイムラインに遷移
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
        time.sleep(1)  # ← ここで1秒待機（即リロード防止）
        st.rerun()

# ✅ タイムライン
def timeline():
    if "user" not in st.session_state:
        st.error("ログインしてください。")
        return

    st.title("📜 タイムライン")
    top_navigation()

    reports = load_reports()

    if not reports:
        st.info("📭 表示する投稿がありません。")
        return

    for report in reports:
        st.subheader(f"{report[1]} - {report[2]}")
        st.write(f"🏷 **カテゴリ:** {report[3]}")
        st.write(f"📍 **場所:** {report[4]}")
        st.write(f"📝 **実施内容:** {report[5]}")
        st.write(f"💬 **所感:** {report[6]}")
        st.markdown(f"❤️ {report[7]} 👍 {report[8]}")

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
