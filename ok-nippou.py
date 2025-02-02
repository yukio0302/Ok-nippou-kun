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

# 📜 タイムライン（コメント機能付き）
def timeline():
    st.title("📜 タイムライン")

    all_departments = sorted(set(dept for user in users for dept in user["depart"]))
    depart_filter = st.selectbox("📂 部署フィルター", ["全て"] + all_departments)
    search_keyword = st.text_input("🔎 投稿検索", placeholder="キーワードを入力")

    filtered_reports = [
        r for r in reports if
        (depart_filter == "全て" or any(dept in r["投稿者部署"] for dept in st.session_state["user"]["depart"]))
        and (search_keyword in r["タグ"] or search_keyword in r["実施内容"])
    ]

    if not filtered_reports:
        st.info("🔍 該当する投稿がありません。")
        return

    for idx, report in enumerate(filtered_reports):
        with st.container():
            st.subheader(f"{report['投稿者']} - {report['投稿日時']}")
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

            # 📝 コメント機能（修正後）
            st.subheader("💬 コメント")
            if "コメント" not in report:
                report["コメント"] = []

            for comment in report["コメント"]:
                name = comment.get("投稿者", "不明")
                date = comment.get("日時", "不明な日時")
                content = comment.get("内容", "（コメントなし）")
                st.markdown(f"**{name} ({date}):** {content}")

            comment_input = st.text_area(f"💬 コメントを書く", key=f"comment_input_{idx}")
            if st.button("📤 コメントを投稿", key=f"comment_submit_{idx}"):
                if comment_input.strip():
                    new_comment = {
                        "投稿者": st.session_state["user"]["name"],
                        "日時": datetime.now().strftime("%Y-%m-%d %H:%M"),
                        "内容": comment_input.strip()
                    }
                    report["コメント"].append(new_comment)
                    save_data(REPORTS_FILE, reports)
                    st.experimental_rerun()
                else:
                    st.error("コメントを入力してください！")

# 📢 部署内アナウンス（管理者限定）
def post_announcement():
    st.title("📢 部署内アナウンス投稿（管理者のみ）")

    if not st.session_state["user"]["admin"]:
        st.error("この機能は管理者のみ利用できます。")
        return

    title = st.text_input("📋 タイトル")
    content = st.text_area("📝 内容")
    departments = st.multiselect("📂 対象部署", sorted(set(dept for user in users for dept in user["depart"])))
    submit_button = st.button("📤 アナウンスを送信する")

    if submit_button and title and content and departments:
        notices.append({
            "タイトル": title,
            "日付": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "内容": content,
            "対象部署": departments,
            "既読": False
        })
        save_data(NOTICE_FILE, notices)
        st.success("アナウンスを送信しました！")

# メイン処理
if "user" not in st.session_state:
    st.session_state["user"] = None

if st.session_state["user"] is None:
    login()
else:
    menu = st.sidebar.radio("メニュー", ["タイムライン", "日報投稿", "お知らせ", "部署内アナウンス"])

    if menu == "タイムライン":
        timeline()
    elif menu == "日報投稿":
        post_report()
    elif menu == "お知らせ":
        show_notices()
    elif menu == "部署内アナウンス":
        post_announcement()
