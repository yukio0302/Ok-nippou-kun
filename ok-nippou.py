import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from db_utils import init_db, authenticate_user, load_notices, save_report, load_reports, mark_notice_as_read
from db_utils import update_likes, add_comment

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


# ✅ タイムライン（X風デザイン）
def timeline():
    if "user" not in st.session_state or st.session_state["user"] is None:
        st.error("ログインしてください。")
        return

    st.title("📜 タイムライン")
    reports = load_reports()

    for report in reports:
        with st.container():
            st.subheader(f"{report[1]} - {report[2]}")
            st.write(f"🏷 **カテゴリ:** {report[3]}")
            st.write(f"📍 **場所:** {report[4]}")
            st.write(f"📝 **実施内容:** {report[5]}")
            st.write(f"💬 **所感:** {report[6]}")
            
            # いいね & ナイスファイト（アイコン表示）
            st.markdown(
                f"❤️ {report[7]}  👍 {report[8]}",
                unsafe_allow_html=True
            )
            col1, col2 = st.columns(2)
            with col1:
                if st.button("❤️ いいね！", key=f"like_{report[0]}"):
                    update_likes(report[0], "like")
                    st.rerun()
            with col2:
                if st.button("👍 ナイスファイト！", key=f"nice_{report[0]}"):
                    update_likes(report[0], "nice")
                    st.rerun()
            
            # コメントリスト
            if report[9]:
                st.write("💬 **コメント:**")
                for comment in report[9]:
                    st.text(comment)
                    if st.button("❤️", key=f"comment_like_{comment}"):
                        update_likes(report[0], "comment_like")
                        st.rerun()
                    if st.button("💬 返信", key=f"reply_{comment}"):
                        reply_text = st.text_input("返信を書く", key=f"reply_text_{comment}")
                        if st.button("📤 送信", key=f"send_reply_{comment}"):
                            add_comment(report[0], f"{st.session_state['user']['name']}: {reply_text.strip()}")
                            st.rerun()
            
            # コメント入力欄
            comment_text = st.text_input("💬 コメントを書く", key=f"comment_{report[0]}")
            if st.button("📤 コメント送信", key=f"send_comment_{report[0]}"):
                if comment_text.strip():
                    add_comment(report[0], f"{st.session_state['user']['name']}: {comment_text.strip()}")
                    st.rerun()
                else:
                    st.warning("コメントを入力してください！")



# ✅ 日報投稿（ボタン連打防止 & 投稿フィードバック追加）
def post_report():
    if "user" not in st.session_state or st.session_state["user"] is None:
        st.error("ログインしてください。")
        return

    st.title("📝 日報投稿")

    category = st.text_input("📋 カテゴリ")
    location = st.text_input("📍 場所")
    content = st.text_area("📝 実施内容")
    remarks = st.text_area("💬 所感")

    submit_button = st.button("📤 投稿する", disabled=st.session_state.get("posting", False))

    if submit_button:
        st.session_state["posting"] = True  # ボタンを一時的に無効化
        save_report({
            "投稿者": st.session_state["user"]["name"],
            "実行日": datetime.utcnow().strftime("%Y-%m-%d"),
            "カテゴリ": category,
            "場所": location,
            "実施内容": content,
            "所感": remarks,
            "コメント": []
        })
        st.success("✅ 日報を投稿しました！")
        time.sleep(2)  # 2秒待ってから画面更新
        st.session_state["posting"] = False  # ボタンを再び有効化
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


# ✅ 日報データを取得（SQLite → DataFrame）
def load_reports():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM reports ORDER BY 実行日 DESC")
        rows = cursor.fetchall()

        # カラム名をDBの定義に合わせる
        columns = ["ID", "投稿者", "実行日", "カテゴリ", "場所", "実施内容", "所感", "いいね", "ナイスファイト", "コメント"]
        df = pd.DataFrame(rows, columns=columns)

        # `実行日` を `datetime` 型に変換（フォーマット統一）
        df["実行日"] = pd.to_datetime(df["実行日"], errors="coerce")  # エラーが出たら NaT にする
        df["コメント"] = df["コメント"].apply(lambda x: json.loads(x) if isinstance(x, str) else [])

        return df
    except Exception as e:
        st.error(f"❌ データ取得エラー: {e}")
        return pd.DataFrame()  # 空のDataFrameを返す
    finally:
        conn.close()

# ✅ マイページ
def my_page():
    if "user" not in st.session_state or st.session_state["user"] is None:
        st.error("ログインしてください。")
        return

    st.title("👤 マイページ")

    # 📜 自分の投稿一覧
    df = load_reports()
    if df.empty:
        st.warning("まだ投稿がありません。")
        return

    user_name = st.session_state["user"]["name"]
    user_reports = df[df["投稿者"] == user_name]

    # 📅 CSVダウンロード用のフィルター
    start_date = st.date_input("📅 CSV出力開始日", datetime.today() - timedelta(days=7))
    end_date = st.date_input("📅 CSV出力終了日", datetime.today())

    # `実行日` を文字列（YYYY-MM-DD）に変換してフィルタリング
    filtered_reports = user_reports[
        (user_reports["実行日"] >= pd.to_datetime(start_date)) &
        (user_reports["実行日"] <= pd.to_datetime(end_date))
    ]

    # ダウンロードボタン
    if not filtered_reports.empty:
        csv_data = filtered_reports.copy()
        csv_data["実行日"] = csv_data["実行日"].dt.strftime("%Y-%m-%d")  # 文字列に変換
        csv_data["コメント"] = csv_data["コメント"].apply(json.dumps)  # JSONを文字列化

        st.download_button(
            label="📥 CSVダウンロード",
            data=csv_data.to_csv(index=False, encoding="utf-8-sig"),  # UTF-8 BOM付きでExcel対応
            file_name="my_report.csv",
            mime="text/csv",
        )
    else:
        st.warning("指定期間内のデータがありません。")
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
