import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

# Google Sheets API 認証設定
SCOPE = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
CREDS_FILE = "serviceAccountKey.json"  # 認証キーのJSONファイル
SHEET_NAME = "日報管理"  # スプレッドシート名
NOTICE_SHEET_NAME = "お知らせ"  # お知らせ用スプレッドシート名

def get_sheet(sheet_name):
    creds = ServiceAccountCredentials.from_json_keyfile_name(CREDS_FILE, SCOPE)
    client = gspread.authorize(creds)
    return client.open(sheet_name).sheet1

sheet = get_sheet(SHEET_NAME)
notice_sheet = get_sheet(NOTICE_SHEET_NAME)

# Streamlit 初期設定
st.set_page_config(page_title="日報管理システム", layout="wide")

# ログイン画面
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
        category = st.selectbox("カテゴリ", ["営業活動", "社内作業", "その他"], key="category")
        tags = st.text_input("タグ", placeholder="#案件, #改善提案 など", key="tags")
        content = st.text_area("実施内容", placeholder="実施した内容を記入してください", key="content")
        notes = st.text_area("所感・備考", placeholder="所感や備考を記入してください（任意）", key="notes")
        submit = st.form_submit_button("投稿")
        
        if submit:
            if not content:
                st.error("実施内容は必須項目です。")
            else:
                new_report = [
                    st.session_state["user"],
                    category,
                    tags,
                    content,
                    notes,
                    datetime.now().strftime("%Y-%m-%d %H:%M"),
                    0,  # いいね数
                    0   # ナイスファイト数
                ]
                sheet.append_row(new_report)
                st.success("日報を投稿しました！")

# タイムライン表示
def timeline():
    st.title("タイムライン")
    reports = sheet.get_all_values()[1:]  # ヘッダーを除く
    
    if not reports:
        st.info("まだ投稿がありません。")
        return
    
    for idx, report in enumerate(reports):
        with st.container():
            st.subheader(f"{report[0]} - {report[5]}")
            st.write(report[3])
            st.text(f"いいね！ {report[6]} / ナイスファイト！ {report[7]}")
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("いいね！", key=f"like_{idx}"):
                    sheet.update_cell(idx + 2, 7, int(report[6]) + 1)
                    st.experimental_rerun()
            with col2:
                if st.button("ナイスファイト！", key=f"nice_fight_{idx}"):
                    sheet.update_cell(idx + 2, 8, int(report[7]) + 1)
                    st.experimental_rerun()

# マイページ
def my_page():
    st.title("マイページ")
    user = st.session_state["user"]
    reports = sheet.get_all_values()[1:]  # ヘッダーを除く
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
    notices = notice_sheet.get_all_values()[1:]
    
    if not notices:
        st.info("現在お知らせはありません。")
        return
    
    for notice in notices:
        st.subheader(f"{notice[0]} - {notice[1]}")
        st.write(notice[2])

# メイン処理
if "user" not in st.session_state:
    st.session_state["user"] = None

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
        notice()
