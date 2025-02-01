import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import json

# Google Sheets API 認証設定
SCOPE = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
SERVICE_ACCOUNT_INFO = {
     "type": "service_account",
  "project_id": "meimon-map",
  "private_key_id": "5663f32b0541766cb4313d40cef2f15b0691a20e",
  "private_key": "-----BEGIN PRIVATE KEY-----\nMIIEvgIBADANBgkqhkiG9w0BAQEFAASCBKgwggSkAgEAAoIBAQCadCTvSI0Ze/85\nus//jqmHfsFpiZ+4yiLouq1usif+v70jFi4RLZ1DQbw1yrJOky5nhoG1y4iPpBwv\nQRmie+Y7HE1M8O1Bw6dqLQB8aIOLXchsvuup/fR73LcEe0n6aYYfbrx89IDPURET\nhyTC3GCiYdzcjibfYj3Gap1Sh81jxwOzSfSc5UKvxy7aCuihe8H4Esd5PdBaUbVB\nD+k4r48jfKbcc6XpgFRAbWqZaDjGeBPmXZPVOt0QsdIMdCSpTsat+p5tlVZvo6fx\n6d46JjHih09ftr+WjiGJsZA4vaFKd2AKky98454gKsv9zmG5AKPTZyokTjy5z1XI\nrxdSxS2/AgMBAAECggEADo/yx4i8nPF+7894Ou0VeMvvqmaqY37TacPoBC7R7Ifh\nakR2FXKKiEPTXfL9esEPt/0Lj7tf5cMgUSg/JX2vCFWzyBRTGkc7KpyRlik4ddRi\nyDX7/CwQd/koXEjPgcefOKl1JgbbejB3frLYOXMTvVuiujzA14DouCNnL9fT+pss\natHEwK8OToUHiAgXLbKIjoBXRd/zc4vGGeaBsomBf7XqtCqNBPFtmb4pxyJ5UC+T\npKHNzbjYH4cD+AOor0Gk1+SK3sas11NNXWt67erSNqlhGA/cxqLg5UbdZhb/PPQk\nEHkfjnloTismNK668eaKVt5XT3td4zUH3qXesJMD8QKBgQDPyma4VbfpvQ4u93/K\nReOAYdBVhrUYC1wGJhND3lt4jACW6aHvKjVoPc5EuW5c6BIHqAIwPkBEmEDpNzS8\nnmCkHcg2ZhnyvCLy1wU+jF5qSsOSqz/qYXmPeICflTHGzuhR57To2boIYI+c4ibt\nH5hhPA6mkgvBW8VX1OFxc3c8eQKBgQC+SdPh5ieMLIvBUnaaCX265PtmoL2dBsc2\no3nIe/Y0dErzJpjSZwbeyWptNMYtINuiljZ/aMxdimqM0HUHuE3LVFrk2LnCKb1q\nipi1VKHIRvNEqXyjzSUph/uXO78BuDKUzUPHoK2Xlsc1lANH/mUklBYCpX80NQas\noyYMBZk99wKBgQC6/qjGRs3FmY+EENN90rtTs7Lq5NlgFAjyt50qvJaQu11kckh6\nlP+PGd/g1QdOsMJZBYdCpyLrGCGCP15ESDssNmkRG31Khqjk5UAg8+2btkCeY2KX\nqLTeulD2TCuJgHZuDxktW5MhKtTTGGpzhrV4+7Urjc7qaY4E5t0jXgf18QKBgQCB\nDBZqg6hcUrVwpNkT+83Nmo63+di9jiQ59MGZah/9UMSng4xuXDp3ikbnyrt/TWJG\nL/LDkzHNWhqKZrCHTMFNXGbL/gJ0H9R6VYXcq4mQBjXiYcLKX0yNjs/br0QJCX8c\nFNybnGc9f56Xwko7X9X96YPHxa6vnCprl7Usv/s93wKBgDvYZErASYWDLwjp1AJO\nKf9KKGxmMuHW+lJpIvuunF8CPPimKav9o0cPl5xro/xfh1swQ7Lk2aSKlRb+TLxM\niJ3kmOgj0SVGIPkuRhzxGviHz2rAYS8x/SS9RtVuTr8696CHEYCl/b3p7gtOv7if\nj1EuVRmK3l+jdwyywHmKia62\n-----END PRIVATE KEY-----\n",
  "client_email": "service-account@meimon-map.iam.gserviceaccount.com",
  "client_id": "107338856589811318823",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://oauth2.googleapis.com/token",
  "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
  "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/service-account%40meimon-map.iam.gserviceaccount.com",
  "universe_domain": "googleapis.com"
}

CREDS = ServiceAccountCredentials.from_json_keyfile_dict(SERVICE_ACCOUNT_INFO, SCOPE)
client = gspread.authorize(CREDS)

SHEET_NAME = "日報管理"  # スプレッドシート名
NOTICE_SHEET_NAME = "お知らせ"  # お知らせ用スプレッドシート名

def get_sheet(sheet_name):
    return client.open(sheet_name).sheet1

sheet = get_sheet(SHEET_NAME)
notice_sheet = get_sheet(NOTICE_SHEET_NAME)

# Streamlit 初期設定
st.set_page_config(page_title="日報管理システム", layout="wide")

# ログイン画面
def login():
    st.title("ログイン")
    user_name = st.text_input("名前", key="user_name_input")
    login_button = st.button("ログイン", key="login_button")
    
    if login_button and user_name:
        st.session_state["user"] = user_name
        st.success(f"ログイン成功！ようこそ、{user_name}さん！")

# 日報投稿
def post_report():
    st.title("日報投稿")
    with st.form("report_form"):
        category = st.selectbox("カテゴリ", ["営業活動", "社内作業", "その他"], key="category")
        tags = st.text_input("タグ", placeholder="#案件, #改善提案 など", key="tags")
        content = st.text_area("実施内容", placeholder="実施した内容を記入してください", key="content")
        notes = st.text_area("所感・備考", placeholder="所感や備考を記入してください（任意）", key="notes")
        submit = st.form_submit_button("投稿")
        
        if submit:
            if not content:
                st.error("実施内容は必須項目です。")
            else:
                new_report = [
                    st.session_state["user"],
                    category,
                    tags,
                    content,
                    notes,
                    datetime.now().strftime("%Y-%m-%d %H:%M"),
                    0,  # いいね数
                    0   # ナイスファイト数
                ]
                sheet.append_row(new_report)
                st.success("日報を投稿しました！")

# タイムライン表示
def timeline():
    st.title("タイムライン")
    reports = sheet.get_all_values()[1:]  # ヘッダーを除く
    
    if not reports:
        st.info("まだ投稿がありません。")
        return
    
    for idx, report in enumerate(reports):
        with st.container():
            st.subheader(f"{report[0]} - {report[5]}")
            st.write(report[3])
            st.text(f"いいね！ {report[6]} / ナイスファイト！ {report[7]}")
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("いいね！", key=f"like_{idx}"):
                    sheet.update_cell(idx + 2, 7, int(report[6]) + 1)
                    st.experimental_rerun()
            with col2:
                if st.button("ナイスファイト！", key=f"nice_fight_{idx}"):
                    sheet.update_cell(idx + 2, 8, int(report[7]) + 1)
                    st.experimental_rerun()

# マイページ
def my_page():
    st.title("マイページ")
    user = st.session_state["user"]
    reports = sheet.get_all_values()[1:]  # ヘッダーを除く
    user_reports = [r for r in reports if r[0] == user]
    
    if not user_reports:
        st.info("あなたの投稿はまだありません。")
        return
    
    st.subheader(f"{user} さんの投稿一覧")
    for report in user_reports:
        st.write(f"{report[5]} - {report[3]}")
    
    total_likes = sum(int(r[6]) for r in user_reports)
    total_nice_fights = sum(int(r[7]) for r in user_reports)
    st.text(f"総いいね数: {total_likes} / 総ナイスファイト数: {total_nice_fights}")

# お知らせ
def notice():
    st.title("お知らせ")
    notices = notice_sheet.get_all_values()[1:]
    
    if not notices:
        st.info("現在お知らせはありません。")
        return
    
    for notice in notices:
        st.subheader(f"{notice[0]} - {notice[1]}")
        st.write(notice[2])

# メイン処理
if "user" not in st.session_state:
    st.session_state["user"] = None

if st.session_state["user"] is None:
    login()
else:
    menu = st.sidebar.radio("メニュー", ["タイムライン", "日報投稿", "マイページ", "お知らせ"])
    if menu == "タイムライン":
        timeline()
    elif menu == "日報投稿":
        post_report()
    elif menu == "マイページ":
        my_page()
    elif menu == "お知らせ":
        notice()
