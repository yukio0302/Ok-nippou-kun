import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from db_utils import init_db, authenticate_user, load_notices, save_report, load_reports, mark_notice_as_read

# ✅ SQLite 初期化
init_db()

# ✅ ログイン機能
def login():
    st.title("🔑 ログイン")
    employee_code = st.text_input("社員コード")
    password = st.text_input("パスワード", type="password")
    login_button = st.button("ログイン")

    if login_button:
        user = authenticate_user(employee_code, password)
        if user:
            st.session_state["user"] = user
            st.success(f"ようこそ、{user['name']} さん！（{', '.join(user['depart'])}）")
            st.rerun()
        else:
            st.error("社員コードまたはパスワードが間違っています。")

# ✅ タイムライン
def timeline():
    if "user" not in st.session_state or st.session_state["user"] is None:
        st.error("ログインしてください。")
        return

    st.title("📜 タイムライン")
    
    # 🔍 検索＆期間フィルター
    search_query = st.text_input("🔍 キーワード検索")
    start_date = st.date_input("📅 開始日", datetime.utcnow() - timedelta(days=7))
    end_date = st.date_input("📅 終了日", datetime.utcnow())

    # 📜 投稿データを取得
    reports = load_reports()

    # フィルタリング
    filtered_reports = [
        r for r in reports
        if start_date.strftime("%Y-%m-%d") <= r[2] <= end_date.strftime("%Y-%m-%d") and
           (search_query.lower() in r[5].lower() or search_query.lower() in r[3].lower())
    ]

    for report in filtered_reports:
        with st.container():
            st.subheader(f"{report[1]} - {report[2]}")
            st.write(f"🏷 カテゴリ: {report[3]}")
            st.write(f"📍 場所: {report[4]}")
            st.write(f"📝 **実施内容:** {report[5]}")
            st.write(f"💬 **所感:** {report[6]}")
            st.text(f"👍 いいね！ {report[7]} / 🎉 ナイスファイト！ {report[8]}")

# ✅ 日報投稿
def post_report():
    if "user" not in st.session_state or st.session_state["user"] is None:
        st.error("ログインしてください。")
        return

    st.title("📝 日報投稿")

    execution_date = st.date_input("📅 実行日", datetime.utcnow())
    category = st.text_input("📋 カテゴリ")
    location = st.text_input("📍 場所")
    content = st.text_area("📝 実施内容")
    remarks = st.text_area("💬 所感")
    uploaded_file = st.file_uploader("📷 画像をアップロード", type=["jpg", "png", "jpeg"])

    submit_button = st.button("📤 投稿する")

    if submit_button:
        new_report = {
            "投稿者": st.session_state["user"]["name"],
            "実行日": execution_date.strftime("%Y-%m-%d"),
            "カテゴリ": category,
            "場所": location,
            "実施内容": content,
            "所感": remarks,
            "コメント": []
        }

        save_report(new_report)
        st.success("日報を投稿しました！")
        st.rerun()

# ✅ お知らせ
def show_notices():
    if "user" not in st.session_state or st.session_state["user"] is None:
        st.error("ログインしてください。")
        return

    st.title("🔔 お知らせ")

    notices = load_notices()
    for notice in notices:
        with st.container():
            st.subheader(f"📢 {notice[2]}")
            st.write(f"📅 **日付**: {notice[3]}")
            st.write(f"📝 **内容:** {notice[1]}")

            if st.button("✅ 既読にする", key=f"mark_read_{notice[0]}"):
                mark_notice_as_read(notice[0])
                st.rerun()

# ✅ マイページ
def my_page():
    if "user" not in st.session_state or st.session_state["user"] is None:
        st.error("ログインしてください。")
        return

    st.title("👤 マイページ")

    # 📜 自分の投稿一覧
    user_reports = [r for r in load_reports() if r[1] == st.session_state["user"]["name"]]

    # 📅 CSVダウンロード
    start_date = st.date_input("📅 CSV出力開始日", datetime.utcnow() - timedelta(days=7))
    end_date = st.date_input("📅 CSV出力終了日", datetime.utcnow())

    csv_data = pd.DataFrame(user_reports, columns=["投稿者", "実行日", "カテゴリ", "場所", "実施内容", "所感", "いいね", "ナイスファイト", "コメント"])
    csv_data = csv_data[(csv_data["実行日"] >= start_date.strftime("%Y-%m-%d")) & (csv_data["実行日"] <= end_date.strftime("%Y-%m-%d"))]

    st.download_button("📥 CSVダウンロード", csv_data.to_csv(index=False).encode("utf-8"), "my_report.csv", "text/csv")

# ✅ メニュー管理
if "user" not in st.session_state:
    st.session_state["user"] = None

if st.session_state["user"] is None:
    login()
else:
    menu = st.sidebar.radio("メニュー", ["タイムライン", "日報投稿", "お知らせ", "マイページ"])
    
    if menu == "タイムライン":
        timeline()
    elif menu == "日報投稿":
        post_report()
    elif menu == "お知らせ":
        show_notices()
    elif menu == "マイページ":
        my_page()
