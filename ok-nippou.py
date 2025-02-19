import sys
import os
import time
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

# サブコーディングから必要な関数をインポート
from db_utils import init_db, authenticate_user, save_report, load_reports, load_notices, mark_notice_as_read, edit_report, delete_report

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
        st.subheader(f"{report['投稿者']} さんの日報 ({report['実行日']})")  # 投稿者と実行日
        st.write(f"🏷 **カテゴリ:** {report['カテゴリ']}")
        st.write(f"📍 **場所:** {report['場所']}")
        st.write(f"📝 **実施内容:** {report['実施内容']}")
        st.write(f"💬 **所感:** {report['所感']}")
        st.markdown(f"❤️ {report['いいね']} 👍 {report['ナイスファイト']}")
        st.write("----")

# ✅ お知らせ機能
def show_notices():
    if "user" not in st.session_state or st.session_state["user"] is None:
        st.error("ログインしてください。")
        return

    st.title("🔔 お知らせ")
    top_navigation()

    notices = load_notices()  # データベースからお知らせを取得

    for notice in notices:
        status = "未読" if notice["既読"] == 0 else "既読"
        st.subheader(f"{notice['タイトル']} - {status}")
        st.write(f"📅 {notice['日付']}")
        st.write(f"{notice['内容']}")
        if notice["既読"] == 0:
            if st.button(f"既読にする ({notice['id']})"):
                mark_notice_as_read(notice["id"])
                st.experimental_rerun()  # ページをリロードして更新

# ✅ マイページ機能
def my_page():
    if "user" not in st.session_state or st.session_state["user"] is None:
        st.error("ログインしてください。")
        return

    st.title("👤 マイページ")
    top_navigation()

    reports = load_reports()  # 自分の投稿を取得
    my_reports = [r for r in reports if r["投稿者"] == st.session_state["user"]["name"]]

    # 今週の投稿を表示
    st.subheader("📅 今週の投稿")
    now = datetime.utcnow()
    start_of_week = now - timedelta(days=now.weekday())  # 月曜日
    end_of_week = start_of_week + timedelta(days=4)  # 金曜日
    weekly_reports = [r for r in my_reports if start_of_week.date() <= datetime.strptime(r["実行日"], "%Y-%m-%d").date() <= end_of_week.date()]

    for report in weekly_reports:
        st.write(f"- {report['実行日']}: {report['カテゴリ']} / {report['場所']}")

    # 投稿編集・削除
    st.subheader("✏️ 投稿の編集・削除")
    for report in my_reports:
        st.write(f"- {report['実行日']}: {report['カテゴリ']} / {report['場所']}")
        if st.button(f"編集 ({report['id']})"):
            # 編集機能（未実装の詳細）
            st.write("編集機能の実装")
        if st.button(f"削除 ({report['id']})"):
            delete_report(report["id"])
            st.experimental_rerun()

    # データのエクスポート
    st.subheader("📤 データエクスポート")
    start_date = st.date_input("開始日")
    end_date = st.date_input("終了日")
    export_button = st.button("ダウンロード")

    if export_button:
        filtered_reports = [r for r in my_reports if start_date <= datetime.strptime(r["実行日"], "%Y-%m-%d").date() <= end_date]
        df = pd.DataFrame(filtered_reports)
        st.download_button("📥 ダウンロード", df.to_csv(index=False).encode("utf-8"), "my_reports.csv", "text/csv")

# ✅ メニュー管理
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
