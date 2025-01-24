import streamlit as st
from datetime import datetime, timedelta
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# Googleスプレッドシート認証設定
def authenticate_google_sheet():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    credentials = ServiceAccountCredentials.from_json_keyfile_name("service_account.json", scope)
    gc = gspread.authorize(credentials)
    return gc

# スプレッドシートに接続
def get_sheets():
    gc = authenticate_google_sheet()
    spreadsheet = gc.open("日報システム")
    reports_sheet = spreadsheet.worksheet("日報データ")
    comments_sheet = spreadsheet.worksheet("コメントデータ")
    return reports_sheet, comments_sheet

# 初期設定
st.set_page_config(page_title="日報管理システム", layout="wide")
st.session_state.setdefault("user", None)  # ユーザー情報

# ログイン画面
def login():
    st.title("ログイン")
    employee_code = st.text_input("社員コード")
    password = st.text_input("パスワード", type="password")
    login_button = st.button("ログイン")

    if login_button:
        # ユーザー認証（簡易版、外部ユーザー情報データを使用予定）
        if employee_code == "901179" and password == "okanaga":
            st.session_state.user = {"code": employee_code, "name": "野村幸男"}
            st.success("ログイン成功！")
        else:
            st.error("社員コードまたはパスワードが間違っています。")

# メイン処理
if "user" not in st.session_state or st.session_state.user is None:
    login()
else:
    # 下部ナビゲーション
    menu = st.sidebar.radio("メニュー", ["タイムライン", "日報投稿", "マイページ", "お知らせ"])

    if menu == "タイムライン":
        timeline()
    elif menu == "日報投稿":
        post_report()
    elif menu == "マイページ":
        st.write("マイページ機能は未実装です。")
    elif menu == "お知らせ":
        st.write("お知らせ機能は未実装です。")

# タイムライン表示
def timeline():
    reports_sheet, comments_sheet = get_sheets()
    st.title("タイムライン")

    # 日報データを取得
    reports = reports_sheet.get_all_records()
    current_time = datetime.now()

    # 表示期間フィルタリング
    time_filter = st.radio("表示期間", ("5日間", "24時間以内"), horizontal=True)
    if time_filter == "5日間":
        start_date = current_time - timedelta(days=5)
    else:
        start_date = current_time - timedelta(hours=24)

    filtered_reports = [report for report in reports if datetime.strptime(report['日付'], "%Y-%m-%d") >= start_date]

    for report in filtered_reports:
        st.subheader(f"{report['タイトル']} by {report['投稿者']} - {report['日付']}")
        st.write(report['内容'])
        st.write(f"カテゴリ: {report['カテゴリ']}")
        if report['画像URL']:
            st.image(report['画像URL'], use_column_width=True)

        # スタンプとコメント
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button(f"👍 いいね！ ({report['いいね数']})", key=f"like_{report['ID']}"):
                reports_sheet.update_cell(report['ID'] + 1, 6, int(report['いいね数']) + 1)
                st.experimental_rerun()
        with col2:
            if st.button(f"👏 ナイスファイト！ ({report['ナイスファイト数']})", key=f"clap_{report['ID']}"):
                reports_sheet.update_cell(report['ID'] + 1, 7, int(report['ナイスファイト数']) + 1)
                st.experimental_rerun()
        with col3:
            comment = st.text_input("コメントする", key=f"comment_input_{report['ID']}")
            if st.button("コメント投稿", key=f"comment_btn_{report['ID']}"):
                comments_sheet.append_row([report['ID'], st.session_state.user['name'], comment, datetime.now().strftime("%Y-%m-%d %H:%M")])
                st.experimental_rerun()

# 日報投稿フォーム
def post_report():
    reports_sheet, _ = get_sheets()
    st.title("日報投稿")

    with st.form("report_form"):
        category = st.selectbox("カテゴリ", ["営業活動", "社内作業", "その他"])
        client = st.text_input("得意先", placeholder="カテゴリが営業活動の場合のみ") if category == "営業活動" else ""
        tags = st.text_input("タグ", placeholder="#案件, #クレーム対応, #要検討など")
        content = st.text_area("実施内容")
        notes = st.text_area("所感・備考")
        image = st.file_uploader("画像をアップロード", type=["jpg", "png", "jpeg"])

        submit = st.form_submit_button("投稿")
        if submit:
            image_url = None
            if image:
                image_url = f"uploaded_images/{image.name}"
                with open(image_url, "wb") as f:
                    f.write(image.getbuffer())

            new_report = [
                len(reports_sheet.get_all_values()),  # ID
                content,
                st.session_state.user['name'],
                category,
                client,
                tags,
                notes,
                image_url,
                datetime.now().strftime("%Y-%m-%d")
            ]
            reports_sheet.append_row(new_report)
            st.success("日報が投稿されました！")

# メイン処理
if st.session_state.user is None:
    login()
else:
    # 下部ナビゲーション
    menu = st.sidebar.radio("メニュー", ["タイムライン", "日報投稿", "マイページ", "お知らせ"])

    if menu == "タイムライン":
        timeline()
    elif menu == "日報投稿":
        post_report()
    elif menu == "マイページ":
        st.write("マイページ機能は未実装です。")
    elif menu == "お知らせ":
        st.write("お知らせ機能は未実装です。")
