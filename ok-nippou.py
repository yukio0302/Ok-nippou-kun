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

# 🖼 ユーザーの丸型アイコン生成
def generate_avatar(name):
    initials = name[:2].upper()
    return f"🟢 {initials}"

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
            st.rerun()
        else:
            st.error("社員コードまたはパスワードが間違っています。")

# 📜 タイムライン
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
            st.markdown("---")
            col1, col2 = st.columns([1, 8])
            with col1:
                st.text(generate_avatar(report["投稿者"]))
            with col2:
                st.subheader(f"{report['投稿者']} - {report['投稿日時']}")
                st.markdown(f"🏷 **タグ**: {report['タグ']}")
            st.write(f"📝 **実施内容**: {report['実施内容']}")
            st.write(f"💬 **所感**: {report['所感・備考']}")
            st.text(f"👍 {report['いいね']} いいね！ | 🎉 {report['ナイスファイト']} ナイスファイト！")

            col1, col2 = st.columns([2, 2])
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

# 📝 日報投稿
def post_report():
    st.title("📝 日報投稿")
    with st.form("report_form"):
        tags = st.text_input("🏷 タグ (カンマ区切り)", placeholder="例: 開発, 調査, テスト")
        content = st.text_area("📝 実施内容")
        feedback = st.text_area("💬 所感・備考")
        submit = st.form_submit_button("📤 投稿する")

        if submit:
            if tags and content:
                new_report = {
                    "投稿者": st.session_state["user"]["name"],
                    "投稿者部署": st.session_state["user"]["depart"],
                    "投稿日時": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "タグ": tags.split(","),
                    "実施内容": content,
                    "所感・備考": feedback,
                    "いいね": 0,
                    "ナイスファイト": 0
                }
                reports.append(new_report)
                save_data(REPORTS_FILE, reports)
                st.success("✅ 日報を投稿しました！")
                st.rerun()
            else:
                st.error("⚠ タグと実施内容を入力してください。")

# 🔔 お知らせ
def show_notices():
    st.title("🔔 お知らせ")
    user_departments = st.session_state["user"]["depart"]
    filtered_notices = [
        n for n in notices if any(dept in user_departments for dept in n["対象部署"])
    ]

    if not filtered_notices:
        st.info("📭 現在、あなた宛てのお知らせはありません。")
        return

    for notice in filtered_notices:
        st.markdown("---")
        st.subheader(f"📢 {notice['タイトル']}")
        st.write(f"📅 **日付**: {notice['日付']}")
        st.write(f"💬 **内容**: {notice['内容']}")
        st.markdown(f"**対象部署**: {', '.join(notice['対象部署'])}")

# 📢 部署アナウンス（管理者のみ）
def post_announcement():
    if not st.session_state["user"].get("admin", False):
        st.error("⚠ あなたにはアナウンス投稿の権限がありません。")
        return

    st.title("📢 部署アナウンス投稿")

    with st.form("announcement_form"):
        target_dept = st.multiselect("📂 対象部署", sorted(set(dept for user in users for dept in user["depart"])))
        content = st.text_area("📢 アナウンス内容")
        submit = st.form_submit_button("📢 投稿する")

        if submit and content and target_dept:
            new_announcement = {
                "タイトル": "📢 部署アナウンス",
                "日付": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "内容": content,
                "対象部署": target_dept,
                "既読": False
            }
            notices.append(new_announcement)
            save_data(NOTICE_FILE, notices)
            st.success("✅ アナウンスを投稿しました！")
            st.rerun()

# メイン処理
if "user" not in st.session_state:
    st.session_state["user"] = None

if st.session_state["user"] is None:
    login()
else:
    menu = st.sidebar.radio("メニュー", ["タイムライン", "日報投稿", "お知らせ", "部署アナウンス（管理者）"])
    if menu == "タイムライン":
        timeline()
    elif menu == "日報投稿":
        post_report()
    elif menu == "お知らせ":
        show_notices()
    elif menu == "部署アナウンス（管理者）":
        post_announcement()
