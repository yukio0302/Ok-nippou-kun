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
            st.stop()
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

# ✏️ 日報投稿画面（過去の投稿一覧付き）
def post_report():
    st.title("✏️ 日報投稿")
    user = st.session_state["user"]

    # 日報投稿フォーム
    st.subheader("新しい日報を投稿する")
    category = st.text_input("📋 カテゴリ")
    tags = st.text_input("🏷 タグ (カンマ区切り)")
    content = st.text_area("📝 実施内容")
    remarks = st.text_area("💬 所感・備考")
    submit_button = st.button("📤 投稿する")

    if submit_button:
        if not category or not tags or not content:
            st.error("カテゴリ、タグ、実施内容は必須項目です。")
            return

        new_report = {
            "投稿者": user["name"],
            "投稿者部署": user["depart"],
            "投稿日時": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "カテゴリ": category,
            "タグ": tags.split(","),
            "実施内容": content,
            "所感・備考": remarks,
            "いいね": 0,
            "ナイスファイト": 0
        }
        reports.append(new_report)
        save_data(REPORTS_FILE, reports)
        st.success("日報を投稿しました！")

    # 過去の投稿一覧
    st.subheader("過去の投稿一覧")
    user_reports = [r for r in reports if r["投稿者"] == user["name"]]
    if not user_reports:
        st.info("まだ投稿はありません。")
        return

    for idx, report in enumerate(user_reports):
        with st.container():
            st.markdown("---")
            st.write(f"📅 投稿日時: {report['投稿日時']}")
            st.write(f"📋 カテゴリ: {report['カテゴリ']}")
            st.write(f"🏷 タグ: {', '.join(report['タグ'])}")
            st.write(f"📝 実施内容: {report['実施内容']}")
            st.write(f"💬 所感・備考: {report['所感・備考']}")

            col1, col2 = st.columns(2)
            with col1:
                if st.button("✏️ 修正", key=f"edit_{idx}"):
                    edit_report(report)
            with col2:
                if st.button("🗑️ 削除", key=f"delete_{idx}"):
                    reports.remove(report)
                    save_data(REPORTS_FILE, reports)
                    st.success("投稿を削除しました。")
                    st.experimental_rerun()

# 投稿修正機能
def edit_report(report):
    st.text_input("📋 カテゴリ", value=report["カテゴリ"], key="edit_category")
    st.text_input("🏷 タグ", value=",".join(report["タグ"]), key="edit_tags")
    st.text_area("📝 実施内容", value=report["実施内容"], key="edit_content")
    st.text_area("💬 所感・備考", value=report["所感・備考"], key="edit_remarks")
    if st.button("✅ 修正を保存する"):
        report["カテゴリ"] = st.session_state["edit_category"]
        report["タグ"] = st.session_state["edit_tags"].split(",")
        report["実施内容"] = st.session_state["edit_content"]
        report["所感・備考"] = st.session_state["edit_remarks"]
        save_data(REPORTS_FILE, reports)
        st.success("投稿を修正しました。")
        st.experimental_rerun()

# 📢 部署内アナウンス投稿
def post_announcement():
    st.title("📢 部署内アナウンス投稿（管理者限定）")

    user = st.session_state["user"]
    if not user.get("admin"):
        st.error("この機能は管理者のみ利用できます。")
        return

    title = st.text_input("📋 タイトル")
    content = st.text_area("📝 内容")
    departments = st.multiselect("📂 対象部署", options=sorted(set(dept for u in users for dept in u["depart"])))
    submit_button = st.button("📤 アナウンスを送信する")

    if submit_button:
        if not title or not content or not departments:
            st.error("タイトル、内容、対象部署は必須項目です。")
            return

        new_notice = {
            "タイトル": title,
            "日付": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "内容": content,
            "対象部署": departments,
            "既読": False
        }
        notices.append(new_notice)
        save_data(NOTICE_FILE, notices)
        st.success("アナウンスを送信しました！")

# メイン処理
if "user" not in st.session_state:
    st.session_state["user"] = None

if st.session_state["user"] is None:
    login()
else:
    menu = st.sidebar.radio("メニュー", ["タイムライン", "日報投稿", "部署内アナウンス", "お知らせ"])
    if menu == "タイムライン":
        timeline()
    elif menu == "日報投稿":
        post_report()
    elif menu == "部署内アナウンス":
        post_announcement()
