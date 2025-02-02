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

# 🔑 ログイン機能（ログイン後にタイムラインへ）
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
            st.markdown(f"🏷 タグ: {', '.join(report['タグ'])}")
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

            # 💬 コメント機能追加
            st.subheader("💬 コメント")
            if "コメント" not in report:
                report["コメント"] = []

            # 既存コメントを表示
            for comment in report["コメント"]:
                st.markdown(f"**{comment['投稿者']} ({comment['日時']}):** {comment['内容']}")

            # ✍️ コメント入力欄
            new_comment = st.text_area(f"💬 {report['投稿者']} さんの投稿にコメント", key=f"comment_input_{idx}")
            if st.button("📤 コメントを投稿", key=f"comment_button_{idx}"):
                if new_comment.strip():
                    report["コメント"].append({
                        "投稿者": st.session_state["user"]["name"],
                        "日時": datetime.now().strftime("%Y-%m-%d %H:%M"),
                        "内容": new_comment
                    })
                    save_data(REPORTS_FILE, reports)
                    st.success("コメントを追加しました！")
                    st.experimental_rerun()
                else:
                    st.error("コメントを入力してください。")

# 📝 日報投稿（過去の投稿管理付き）
def post_report():
    st.title("📝 日報投稿")
    user = st.session_state["user"]

    category = st.text_input("📋 カテゴリ")
    tags = st.text_input("🏷 タグ (カンマ区切り)")
    content = st.text_area("📝 実施内容")
    remarks = st.text_area("💬 所感・備考")
    submit_button = st.button("📤 投稿する")

    if submit_button:
        if not category or not tags or not content:
            st.error("カテゴリ、タグ、実施内容は必須項目です。")
        else:
            reports.append({
                "投稿者": user["name"],
                "投稿者部署": user["depart"],
                "投稿日時": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "カテゴリ": category,
                "タグ": tags.split(","),
                "実施内容": content,
                "所感・備考": remarks,
                "いいね": 0,
                "ナイスファイト": 0,
                "コメント": []
            })
            save_data(REPORTS_FILE, reports)
            st.success("日報を投稿しました！")

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
