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

# データ読み込み
users = load_data(USER_DATA_FILE, [])
reports = load_data(REPORTS_FILE, [])
notices = load_data(NOTICE_FILE, [])

# Streamlit 初期設定
st.set_page_config(page_title="日報管理システム", layout="wide")

# ログイン機能
def login():
    st.title("ログイン")
    user_code = st.text_input("社員コード")
    password = st.text_input("パスワード", type="password", help="パスワードを入力してください")
    login_button = st.button("ログイン")
    
    if login_button:
        user = next((u for u in users if u["code"] == user_code and u["password"] == password), None)
        if user:
            st.session_state["user"] = user
            st.success(f"ログイン成功！ようこそ、{user['name']}さん！")
            st.rerun()
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
                "ナイスファイト": 0,
                "コメント": []
            }
            reports.append(new_report)
            save_data(REPORTS_FILE, reports)
            st.success("日報を投稿しました！")
            st.rerun()

# タイムライン
def timeline():
    st.title("📜 タイムライン")

    # 🔍 タグ & キーワード検索
    search_keyword = st.text_input("🔎 投稿検索（タグ & 本文）", placeholder="キーワードを入力")
    
    # 検索ロジック（投稿のタグ or 本文にキーワードが含まれるか）
    filtered_reports = reports if not search_keyword else [
        r for r in reports if search_keyword in r["タグ"] or search_keyword in r["実施内容"]
    ]

    if not filtered_reports:
        st.info("🔍 該当する投稿がありません。")
        return

    for idx, report in enumerate(filtered_reports):
        with st.container():
            st.subheader(f"{report['投稿者']} - {report['カテゴリ']} - {report['投稿日時']}")

            if report["タグ"]:
                st.markdown(f"**🏷 タグ:** {report['タグ']}")

            st.write(f"📝 {report['実施内容']}")

            st.text(f"👍 いいね！ {report['いいね']} / 🎉 ナイスファイト！ {report['ナイスファイト']}")

            col1, col2 = st.columns(2)
            with col1:
                if st.button("👍 いいね！", key=f"like_{idx}"):
                    report["いいね"] += 1
                    save_data(REPORTS_FILE, reports)
                    st.rerun()

            with col2:
                if st.button("🎉 ナイスファイト！", key=f"nice_fight_{idx}"):
                    report["ナイスファイト"] += 1
                    save_data(REPORTS_FILE, reports)
                    st.rerun()

            if "コメント" not in report:
                report["コメント"] = []

            st.subheader("💬 コメント一覧")
            for comment_idx, comment in enumerate(report["コメント"]):
                st.text(f"📌 {comment['投稿者']}: {comment['内容']} ({comment['投稿日時']})")
                if comment["投稿者"] == st.session_state["user"]["name"]:
                    if st.button("🗑 削除", key=f"delete_comment_{idx}_{comment_idx}"):
                        report["コメント"].pop(comment_idx)
                        save_data(REPORTS_FILE, reports)
                        st.rerun()

            new_comment = st.text_input(f"✏ コメントを入力（{report['投稿者']} さんの日報）", key=f"comment_{idx}")
            if st.button("💬 コメント投稿", key=f"post_comment_{idx}"):
                if new_comment.strip():
                    new_comment_data = {
                        "投稿者": st.session_state["user"]["name"],
                        "内容": new_comment,
                        "投稿日時": datetime.now().strftime("%Y-%m-%d %H:%M")
                    }
                    report["コメント"].append(new_comment_data)
                    save_data(REPORTS_FILE, reports)

                    new_notice = {
                        "タイトル": "あなたの投稿にコメントがつきました！",
                        "日付": datetime.now().strftime("%Y-%m-%d %H:%M"),
                        "内容": f"{st.session_state['user']['name']} さんがコメントしました！",
                        "リンク": idx,
                        "既読": False
                    }
                    notices.append(new_notice)
                    save_data(NOTICE_FILE, notices)

                    st.success("コメントを投稿しました！")
                    st.rerun()

# お知らせ
def notice():
    st.title("お知らせ")
    if not notices:
        st.info("現在お知らせはありません。")
        return
    
    for idx, notice in enumerate(notices):
        with st.container():
            st.subheader(f"{notice['タイトル']} - {notice['日付']}")
            st.write(notice["内容"])

            if "リンク" in notice:
                if st.button("投稿を確認する", key=f"notice_{idx}"):
                    st.session_state["jump_to_report"] = notice["リンク"]
                    notice["既読"] = True
                    save_data(NOTICE_FILE, notices)
                    st.rerun()
            if not notice["既読"]:
                st.text("🔴 未読")

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
