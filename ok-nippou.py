import streamlit as st
from datetime import datetime, timedelta
from db_utils import init_db, save_report, load_reports

# ✅ SQLite 初期化
init_db()

# ✅ タイムライン
def timeline():
    st.title("📜 タイムライン")

    # 🔍 検索＆期間フィルター
    search_query = st.text_input("🔍 キーワード検索")
    start_date = st.date_input("📅 開始日", datetime.utcnow() - timedelta(days=7))
    end_date = st.date_input("📅 終了日", datetime.utcnow())

    # 📜 投稿データを取得
    reports = load_reports()

    for report in reports:
        st.subheader(f"{report[1]} - {report[2]}")
        st.write(f"🏷 カテゴリ: {report[3]}")
        st.write(f"📍 場所: {report[4]}")
        st.write(f"📝 **実施内容:** {report[5]}")
        st.write(f"💬 **所感:** {report[6]}")
        st.text(f"👍 いいね！ {report[7]} / 🎉 ナイスファイト！ {report[8]}")

# ✅ 日報投稿
def post_report():
    st.title("📝 日報投稿")

    execution_date = st.date_input("📅 実行日", datetime.utcnow())
    category = st.text_input("📋 カテゴリ")
    location = st.text_input("📍 場所")
    content = st.text_area("📝 実施内容")
    remarks = st.text_area("💬 所感")

    submit_button = st.button("📤 投稿する")

    if submit_button:
        new_report = {
            "投稿者": "テストユーザー",
            "実行日": execution_date.strftime("%Y-%m-%d"),
            "カテゴリ": category,
            "場所": location,
            "実施内容": content,
            "所感": remarks,
            "コメント": []
        }

        save_report(new_report)
        st.success("日報を投稿しました！")

# ✅ メニュー管理
menu = st.sidebar.radio("メニュー", ["タイムライン", "日報投稿"])

if menu == "タイムライン":
    timeline()
elif menu == "日報投稿":
    post_report()
