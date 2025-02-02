import streamlit as st
import json
from datetime import datetime

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
            st.success(f"ようこそ、{user['name']} さん！（{', '.join(user['depart'])}）")
            st.experimental_rerun()
        else:
            st.error("社員コードまたはパスワードが間違っています。")

# 📜 タイムライン
def timeline():
    st.title("📜 タイムライン")

    all_departments = sorted(set(dept for user in users for dept in user["depart"]))
    depart_filter = st.selectbox("📂 部署フィルター", ["全て"] + all_departments)
    search_keyword = st.text_input("🔎 投稿検索", placeholder="キーワードを入力")

    filtered_reports = []
    for r in reports:
        if depart_filter == "全て" or any(dept in r["投稿者部署"] for dept in st.session_state["user"]["depart"]):
            filtered_reports.append(r)

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
            st.text(f"👍 いいね！ {report['いいね']} / 🎉 ナイスファイト！ {report['ナイスファイト']}")

            col1, col2 = st.columns(2)
            with col1:
                if st.button("👍 いいね！", key=f"like_{idx}"):
                    report["いいね"] += 1
                    save_data(REPORTS_FILE, reports)
                    st.experimental_rerun()

            with col2:
                if st.button("🎉 ナイスファイト！", key=f"nice_fight_{idx}"):
                    report["ナイスファイト"] += 1
                    save_data(REPORTS_FILE, reports)
                    st.experimental_rerun()

            if "コメント" not in report:
                report["コメント"] = []

            st.subheader("💬 コメント一覧")
            for comment_idx, comment in enumerate(report["コメント"]):
                st.text(f"📌 {comment['投稿者']}: {comment['内容']} ({comment['投稿日時']})")
                if comment["投稿者"] == st.session_state["user"]["name"]:
                    if st.button("🗑 削除", key=f"delete_comment_{idx}_{comment_idx}"):
                        report["コメント"].pop(comment_idx)
                        save_data(REPORTS_FILE, reports)
                        st.experimental_rerun()

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
                        "対象部署": report["投稿者部署"],
                        "既読": False
                    }
                    notices.append(new_notice)
                    save_data(NOTICE_FILE, notices)

                    st.success("コメントを投稿しました！")
                    st.experimental_rerun()

# 📋 日報投稿機能
def post_report():
    st.title("📋 日報投稿")

    with st.form("post_report_form"):
        category = st.text_input("カテゴリ", placeholder="例: 定例会議")
        tags = st.text_input("タグ", placeholder="例: 会議, ミーティング")
        content = st.text_area("実施内容", placeholder="何を実施したのか詳細に記載してください。")
        notes = st.text_area("所感・備考", placeholder="感じたことや次の改善点など")

        submit = st.form_submit_button("投稿する")
        if submit:
            if category and tags and content:
                new_report = {
                    "投稿者": st.session_state["user"]["name"],
                    "投稿者部署": st.session_state["user"]["depart"],
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
                st.success("✅ 日報を投稿しました！")
                st.experimental_rerun()
            else:
                st.error("⚠ 必須項目を入力してください。")

# 🔔 お知らせ
def show_notices():
    st.title("🔔 お知らせ")
    user_departments = st.session_state["user"]["depart"]

    filtered_notices = [
        n for n in notices if "対象部署" in n and isinstance(n["対象部署"], list) and any(dept in user_departments for dept in n["対象部署"])
    ]

    if not filtered_notices:
        st.info("📭 現在、あなた宛てのお知らせはありません。")
        return

    for notice in filtered_notices:
        st.markdown("---")
        st.subheader(f"📢 {notice['タイトル']}")
        st.write(f"📅 **日付**: {notice['日付']}")
        st.write(f"💬 **内容**: {notice['内容']}")
        st.markdown(f"**対象部署**: {', '.join(notice.get('対象部署', []))}")

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
        show_notices()
