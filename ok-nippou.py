import streamlit as st
import json
from datetime import datetime

# ファイルパス
USER_DATA_FILE = "users_data.json"
REPORTS_FILE = "reports.json"
NOTICE_FILE = "notices.json"

# ファイル読み込み関数
def load_data(file_path, default_data):
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return default_data

# ファイル保存関数
def save_data(file_path, data):
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# 認証情報読み込み
users = load_data(USER_DATA_FILE, [])
reports = load_data(REPORTS_FILE, [])
notices = load_data(NOTICE_FILE, [])

# Streamlit 初期設定
st.set_page_config(page_title="日報管理システム", layout="wide")

# ログイン機能
def login():
    st.title("ログイン")
    user_code = st.text_input("社員コード")
    password = st.text_input("パスワード", type="password")
    login_button = st.button("ログイン")
    
    if login_button:
        user = next((u for u in users if u["code"] == user_code and u["password"] == password), None)
        if user:
            st.session_state["user"] = user
            st.success(f"ログイン成功！ようこそ、{user['name']}さん！")
        else:
            st.error("社員コードまたはパスワードが間違っています。")

# 日報投稿
def post_report():
    st.title("日報投稿")
    with st.form("report_form"):
        category = st.selectbox("カテゴリ", ["営業活動", "社内作業", "その他"])
        tags = st.text_input("タグ", placeholder="#案件, #改善提案 など")
        content = st.text_area("実施内容", placeholder="実施した内容を記入してください")
        notes = st.text_area("所感・備考", placeholder="所感や備考を記入してください（任意）")
        submit = st.form_submit_button("投稿")
        
        if submit and content:
            new_report = {
                "投稿者": st.session_state["user"]["name"],
                "カテゴリ": category,
                "タグ": tags,
                "実施内容": content,
                "所感・備考": notes,
                "投稿日時": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "いいね": 0,
                "ナイスファイト": 0
            }
            reports.append(new_report)
            save_data(REPORTS_FILE, reports)
            st.success("日報を投稿しました！")

# タイムライン
def timeline():
    st.title("タイムライン")
    if not reports:
        st.info("まだ投稿がありません。")
        return
    
    for idx, report in enumerate(reports):
        with st.container():
            st.subheader(f"{report['投稿者']} - {report['投稿日時']}")
            st.write(report["実施内容"])
            st.text(f"いいね！ {report['いいね']} / ナイスファイト！ {report['ナイスファイト']}")
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("いいね！", key=f"like_{idx}"):
                    report["いいね"] += 1
                    save_data(REPORTS_FILE, reports)
                    st.experimental_rerun()
            with col2:
                if st.button("ナイスファイト！", key=f"nice_fight_{idx}"):
                    report["ナイスファイト"] += 1
                    save_data(REPORTS_FILE, reports)
                    st.experimental_rerun()

# マイページ
def my_page():
    st.title("マイページ")
    user_reports = [r for r in reports if r["投稿者"] == st.session_state["user"]["name"]]
    if not user_reports:
        st.info("あなたの投稿はまだありません。")
        return
    
    st.subheader(f"{st.session_state['user']['name']} さんの投稿一覧")
    for report in user_reports:
        st.write(f"{report['投稿日時']} - {report['実施内容']}")
    
    total_likes = sum(r["いいね"] for r in user_reports)
    total_nice_fights = sum(r["ナイスファイト"] for r in user_reports)
    st.text(f"総いいね数: {total_likes} / 総ナイスファイト数: {total_nice_fights}")

# お知らせ
def notice():
    st.title("お知らせ")
    if not notices:
        st.info("現在お知らせはありません。")
        return
    
    for notice in notices:
        st.subheader(f"{notice['タイトル']} - {notice['日付']}")
        st.write(notice["内容"])

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
