import streamlit as st
from datetime import datetime
import json
import os

# ファイルパス
USERS_FILE = "users_data.json"
REPORTS_FILE = "reports_data.json"

# 初期設定
st.set_page_config(page_title="日報管理システム", layout="wide")

# データロード
def load_users():
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def save_users(users):
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, ensure_ascii=False, indent=4)

def load_reports():
    if os.path.exists(REPORTS_FILE):
        with open(REPORTS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def save_reports(reports):
    with open(REPORTS_FILE, "w", encoding="utf-8") as f:
        json.dump(reports, f, ensure_ascii=False, indent=4)

# セッション初期化
if "user" not in st.session_state:
    st.session_state["user"] = None
if "reports" not in st.session_state:
    st.session_state["reports"] = load_reports()

# ログイン画面
def login():
    st.title("ログイン")
    user_code = st.text_input("社員コード", key="user_code_input")
    password = st.text_input("パスワード", type="password", key="password_input")
    login_button = st.button("ログイン", key="login_button")

    if login_button:
        users = load_users()
        for user in users:
            if user["code"] == user_code and user["password"] == password:
                st.session_state["user"] = user
                st.success(f"ログイン成功！ようこそ、{user['name']}さん！")
                return
        st.error("社員コードまたはパスワードが間違っています。")

# 通知を追加
def add_notification(target_user, message, link_to_post=None):
    users = load_users()
    for user in users:
        if user["name"] == target_user:
            if "notifications" not in user:
                user["notifications"] = []
            user["notifications"].append({
                "message": message,
                "link": link_to_post,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "read": False
            })
    save_users(users)

# お知らせ機能
def notifications():
    st.title("お知らせ")
    user = st.session_state["user"]
    if "notifications" not in user or len(user["notifications"]) == 0:
        st.info("現在、お知らせはありません。")
        return

    for idx, notification in enumerate(reversed(user["notifications"])):
        with st.container():
            is_read = notification["read"]
            message_style = "font-weight: bold;" if not is_read else ""
            st.markdown(
                f"""
                <div style="background-color: #f9f9f9; padding: 10px; border-radius: 5px; margin-bottom: 10px;">
                    <p style="{message_style}">🔔 {notification['message']}</p>
                    <small>{notification['timestamp']}</small>
                </div>
                """,
                unsafe_allow_html=True,
            )
            col1, col2 = st.columns([1, 3])
            with col1:
                if not is_read:
                    if st.button("既読にする", key=f"mark_read_{idx}"):
                        notification["read"] = True
                        save_users(load_users())
                        st.experimental_rerun()
            with col2:
                if notification["link"]:
                    if st.button("詳細を見る", key=f"view_detail_{idx}"):
                        st.write(f"投稿へのリンク: {notification['link']}")

# タイムライン表示
def timeline():
    st.title("タイムライン")
    if len(st.session_state["reports"]) == 0:
        st.info("まだ投稿がありません。")
        return

    for idx, report in enumerate(reversed(st.session_state["reports"])):
        with st.container():
            st.subheader(f"{report['投稿者']} - {report['投稿日時']}")
            st.write(report["実施内容"])
            st.text(f"いいね！ {len(report['いいね'])} / ナイスファイト！ {len(report['ナイスファイト'])}")
            
            col1, col2, col3 = st.columns(3)
            with col1:
                if st.button("いいね！", key=f"like_{idx}"):
                    if st.session_state["user"]["name"] not in report["いいね"]:
                        report["いいね"].append(st.session_state["user"]["name"])
                        add_notification(report["投稿者"], f"{st.session_state['user']['name']} さんが「いいね！」しました。", link_to_post=f"投稿ID: {idx}")
                        save_reports(st.session_state["reports"])
            with col2:
                if st.button("ナイスファイト！", key=f"nice_fight_{idx}"):
                    if st.session_state["user"]["name"] not in report["ナイスファイト"]:
                        report["ナイスファイト"].append(st.session_state["user"]["name"])
                        add_notification(report["投稿者"], f"{st.session_state['user']['name']} さんが「ナイスファイト！」しました。", link_to_post=f"投稿ID: {idx}")
                        save_reports(st.session_state["reports"])
            with col3:
                st.button("コメントする", key=f"comment_{idx}")

# 日報投稿フォーム
def post_report():
    st.title("日報投稿")
    with st.form("report_form"):
        category = st.selectbox("カテゴリ", ["営業活動", "社内作業", "その他"], key="category")
        tags = st.text_input("タグ", placeholder="#案件, #改善提案 など", key="tags")
        content = st.text_area("実施内容", placeholder="実施した内容を記入してください", key="content")
        notes = st.text_area("所感・備考", placeholder="所感や備考を記入してください（任意）", key="notes")
        submit = st.form_submit_button("投稿")
        if submit:
            if not content:
                st.error("実施内容は必須項目です。")
            else:
                new_report = {
                    "投稿者": st.session_state["user"]["name"],
                    "カテゴリ": category,
                    "タグ": tags,
                    "実施内容": content,
                    "所感・備考": notes,
                    "投稿日時": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "いいね": [],
                    "ナイスファイト": []
                }
                st.session_state["reports"].append(new_report)
                save_reports(st.session_state["reports"])
                st.success("日報を投稿しました！")

# マイページ
def my_page():
    st.title("マイページ")
    st.write(f"ログインユーザー: {st.session_state['user']['name']}")
    st.write("お気に入り投稿:")
    if "favorites" in st.session_state["user"] and st.session_state["user"]["favorites"]:
        for favorite in st.session_state["user"]["favorites"]:
            st.write(f"- {favorite['実施内容']} (投稿日時: {favorite['投稿日時']})")
    else:
        st.write("お気に入り登録がありません。")

# お知らせ
def notifications():
    st.title("お知らせ")
    st.write("お知らせ機能は未実装です。")

# メイン処理
if st.session_state["user"] is None:
    login()
else:
    menu = st.sidebar.radio("メニュー", ["タイムライン", "日報投稿", "マイページ", "お知らせ"])
    if menu == "タイムライン":
        timeline()
    elif menu == "日報投稿":
        post_report()
    elif menu == "マイページ":
        my_page()
    elif menu == "お知らせ":
        notifications()
