import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from db_utils import (
    load_json, save_json, save_to_db, load_from_db, 
    init_db, load_notices, save_notice
)

# ✅ SQLite 初期化
init_db()

# ✅ セッションにデータをキャッシュ
if "reports" not in st.session_state:
    st.session_state["reports"] = load_from_db()

if "notices" not in st.session_state:
    st.session_state["notices"] = load_notices()

# ✅ タイムライン（ワード検索＋期間フィルター＋いいね！＋コメント）
def timeline():
    if "user" not in st.session_state or st.session_state["user"] is None:
        st.error("ログインしてください。")
        return

    st.title("📜 タイムライン")
    
    # 🔍 検索機能
    search_query = st.text_input("🔍 投稿を検索（キーワード or タグ）", "")

    # 📅 期間フィルター
    today = datetime.utcnow()
    start_date = st.date_input("📅 開始日", today - timedelta(days=7))
    end_date = st.date_input("📅 終了日", today)

    # フィルタリング
    filtered_reports = [
        r for r in st.session_state["reports"]
        if start_date <= datetime.strptime(r[3], "%Y-%m-%d %H:%M") <= end_date
        and (search_query.lower() in r[6].lower() or search_query.lower() in r[5].lower())
    ]

    for idx, report in enumerate(filtered_reports):
        with st.container():
            st.subheader(f"{report[1]} - {report[3]}")
            st.write(f"🏷 タグ: {report[5]}")
            st.write(f"📍 得意先 / 実施場所: {report[4]}")
            st.write(f"📝 **実施内容:** {report[6]}")
            st.write(f"💬 **所感:** {report[7]}")
            st.text(f"👍 いいね！ {report[8]} / 🎉 ナイスファイト！ {report[9]}")

            # いいねボタン
            if st.button("👍 いいね！", key=f"like_{idx}"):
                report[8] += 1
                save_to_db(report)
                st.rerun()

            # コメント機能
            st.subheader("💬 コメント")
            comment_input = st.text_area(f"コメントを書く", key=f"comment_input_{idx}")
            if st.button("📤 投稿", key=f"comment_submit_{idx}"):
                if comment_input.strip():
                    new_comment = {
                        "投稿者": st.session_state["user"]["name"],
                        "日時": today.strftime("%Y-%m-%d %H:%M"),
                        "内容": comment_input.strip()
                    }
                    report[10].append(new_comment)
                    save_to_db(report)
                    st.rerun()

# ✅ 日報投稿（実行日 + 写真アップロード）
def post_report():
    if "user" not in st.session_state or st.session_state["user"] is None:
        st.error("ログインしてください。")
        return

    st.title("📝 日報投稿")
    user = st.session_state["user"]

    execution_date = st.date_input("📅 実行日", datetime.utcnow())
    category = st.text_input("📋 カテゴリ")
    location = st.text_input("📍 得意先 or 実施場所")
    tags = st.text_input("🏷 タグ (カンマ区切り)")
    content = st.text_area("📝 実施内容")
    remarks = st.text_area("💬 所感・備考")
    uploaded_file = st.file_uploader("📷 画像をアップロード", type=["jpg", "png", "jpeg"])

    submit_button = st.button("📤 投稿する")

    if submit_button:
        if not category or not tags or not content:
            st.error("カテゴリ、タグ、実施内容は必須項目です。")
        else:
            now_japan = datetime.utcnow().strftime("%Y-%m-%d %H:%M")
            tag_list = [tag.strip() for tag in tags.replace(" ", "").split(",") if tag.strip()]

            new_report = {
                "投稿者": user["name"],
                "投稿者部署": user["depart"],
                "投稿日時": now_japan,
                "実行日": execution_date.strftime("%Y-%m-%d"),
                "カテゴリ": category,
                "得意先・場所": location,
                "タグ": tag_list,
                "実施内容": content,
                "所感・備考": remarks,
                "いいね": 0,
                "ナイスファイト": 0,
                "コメント": []
            }

            save_to_db(new_report)
            st.session_state["reports"] = load_from_db()
            st.success("日報を投稿しました！")
            st.rerun()

# ✅ マイページ（投稿編集・CSVダウンロード）
def my_page():
    if "user" not in st.session_state or st.session_state["user"] is None:
        st.error("ログインしてください。")
        return

    st.title("👤 マイページ")

    # ✅ 自分の投稿一覧
    user_reports = [r for r in st.session_state["reports"] if r[1] == st.session_state["user"]["name"]]
    
    # 📅 CSVダウンロード
    start_date = st.date_input("📅 CSV出力開始日", datetime.utcnow() - timedelta(days=7))
    end_date = st.date_input("📅 CSV出力終了日", datetime.utcnow())

    csv_data = pd.DataFrame(user_reports, columns=["投稿者", "部署", "投稿日時", "実行日", "カテゴリ", "場所", "タグ", "内容", "所感", "いいね", "ナイスファイト", "コメント"])
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
