import streamlit as st
from datetime import datetime
import os
import json

# 初期設定
st.set_page_config(page_title="日報管理システム", layout="wide")

# JSONファイルのパス
data_file = "reports_data.json"
notifications_file = "notifications_data.json"

# データの永続化用関数
def load_reports():
    if os.path.exists(data_file):
        with open(data_file, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def save_reports(reports):
    with open(data_file, "w", encoding="utf-8") as f:
        json.dump(reports, f, ensure_ascii=False, indent=4)

def load_notifications():
    if os.path.exists(notifications_file):
        with open(notifications_file, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def save_notifications(notifications):
    with open(notifications_file, "w", encoding="utf-8") as f:
        json.dump(notifications, f, ensure_ascii=False, indent=4)

# セッション初期化
if "user" not in st.session_state:
    st.session_state["user"] = None

if "reports" not in st.session_state:
    st.session_state["reports"] = load_reports()

if "notifications" not in st.session_state:
    st.session_state["notifications"] = load_notifications()

# ログイン画面
def login():
    st.title("ログイン")
    employee_code = st.text_input("社員コード", key="employee_code_input")
    password = st.text_input("パスワード", type="password", key="password_input")
    login_button = st.button("ログイン", key="login_button")

    if login_button:
        # ユーザー認証
        if employee_code == "1234" and password == "password":
            st.session_state.user = {"code": employee_code, "name": "山田 太郎"}
            st.success("ログイン成功！")
            st.experimental_rerun()  # 画面をリロードしてセッション状態を反映
        else:
            st.error("社員コードまたはパスワードが間違っています。")

# タイムライン表示
def timeline():
    st.title("タイムライン")

    if "reports" not in st.session_state or len(st.session_state["reports"]) == 0:
        st.info("まだ投稿がありません。")
        return

    for report in reversed(st.session_state["reports"]):
        st.subheader(f"カテゴリ: {report['カテゴリ']} - {report['投稿日時']}")
        if report["得意先"]:
            st.write(f"得意先: {report['得意先']}")
        if report["タグ"]:
            st.write(f"タグ: {report['タグ']}")
        st.write(f"実施内容: {report['実施内容']}")
        if report["所感・備考"]:
            st.write(f"所感・備考: {report['所感・備考']}")
        if report["画像"]:
            try:
                st.image(report["画像"].read(), caption=report["画像"].name, use_container_width=True)
            except Exception as e:
                st.warning("画像の読み込み中にエラーが発生しました。")

# 日報投稿フォーム
def post_report():
    st.title("日報投稿")

    with st.form("report_form"):
        category = st.selectbox("カテゴリ", ["営業活動", "社内作業", "その他"], key="category")
        client = st.text_input("得意先", placeholder="営業活動の場合に記入してください", key="client") if category == "営業活動" else ""
        tags = st.text_input("タグ", placeholder="#案件, #改善提案 など", key="tags")
        content = st.text_area("実施内容", placeholder="実施した内容を記入してください", key="content")
        notes = st.text_area("所感・備考", placeholder="所感や備考を記入してください（任意）", key="notes")
        image = st.file_uploader("画像をアップロード（任意）", type=["jpg", "png", "jpeg"], key="image")
        submit = st.form_submit_button("投稿")

        if submit:
            if not content:
                st.error("実施内容は必須項目です。")
            else:
                post = {
                    "カテゴリ": category,
                    "得意先": client,
                    "タグ": tags,
                    "実施内容": content,
                    "所感・備考": notes,
                    "画像": image if image else None,
                    "投稿日時": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "投稿者": st.session_state.user["name"]
                }
                st.session_state["reports"].append(post)
                save_reports(st.session_state["reports"])

                # 通知を追加
                for report in st.session_state["reports"]:
                    if report["投稿者"] != st.session_state.user["name"]:
                        notification = {
                            "message": f"{st.session_state.user['name']} さんが新しい日報を投稿しました。",
                            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
                            "recipient": report["投稿者"]
                        }
                        st.session_state["notifications"].append(notification)
                save_notifications(st.session_state["notifications"])

                st.success("日報を投稿しました！")

# マイページ
def my_page():
    st.title("マイページ")

    my_reports = [report for report in st.session_state["reports"] if report["投稿者"] == st.session_state.user["name"]]

    if len(my_reports) == 0:
        st.info("まだ投稿がありません。")
        return

    for report in reversed(my_reports):
        st.subheader(f"カテゴリ: {report['カテゴリ']} - {report['投稿日時']}")
        if report["得意先"]:
            st.write(f"得意先: {report['得意先']}")
        if report["タグ"]:
            st.write(f"タグ: {report['タグ']}")
        st.write(f"実施内容: {report['実施内容']}")
        if report["所感・備考"]:
            st.write(f"所感・備考: {report['所感・備考']}")
        if report["画像"]:
            try:
                st.image(report["画像"].read(), caption=report["画像"].name, use_container_width=True)
            except Exception as e:
                st.warning("画像の読み込み中にエラーが発生しました。")

# お知らせ
def notifications():
    st.title("お知らせ")

    my_notifications = [note for note in st.session_state["notifications"] if note["recipient"] == st.session_state.user["name"]]

    if len(my_notifications) == 0:
        st.info("お知らせはありません。")
        return

    for note in reversed(my_notifications):
        st.write(f"[{note['timestamp']}] {note['message']}")

# メイン処理
if st.session_state.user is None:
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
