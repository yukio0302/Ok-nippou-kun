import sys
import os

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from db_utils import init_db, authenticate_user, load_notices, save_report, load_reports, mark_notice_as_read
from db_utils import update_likes, add_comment, edit_report, delete_report

# ✅ SQLite 初期化（既存データを保持）
init_db(keep_existing=True)

# ✅ ナビゲーションバー（画面上部固定）
def top_navigation():
    st.markdown("""
    <style>
        .nav-bar {
            position: fixed;
            top: 0;
            width: 100%;
            background-color: #f9f9f9;
            display: flex;
            justify-content: space-around;
            padding: 10px 0;
            border-bottom: 1px solid #ccc;
            z-index: 9999;
        }
        .nav-bar a {
            text-decoration: none;
            color: #555;
            font-size: 16px;
            text-align: center;
        }
        .nav-bar img {
            width: 30px;
            height: 30px;
        }
    </style>
    <div class="nav-bar">
        <a href="#タイムライン"><img src="https://img.icons8.com/ios-filled/50/000000/home.png"/><br>タイムライン</a>
        <a href="#日報投稿"><img src="https://img.icons8.com/ios-filled/50/000000/add.png"/><br>日報投稿</a>
        <a href="#お知らせ"><img src="https://img.icons8.com/ios-filled/50/000000/notification.png"/><br>お知らせ</a>
        <a href="#マイページ"><img src="https://img.icons8.com/ios-filled/50/000000/user.png"/><br>マイページ</a>
    </div>
    """, unsafe_allow_html=True)

# ✅ ログイン機能
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
            st.rerun()
        else:
            st.error("社員コードまたはパスワードが間違っています。")

# ✅ タイムライン（コメント＆いいね！機能）
def timeline():
    if "user" not in st.session_state or st.session_state["user"] is None:
        st.error("ログインしてください。")
        return

    st.title("📜 タイムライン")

    search_query = st.text_input("🔍 キーワード検索", placeholder="カテゴリ、実施内容、所感などで検索")
    reports = load_reports()

    if search_query:
        reports = [r for r in reports if search_query.lower() in str(r).lower()]

    for report in reports:
        with st.container():
            st.subheader(f"{report[1]} - {report[2]}")
            st.write(f"🏷 **カテゴリ:** {report[3]}")
            st.write(f"📍 **場所:** {report[4]}")
            st.write(f"📝 **実施内容:** {report[5]}")
            st.write(f"💬 **所感:** {report[6]}")
            st.markdown(f"❤️ {report[7]} 👍 {report[8]}")

            # いいねボタン
            col1, col2 = st.columns(2)
            with col1:
                if st.button("❤️ いいね！", key=f"like_{report[0]}"):
                    update_likes(report[0], "like")
                    st.experimental_rerun()
            with col2:
                if st.button("👍 ナイスファイト！", key=f"nice_{report[0]}"):
                    update_likes(report[0], "nice")
                    st.experimental_rerun()

            # コメント表示
            st.write("💬 **コメント一覧:**")
            for comment in report[9]:
                st.write(f"・{comment}")

            # コメント入力＆送信
            comment_text = st.text_input("コメントを書く", key=f"comment_input_{report[0]}")
            if st.button("📤 コメント送信", key=f"send_comment_{report[0]}"):
                if comment_text.strip():
                    add_comment(report[0], f"{st.session_state['user']['name']}: {comment_text.strip()}")
                    st.experimental_rerun()
                else:
                    st.warning("コメントを入力してください！")

    top_navigation()

# ✅ 日報投稿（画像対応）
def post_report():
    if "user" not in st.session_state or st.session_state["user"] is None:
        st.error("ログインしてください。")
        return

    st.title("📝 日報投稿")

    category = st.text_input("📋 カテゴリ")
    location = st.text_input("📍 場所")
    content = st.text_area("📝 実施内容")
    remarks = st.text_area("💬 所感")
    image = st.file_uploader("📷 添付画像", type=["png", "jpg", "jpeg"])

    submit_button = st.button("📤 投稿する")
    if submit_button:
        image_data = image.read() if image else None
        save_report({
            "投稿者": st.session_state["user"]["name"],
            "実行日": datetime.utcnow().strftime("%Y-%m-%d"),
            "カテゴリ": category,
            "場所": location,
            "実施内容": content,
            "所感": remarks,
            "コメント": [],
            "画像": image_data
        })
        st.success("✅ 日報を投稿しました！")
        st.rerun()

# ✅ マイページ（投稿修正・削除対応）
def my_page():
    if "user" not in st.session_state or st.session_state["user"] is None:
        st.error("ログインしてください。")
        return

    st.title("👤 マイページ")

    user_reports = [r for r in load_reports() if r[1] == st.session_state["user"]["name"]]

    for report in user_reports:
        with st.container():
            st.subheader(f"{report[1]} - {report[2]}")
            st.write(f"🏷 **カテゴリ:** {report[3]}")
            st.write(f"📍 **場所:** {report[4]}")
            st.write(f"📝 **実施内容:** {report[5]}")
            st.write(f"💬 **所感:** {report[6]}")
            if st.button("✏️ 修正", key=f"edit_{report[0]}"):
                edit_report(report)
                st.success("投稿を修正しました。")
                st.rerun()
            if st.button("🗑️ 削除", key=f"delete_{report[0]}"):
                delete_report(report[0])
                st.success("投稿を削除しました。")
                st.rerun()

    start_date = st.date_input("📅 CSV出力開始日", datetime.utcnow() - timedelta(days=7))
    end_date = st.date_input("📅 CSV出力終了日", datetime.utcnow())

    csv_data = pd.DataFrame(user_reports, columns=["投稿者", "実行日", "カテゴリ", "場所", "実施内容", "所感", "いいね", "ナイスファイト", "コメント"])
    csv_data = csv_data[
        (csv_data["実行日"] >= start_date.strftime("%Y-%m-%d")) &
        (csv_data["実行日"] <= end_date.strftime("%Y-%m-%d"))
    ]

    st.download_button("📥 CSVダウンロード", csv_data.to_csv(index=False).encode("utf-8"), "my_report.csv", "text/csv")

# ✅ お知らせ
def show_notices():
    if "user" not in st.session_state or st.session_state["user"] is None:
        st.error("ログインしてください。")
        return

    st.title("🔔 お知らせ")

    notices = load_notices()
    for notice in notices:
        with st.container():
            st.subheader(f"📢 {notice[2]}")
            st.write(f"📅 **日付**: {notice[3]}")
            st.write(f"📝 **内容:** {notice[1]}")
            if st.button("✅ 既読にする", key=f"mark_read_{notice[0]}"):
                mark_notice_as_read(notice[0])
                st.rerun()

# ✅ メニュー管理
if "user" not in st.session_state:
    st.session_state["user"] = None

if st.session_state["user"] is None:
    login()
else:
    top_navigation()
    menu = st.sidebar.radio("メニュー", ["タイムライン", "日報投稿", "お知らせ", "マイページ"])
    
    if menu == "タイムライン":
        timeline()
    elif menu == "日報投稿":
        post_report()
    elif menu == "お知らせ":
        show_notices()
    elif menu == "マイページ":
        my_page()
