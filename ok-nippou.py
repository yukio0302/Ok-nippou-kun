import streamlit as st
import json
from datetime import datetime, timedelta

# ファイルパス
USER_DATA_FILE = "users_data.json"
REPORTS_FILE = "reports.json"
NOTICE_FILE = "notices.json"

# データの読み込み・保存
def load_data(file_path, default_data):
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return default_data

def save_data(file_path, data):
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# データ読み込み
users = load_data(USER_DATA_FILE, [])
reports = load_data(REPORTS_FILE, [])
notices = load_data(NOTICE_FILE, [])

# Streamlit 初期設定
st.set_page_config(page_title="日報管理システム", layout="wide")

# 🔑 ログイン機能
def login():
    st.title("ログイン")
    user_code = st.text_input("社員コード")
    password = st.text_input("パスワード", type="password")
    login_button = st.button("ログイン")
    
    if login_button:
        user = next((u for u in users if u["code"] == user_code and u["password"] == password), None)
        if user:
            st.session_state["user"] = user
            st.success(f"ようこそ、{user['name']} さん！（{user['depart']}）")
            st.rerun()
        else:
            st.error("社員コードまたはパスワードが間違っています。")

# 📜 タイムライン
def timeline():
    st.title("📜 タイムライン")

    # 🔍 フィルター（部署 + 検索）
    depart_filter = st.selectbox("📂 部署フィルター", ["全て"] + list(set(u["depart"] for u in users)))
    search_keyword = st.text_input("🔎 投稿検索", placeholder="キーワードを入力")

    # フィルタリング
    filtered_reports = [r for r in reports if (depart_filter == "全て" or r["投稿者部署"] == depart_filter)]
    if search_keyword:
        filtered_reports = [r for r in filtered_reports if search_keyword in r["タグ"] or search_keyword in r["実施内容"]]

    if not filtered_reports:
        st.info("🔍 該当する投稿がありません。")
        return

    for idx, report in enumerate(filtered_reports):
        with st.container():
            st.subheader(f"{report['投稿者']} - {report['カテゴリ']} - {report['投稿日時']}")
            st.markdown(f"🏷 タグ: {report['タグ']}")
            st.write(f"📝 実施内容: {report['実施内容']}")
            st.write(f"💬 所感: {report['所感・備考']}")

# 🔔 お知らせ
def notice():
    st.title("🔔 お知らせ")
    tab_selected = st.radio("📌 お知らせ", ["未読", "既読"])

    # フィルタリング
    unread_notices = [n for n in notices if not n["既読"]]
    read_notices = [n for n in notices if n["既読"]]

    if tab_selected == "未読":
        if not unread_notices:
            st.info("未読のお知らせはありません。")
            return
        
        for idx, notice in enumerate(unread_notices):
            with st.container():
                st.subheader(f"{notice['タイトル']} - {notice['日付']}")
                st.write(notice["内容"])

                # コメント内容を表示
                if "コメント" in notice:
                    st.markdown(f"💬 **コメント:** {notice['コメント']}")

                if "リンク" in notice:
                    if st.button("📌 投稿を確認する", key=f"notice_{idx}"):
                        notice["既読"] = True
                        save_data(NOTICE_FILE, notices)
                        st.rerun()

    elif tab_selected == "既読":
        if not read_notices:
            st.info("既読のお知らせはありません。")
            return
        
        for notice in read_notices:
            with st.container():
                st.subheader(f"{notice['タイトル']} - {notice['日付']}")
                st.write(notice["内容"])

# 📝 日報投稿
def post_report():
    st.title("日報投稿")

    with st.form("report_form"):
        category = st.selectbox("カテゴリ", ["営業活動", "社内作業", "その他"])
        tags = st.text_input("タグ", placeholder="#案件, #改善提案 など")
        content = st.text_area("実施内容")
        notes = st.text_area("所感・備考")
        submit = st.form_submit_button("投稿")

        if submit and content:
            new_report = {
                "投稿者": st.session_state["user"]["name"],
                "投稿者部署": st.session_state["user"]["depart"],
                "カテゴリ": category,
                "タグ": tags,
                "実施内容": content,
                "所感・備考": notes,
                "投稿日時": datetime.now().strftime("%Y-%m-%d %H:%M"),
            }
            reports.append(new_report)
            save_data(REPORTS_FILE, reports)
            st.success("日報を投稿しました！")
            st.rerun()

# メイン処理
if "user" not in st.session_state:
    st.session_state["user"] = None

if st.session_state["user"] is None:
    login()
else:
    menu = st.sidebar.radio("メニュー", ["タイムライン", "日報投稿", "お知らせ"])
    if menu == "タイムライン":
        timeline()
    elif menu == "日報投稿":
        post_report()
    elif menu == "お知らせ":
        notice()
