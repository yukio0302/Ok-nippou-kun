import sys
import os
import time
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

# サブコーディングから必要な関数をインポート
from db_utils import init_db, authenticate_user, save_report, load_reports, load_notices, mark_notice_as_read, edit_report, delete_report, update_reaction, save_comment

# ✅ SQLite 初期化（データを消さない）
init_db(keep_existing=True)

# ✅ ログイン状態を管理
if "user" not in st.session_state:
    st.session_state["user"] = None
if "page" not in st.session_state:
    st.session_state["page"] = "ログイン"

# ✅ ページ遷移関数（修正済み）
def switch_page(page_name):
    """ページを切り替える（即時リロードはなし！）"""
    st.session_state["page"] = page_name
# ✅ ナビゲーションバー（修正済み）
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
    </style>
    """, unsafe_allow_html=True)

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        if st.button("🏠 タイムライン"):
            st.session_state["page"] = "タイムライン"
            st.rerun()  # ✅ ここでリロードする！
    with col2:
        if st.button("✏️ 日報投稿"):
            st.session_state["page"] = "日報投稿"
            st.rerun()
    with col3:
        if st.button("🔔 お知らせ"):
            st.session_state["page"] = "お知らせ"
            st.rerun()
    with col4:
        if st.button("👤 マイページ"):
            st.session_state["page"] = "マイページ"
            st.rerun()

# ✅ ログイン機能（修正済み）
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
            time.sleep(1)
            st.session_state["page"] = "タイムライン"
            st.rerun()  # ✅ ここで即リロード！
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
        time.sleep(1)
        switch_page("タイムライン")

# ✅ タイムライン（コメント機能修正）
def timeline():
    if "user" not in st.session_state or st.session_state["user"] is None:
        st.error("ログインしてください。")
        return

    st.title("📜 タイムライン")
    top_navigation()

    reports = load_reports()

    if not reports:
        st.info("📭 表示する投稿がありません。")
        return

    for report in reports:
        st.subheader(f"{report['投稿者']} さんの日報 ({report['実行日']})")
        st.write(f"🏷 **カテゴリ:** {report['カテゴリ']}")
        st.write(f"📍 **場所:** {report['場所']}")
        st.write(f"📝 **実施内容:** {report['実施内容']}")
        st.write(f"💬 **所感:** {report['所感']}")

        # ✅ いいね！＆ナイスファイト！ボタン
        col1, col2 = st.columns(2)
        with col1:
            if st.button(f"❤️ {report['いいね']} いいね！", key=f"like_{report['id']}"):
                update_reaction(report["id"], "いいね")
                st.rerun()
        with col2:
            if st.button(f"👍 {report['ナイスファイト']} ナイスファイト！", key=f"nice_{report['id']}"):
                update_reaction(report["id"], "ナイスファイト")
                st.rerun()

        # ✅ コメント欄
        with st.expander("💬 コメントを見る・追加する"):
            if report["コメント"]:
                for c in report["コメント"]:
                    st.write(f"👤 {c['投稿者']} ({c['日時']}): {c['コメント']}")

            # ✅ IDが `None` の場合のチェック（防止策）
            if report.get("id") is None:
                st.error("⚠️ 投稿の ID が見つかりません。")
                continue

            # ✅ ログインユーザー名の取得
            commenter_name = st.session_state["user"]["name"] if st.session_state["user"] else "匿名"

            # ✅ テキストエリアのキーをユニークに（バグ防止）
            new_comment = st.text_area(f"✏️ {commenter_name} さんのコメント", key=f"comment_{report['id']}")

            if st.button("📤 コメントを投稿", key=f"submit_comment_{report['id']}"):
                if new_comment and new_comment.strip():
                    print(f"🛠️ コメント投稿デバッグ: report_id={report['id']}, commenter={commenter_name}, comment={new_comment}")
save_comment(report["id"], commenter_name, new_comment)
                    save_comment(report["id"], commenter_name, new_comment)
                    st.success("✅ コメントを投稿しました！")
                    st.rerun()
                else:
                    st.warning("⚠️ 空白のコメントは投稿できません！")

        st.write("----")

# ✅ お知らせ
def show_notices():
    if "user" not in st.session_state or st.session_state["user"] is None:
        st.error("ログインしてください。")
        return

    st.title("🔔 お知らせ")
    top_navigation()

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

# ✅ マイページ
def my_page():
    if "user" not in st.session_state or st.session_state["user"] is None:
        st.error("ログインしてください。")
        return

    st.title("👤 マイページ")
    top_navigation()

    reports = load_reports()
    my_reports = [r for r in reports if r["投稿者"] == st.session_state["user"]["name"]]

    st.subheader("📅 今週の投稿")
    now = datetime.utcnow()
    start_of_week = now - timedelta(days=now.weekday())
    end_of_week = start_of_week + timedelta(days=4)
    weekly_reports = [r for r in my_reports if start_of_week.date() <= datetime.strptime(r["実行日"], "%Y-%m-%d").date() <= end_of_week.date()]

    for report in weekly_reports:
        st.write(f"- {report['実行日']}: {report['カテゴリ']} / {report['場所']}")

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
