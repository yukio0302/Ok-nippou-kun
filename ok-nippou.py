import streamlit as st
from datetime import datetime, timedelta
import json
import os

# データファイルのパス
data_file = "reports_data.json"
users_file = "users_data.json"

# データの読み込み・保存用関数
def load_data(file_path):
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def save_data(file_path, data):
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# 初期化
if "reports" not in st.session_state:
    st.session_state["reports"] = load_data(data_file)

if "users" not in st.session_state:
    st.session_state["users"] = load_data(users_file)

if "user" not in st.session_state:
    st.session_state["user"] = None  # ログイン情報を保持

if "login_success" not in st.session_state:
    st.session_state["login_success"] = False  # ログイン成功フラグ

# ログイン機能
def login():
    st.title("ログイン")
    username = st.text_input("ユーザー名", key="username")
    password = st.text_input("パスワード", type="password", key="password")

    if st.button("ログイン"):
        for user in st.session_state["users"]:
            if user["name"] == username and user["password"] == password:
                st.session_state["user"] = user
                st.session_state["login_success"] = True
                st.success(f"ログイン成功！ようこそ、{username}さん！")
                st.experimental_rerun()
        st.error("ユーザー名またはパスワードが正しくありません。")

# ログアウト機能
def logout():
    st.session_state["user"] = None
    st.session_state["login_success"] = False
    st.experimental_rerun()

# 日報投稿
def post_report():
    st.title("日報投稿")
    tag = st.text_input("タグ (例: #進捗, #トラブル対応)", key="tag")
    category = st.text_input("カテゴリ (例: 開発, 営業, 企画)", key="category")
    content = st.text_area("実施内容", key="content")

    if st.button("投稿"):
        if not tag or not category or not content:
            st.error("すべての項目を入力してください。")
            return

        new_report = {
            "投稿者": st.session_state["user"]["name"],
            "タグ": tag,
            "カテゴリ": category,
            "実施内容": content,
            "投稿日時": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "いいね": [],
            "ナイスファイト": [],
            "コメント": [],
        }
        st.session_state["reports"].append(new_report)
        save_data(data_file, st.session_state["reports"])
        st.success("日報を投稿しました！")

# マイページ
def my_page():
    st.title("マイページ")

    # 自分の投稿を表示
    st.header("自分の投稿")
    user_reports = [
        report for report in st.session_state["reports"]
        if report["投稿者"] == st.session_state["user"]["name"]
    ]

    if not user_reports:
        st.info("まだ投稿がありません。")
    else:
        for report in reversed(user_reports):
            st.markdown(f"""
                <div style="border: 1px solid #ddd; padding: 10px; border-radius: 5px; margin-bottom: 10px;">
                    <b>{report['投稿日時']}</b>
                    <p>{report['実施内容']}</p>
                    <small>カテゴリ: {report['カテゴリ']} | タグ: {report['タグ']}</small>
                </div>
            """, unsafe_allow_html=True)

    # お気に入りの投稿
    st.header("お気に入り")
    if "お気に入り" in st.session_state["user"] and st.session_state["user"]["お気に入り"]:
        for index in st.session_state["user"]["お気に入り"]:
            report = st.session_state["reports"][index]
            st.markdown(f"""
                <div style="border: 1px solid #ddd; padding: 10px; border-radius: 5px; margin-bottom: 10px;">
                    <b>{report['投稿者']} - {report['投稿日時']}</b>
                    <p>{report['実施内容']}</p>
                </div>
            """, unsafe_allow_html=True)
    else:
        st.info("まだお気に入りが登録されていません。")

# お知らせ
def notifications():
    st.title("お知らせ")

    user_notifications = st.session_state["user"].get("通知", [])
    if not user_notifications:
        st.info("お知らせはありません。")
        return

    for notification in reversed(user_notifications):
        st.markdown(f"""
            <div style="border: 1px solid #ddd; padding: 10px; border-radius: 5px; margin-bottom: 10px;">
                <b>{notification['内容']}</b>
                <p>{notification['詳細']}</p>
                <small>{notification['日時']}</small>
            </div>
        """, unsafe_allow_html=True)

# タイムライン
def timeline():
    st.title("タイムライン")

    reports = st.session_state["reports"]
    if not reports:
        st.info("投稿がありません。")
        return

    for report_index, report in enumerate(reversed(reports)):
        with st.container():
            st.markdown(f"""
                <div style="border: 1px solid #ddd; padding: 15px; margin-bottom: 10px; border-radius: 5px;">
                    <b>{report['投稿者']}</b> ・ {report['投稿日時']}
                    <p>{report['実施内容']}</p>
                    <small>カテゴリ: {report['カテゴリ']} | タグ: {report['タグ']}</small>
                </div>
            """, unsafe_allow_html=True)

            col1, col2, col3, col4 = st.columns(4)
            with col1:
                if st.button("💬 コメント", key=f"comment_{report_index}"):
                    st.session_state["active_comment"] = report_index
            with col2:
                if st.button(f"❤️ {len(report.get('いいね', []))}", key=f"like_{report_index}"):
                    if st.session_state["user"]["name"] in report.get("いいね", []):
                        report["いいね"].remove(st.session_state["user"]["name"])
                    else:
                        report.setdefault("いいね", []).append(st.session_state["user"]["name"])
                    save_data(data_file, st.session_state["reports"])
                    st.experimental_rerun()
            with col3:
                if st.button(f"🔥 {len(report.get('ナイスファイト', []))}", key=f"fight_{report_index}"):
                    if st.session_state["user"]["name"] in report.get("ナイスファイト", []):
                        report["ナイスファイト"].remove(st.session_state["user"]["name"])
                    else:
                        report.setdefault("ナイスファイト", []).append(st.session_state["user"]["name"])
                    save_data(data_file, st.session_state["reports"])
                    st.experimental_rerun()
            with col4:
                if st.button("⭐", key=f"favorite_{report_index}"):
                    st.success("お気に入りに追加しました！")

# アプリ全体の表示
if st.session_state["user"]:
    with st.sidebar:
        st.write(f"ログイン中: {st.session_state['user']['name']}")
        if st.button("タイムライン"):
            st.session_state["active_page"] = "timeline"
            st.experimental_rerun()
        if st.button("日報投稿"):
            st.session_state["active_page"] = "post_report"
            st.experimental_rerun()
        if st.button("マイページ"):
            st.session_state["active_page"] = "my_page"
            st.experimental_rerun()
        if st.button("お知らせ"):
            st.session_state["active_page"] = "notifications"
            st.experimental_rerun()
        if st.button("ログアウト"):
            logout()

    # ページ切り替え
    if st.session_state.get("active_page") == "timeline":
        timeline()
    elif st.session_state.get("active_page") == "post_report":
        post_report()
    elif st.session_state.get("active_page") == "my_page":
        my_page()
    elif st.session_state.get("active_page") == "notifications":
        notifications()
else:
    login()
