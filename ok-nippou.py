import streamlit as st
from datetime import datetime
import firebase_admin
from firebase_admin import credentials, firestore

# Firebase 初期化
if not firebase_admin._apps:
    cred = credentials.Certificate("serviceAccountKey.json")
    firebase_admin.initialize_app(cred)

db = firestore.client()

# Streamlit 初期設定
st.set_page_config(page_title="日報管理システム", layout="wide")

# ログイン画面
def login():
    st.title("ログイン")
    user_code = st.text_input("社員コード", key="user_code_input")
    password = st.text_input("パスワード", type="password", key="password_input")
    login_button = st.button("ログイン", key="login_button")

    if login_button:
        users_ref = db.collection("users").where("code", "==", user_code).where("password", "==", password).stream()
        user = None
        for u in users_ref:
            user = u.to_dict()
        
        if user:
            st.session_state["user"] = user
            st.success(f"ログイン成功！ようこそ、{user['name']}さん！")
        else:
            st.error("社員コードまたはパスワードが間違っています。")

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
                db.collection("reports").add(new_report)
                st.success("日報を投稿しました！")

# タイムライン表示
def timeline():
    st.title("タイムライン")
    reports_ref = db.collection("reports").order_by("投稿日時", direction=firestore.Query.DESCENDING).stream()
    reports = [r.to_dict() for r in reports_ref]
    
    if not reports:
        st.info("まだ投稿がありません。")
        return
    
    for idx, report in enumerate(reports):
        with st.container():
            st.subheader(f"{report['投稿者']} - {report['投稿日時']}")
            st.write(report["実施内容"])
            st.text(f"いいね！ {len(report['いいね'])} / ナイスファイト！ {len(report['ナイスファイト'])}")
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("いいね！", key=f"like_{idx}"):
                    if st.session_state["user"]["name"] not in report["いいね"]:
                        report["いいね"].append(st.session_state["user"]["name"])
                        db.collection("reports").document(report["投稿日時"]).set(report)
                        st.experimental_rerun()
            with col2:
                if st.button("ナイスファイト！", key=f"nice_fight_{idx}"):
                    if st.session_state["user"]["name"] not in report["ナイスファイト"]:
                        report["ナイスファイト"].append(st.session_state["user"]["name"])
                        db.collection("reports").document(report["投稿日時"]).set(report)
                        st.experimental_rerun()

# メイン処理
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
