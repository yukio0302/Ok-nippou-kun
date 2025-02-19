import sys
import os
import time
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

# サブコーディングから必要な関数をインポート
from db_utils import init_db, authenticate_user, save_report, load_reports, load_notices, mark_notice_as_read, edit_report, delete_report

# 画像の保存ディレクトリを設定
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# ✅ SQLite 初期化（データを消さない）
init_db(keep_existing=True)

# ✅ ログイン状態を管理
if "user" not in st.session_state:
    st.session_state["user"] = None

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
            time.sleep(1)  # ログイン成功後、少し待機
            switch_page("タイムライン")  # タイムラインへ遷移
        else:
            st.error("社員コードまたはパスワードが間違っています。")

# ✅ メニュー管理（ログイン状態を確認）
if st.session_state["user"] is None:
    login()  # 🔥 ここで login() を呼び出す
else:
    if st.session_state["page"] == "タイムライン":
        timeline()
    elif st.session_state["page"] == "日報投稿":
        post_report()
    elif st.session_state["page"] == "お知らせ":
        show_notices()
    elif st.session_state["page"] == "マイページ":
        my_page()


# ✅ ページ遷移関数
def switch_page(page_name):
    st.session_state["page"] = page_name

# ✅ 日報投稿
def post_report():
    if "user" not in st.session_state or st.session_state["user"] is None:
        st.error("ログインしてください。")
        return

    st.title("📝 日報投稿")

    category = st.text_input("📋 カテゴリ")
    location = st.text_input("📍 場所")
    content = st.text_area("📝 実施内容")
    remarks = st.text_area("💬 所感")

    # ✅ 画像アップロード機能
    uploaded_file = st.file_uploader("📷 画像をアップロード", type=["png", "jpg", "jpeg"])
    image_path = None

    if uploaded_file:
        image_path = os.path.join(UPLOAD_DIR, uploaded_file.name)
        with open(image_path, "wb") as f:
            f.write(uploaded_file.getbuffer())

    submit_button = st.button("📤 投稿する")
    if submit_button:
        save_report({
            "投稿者": st.session_state["user"]["name"],
            "実行日": datetime.utcnow().strftime("%Y-%m-%d"),
            "カテゴリ": category,
            "場所": location,
            "実施内容": content,
            "所感": remarks,
            "画像": image_path,  # 画像パスを保存
            "コメント": []
        })
        st.success("✅ 日報を投稿しました！")
        time.sleep(1)
        switch_page("タイムライン")

# ✅ タイムライン
def timeline():
    if "user" not in st.session_state or st.session_state["user"] is None:
        st.error("ログインしてください。")
        return

    st.title("📜 タイムライン")

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

        # ✅ 投稿画像を表示
        if report["画像"]:
            st.image(report["画像"], caption="投稿画像", use_column_width=True)

        st.markdown(f"❤️ {report['いいね']} 👍 {report['ナイスファイト']}")
        st.write("----")

# ✅ マイページ
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
    weekly_reports = [r for r in my_reports if start_of_week.date() <= datetime.strptime(r["実行日"], "%Y-%m-%d").date() <= end_of_week.date()]

    for report in weekly_reports:
        st.write(f"- {report['実行日']}: {report['カテゴリ']} / {report['場所']}")

    # ✅ 自分の投稿を表示（画像付き）
    st.subheader("📷 投稿履歴")
    for report in my_reports:
        st.subheader(f"{report['実行日']} - {report['カテゴリ']} / {report['場所']}")
        st.write(f"📝 {report['実施内容']}")
        if report["画像"]:
            st.image(report["画像"], caption="投稿画像", use_column_width=True)

        if st.button(f"📝 編集 ({report['id']})"):
            st.write("編集機能の実装（今後追加）")

        if st.button(f"🗑 削除 ({report['id']})"):
            delete_report(report["id"])
            st.experimental_rerun()

# ✅ お知らせ機能（そのまま維持）
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
