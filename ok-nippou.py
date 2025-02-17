import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from db_utils import init_db, authenticate_user, load_notices, save_report, load_reports, mark_notice_as_read, update_likes

# ✅ SQLite 初期化
init_db()

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

# ✅ タイムライン（いいね！とナイスファイトを追加）
def timeline():
    if "user" not in st.session_state or st.session_state["user"] is None:
        st.error("ログインしてください。")
        return

    st.title("📜 タイムライン")

    reports = load_reports()

    for report in reports:
        with st.container():
            st.subheader(f"{report['投稿者']} - {report['実行日']}")
            st.write(f"🏷 カテゴリ: {report['カテゴリ']}")
            st.write(f"📍 場所: {report['場所']}")
            st.write(f"📝 **実施内容:** {report['実施内容']}")
            st.write(f"💬 **所感:** {report['所感']}")
            st.text(f"👍 いいね！ {report['いいね']} / 🎉 ナイスファイト！ {report['ナイスファイト']}")

            col1, col2 = st.columns(2)
            with col1:
                if st.button("👍 いいね！", key=f"like_{report['id']}"):
                    update_likes(report["id"], "like")
                    st.rerun()
            with col2:
                if st.button("🎉 ナイスファイト！", key=f"nice_{report['id']}"):
                    update_likes(report["id"], "nice")
                    st.rerun()

# ✅ 日報投稿（ボタンの連打防止）
def post_report():
    if "user" not in st.session_state or st.session_state["user"] is None:
        st.error("ログインしてください。")
        return

    st.title("📝 日報投稿")

    category = st.text_input("📋 カテゴリ")
    location = st.text_input("📍 場所")
    content = st.text_area("📝 実施内容")
    remarks = st.text_area("💬 所感")

    submit_button = st.button("📤 投稿する", disabled=st.session_state.get("posting", False))

    if submit_button:
        st.session_state["posting"] = True
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
        st.session_state["posting"] = False
        st.rerun()

# ✅ メニュー管理
if "user" not in st.session_state:
    st.session_state["user"] = None

if st.session_state["user"] is None:
    login()
else:
    menu = st.sidebar.radio("メニュー", ["タイムライン", "日報投稿"])
    
    if menu == "タイムライン":
        timeline()
    elif menu == "日報投稿":
        post_report()
