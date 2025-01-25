import streamlit as st
from datetime import datetime, timedelta
import os
import json

# 初期設定
st.set_page_config(page_title="日報管理システム", layout="wide")

# JSONファイルのパス
data_file = "reports_data.json"

# セッション永続化の保持時間（1週間）
SESSION_DURATION = timedelta(days=7)

# 初期データ設定
if "user" not in st.session_state:
    st.session_state["user"] = None

if "reports" not in st.session_state:
    st.session_state["reports"] = []

if "last_login" not in st.session_state:
    st.session_state["last_login"] = None

if "notifications" not in st.session_state:
    st.session_state["notifications"] = []

# ログイン画面
def login():
    st.title("ログイン")
    employee_code = st.text_input("社員コード", key="employee_code_input")
    password = st.text_input("パスワード", type="password", key="password_input")
    login_button = st.button("ログイン", key="login_button")

    if login_button:
        # 仮のユーザーデータ
        user = {"code": "901179", "password": "okanaga", "name": "野村幸男"}

        if employee_code == user["code"] and password == user["password"]:
            st.session_state.user = user
            st.session_state.last_login = datetime.now()
            st.success(f"ログイン成功！ようこそ、{user['name']}さん！")
        else:
            st.error("社員コードまたはパスワードが間違っています。")


# タイムライン（省略部分あり）
def timeline():
    st.title("タイムライン")
    st.write("検索機能や投稿一覧を表示します。")


# 日報投稿フォーム（省略部分あり）
def post_report():
    st.title("日報投稿")
    st.write("日報を投稿する機能です。")


# マイページ（省略部分あり）
def my_page():
    st.title("マイページ")
    st.write("自分の投稿を確認・編集・削除する機能です。")


# お知らせ（省略部分あり）
def notifications():
    st.title("お知らせ")
    st.write("通知機能です。")


# メイン処理
if st.session_state.user is None:
    if st.session_state.last_login and datetime.now() - st.session_state.last_login < SESSION_DURATION:
        st.session_state.user = {"code": "901179", "name": "野村幸男"}
    else:
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
