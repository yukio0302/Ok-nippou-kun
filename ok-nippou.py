import streamlit as st
import csv
from datetime import datetime

# ファイル名の設定
REPORTS_FILE = "reports.csv"
NOTICES_FILE = "notices.csv"

# 初回実行時にCSVファイルを作成
def init_csv(file_name, headers):
    try:
        with open(file_name, "x", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(headers)
    except FileExistsError:
        pass  # すでにファイルがある場合はスルー

init_csv(REPORTS_FILE, ["投稿者", "カテゴリ", "タグ", "実施内容", "所感・備考", "投稿日時", "いいね", "ナイスファイト"])
init_csv(NOTICES_FILE, ["タイトル", "日付", "内容"])

# データの保存と取得
def save_report(user, category, tags, content, notes):
    with open(REPORTS_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([user, category, tags, content, notes, datetime.now().strftime("%Y-%m-%d %H:%M"), 0, 0])

def load_reports():
    with open(REPORTS_FILE, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        return list(reader)[1:]  # ヘッダーを除く

def save_notice(title, content):
    with open(NOTICES_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([title, datetime.now().strftime("%Y-%m-%d"), content])

def load_notices():
    with open(NOTICES_FILE, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        return list(reader)[1:]  # ヘッダーを除く

# Streamlit 初期設定
st.set_page_config(page_title="日報管理システム", layout="wide")

if "user" not in st.session_state:
    st.session_state["user"] = None

# ログイン機能
def login():
    st.title("ログイン")
    user_name = st.text_input("名前", key="user_name_input")
    login_button = st.button("ログイン", key="login_button")
    if login_button and user_name:
        st.session_state["user"] = user_name
        st.success(f"ログイン成功！ようこそ、{user_name}さん！")

# 日報投稿
def post_report():
    st.title("日報投稿")
    with st.form("report_form"):
        category = st.selectbox("カテゴリ", ["営業活動", "社内作業", "その他"])
        tags = st.text_input("タグ", placeholder="#案件, #改善提案 など")
        content = st.text_area("実施内容", placeholder="実施した内容を記入してください")
        notes = st.text_area("所感・備考", placeholder="所感や備考を記入してください（任意）")
        submit = st.form_submit_button("投稿")

        if submit:
            if not content:
                st.error("実施内容は必須項目です。")
            else:
                save_report(st.session_state["user"], category, tags, content, notes)
                st.success("日報を投稿しました！")

# タイムライン
def timeline():
    st.title("タイムライン")
    reports = load_reports()
    if not reports:
        st.info("まだ投稿がありません。")
        return
    
    for idx, report in enumerate(reports):
        with st.container():
            st.subheader(f"{report[0]} - {report[5]}")
            st.write(report[3])
            st.text(f"いいね！ {report[6]} / ナイスファイト！ {report[7]}")

# マイページ
def my_page():
    st.title("マイページ")
    user = st.session_state["user"]
    reports = load_reports()
    user_reports = [r for r in reports if r[0] == user]
    
    if not user_reports:
        st.info("あなたの投稿はまだありません。")
        return
    
    st.subheader(f"{user} さんの投稿一覧")
    for report in user_reports:
        st.write(f"{report[5]} - {report[3]}")
    
    total_likes = sum(int(r[6]) for r in user_reports)
    total_nice_fights = sum(int(r[7]) for r in user_reports)
    st.text(f"総いいね数: {total_likes} / 総ナイスファイト数: {total_nice_fights}")

# お知らせ
def notice():
    st.title("お知らせ")
    notices = load_notices()
    
    if not notices:
        st.info("現在お知らせはありません。")
        return
    
    for notice in notices:
        st.subheader(f"{notice[0]} - {notice[1]}")
        st.write(notice[2])

# お知らせ投稿（管理者向け）
def post_notice():
    st.title("お知らせ投稿")
    with st.form("notice_form"):
        title = st.text_input("タイトル", key="notice_title")
        content = st.text_area("内容", key="notice_content")
        submit = st.form_submit_button("投稿")

        if submit:
            if not title or not content:
                st.error("タイトルと内容は必須です。")
            else:
                save_notice(title, content)
                st.success("お知らせを投稿しました！")

# メイン処理
if st.session_state["user"] is None:
    login()
else:
    menu = st.sidebar.radio("メニュー", ["タイムライン", "日報投稿", "マイページ", "お知らせ", "お知らせ投稿"])
    if menu == "タイムライン":
        timeline()
    elif menu == "日報投稿":
        post_report()
    elif menu == "マイページ":
        my_page()
    elif menu == "お知らせ":
        notice()
    elif menu == "お知らせ投稿":
        post_notice()
