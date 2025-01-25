import streamlit as st
from datetime import datetime, timedelta
import os
import json

# 初期設定
st.set_page_config(page_title="日報管理システム", layout="wide")

# JSONファイルのパス
data_file = "reports_data.json"

# セッション永続化の保持時間（1週間）
SESSION_DURATION = timedelta(days=7)

# 初期データ設定
if "user" not in st.session_state:
    st.session_state["user"] = None

if "reports" not in st.session_state:
    st.session_state["reports"] = []

if "last_login" not in st.session_state:
    st.session_state["last_login"] = None

if "notifications" not in st.session_state:
    st.session_state["notifications"] = []

# ログイン画面
def login():
    st.title("ログイン")
    employee_code = st.text_input("社員コード", key="employee_code_input")
    password = st.text_input("パスワード", type="password", key="password_input")
    login_button = st.button("ログイン", key="login_button")

    if login_button:
        # 仮のユーザーデータ
        user = {"code": "901179", "password": "okanaga", "name": "野村幸男"}

        if employee_code == user["code"] and password == user["password"]:
            st.session_state.user = user
            st.session_state.last_login = datetime.now()
            st.success(f"ログイン成功！ようこそ、{user['name']}さん！")
        else:
            st.error("社員コードまたはパスワードが間違っています。")

# タイムライン
def timeline():
    st.title("タイムライン")

    # 検索機能
    search_query = st.text_input("検索", placeholder="タグやカテゴリ、内容で検索", key="search_query")
    search_button = st.button("検索", key="search_button")

    # 表示期間フィルター
    now = datetime.now()
    filter_option = st.radio(
        "表示期間",
        ["24時間以内", "3日以内", "5日以内"],
        horizontal=True,
        key="filter_option",
    )

    days_filter = {"24時間以内": 1, "3日以内": 3, "5日以内": 5}.get(filter_option, 5)
    cutoff_date = now - timedelta(days=days_filter)

    # 検索と期間フィルターで絞り込み
    reports = [
        report
        for report in st.session_state["reports"]
        if datetime.strptime(report["投稿日時"], "%Y-%m-%d %H:%M") >= cutoff_date
        and (not search_query or search_query in report["タグ"] or search_query in report["実施内容"] or search_query in report["カテゴリ"])
    ]

    if not reports:
        st.info("該当する投稿がありません。")
        return

    for report in reversed(reports):
        with st.container():
            st.subheader(f"カテゴリ: {report['カテゴリ']} - {report['投稿日時']}")
            if report["得意先"]:
                st.write(f"得意先: {report['得意先']}")
            if report["タグ"]:
                st.write(f"タグ: {report['タグ']}")
            st.write(f"実施内容: {report['実施内容']}")
            if report["所感・備考"]:
                st.write(f"所感・備考: {report['所感・備考']}")
            if report["画像"]:
                try:
                    st.image(report["画像"].read(), caption=report["画像"].name, use_container_width=True)
                except Exception as e:
                    st.warning("画像の読み込み中にエラーが発生しました。")

            # スタンプ機能
            if st.button(f"いいね！ ({report.get('いいね', 0)})", key=f"like_{report['投稿日時']}"):
                report["いいね"] = report.get("いいね", 0) + 1
                save_data(data_file, st.session_state["reports"])
                st.experimental_rerun()

            if st.button(f"ナイスファイト！ ({report.get('ナイスファイト', 0)})", key=f"fight_{report['投稿日時']}"):
                report["ナイスファイト"] = report.get("ナイスファイト", 0) + 1
                save_data(data_file, st.session_state["reports"])
                st.experimental_rerun()


# マイページ
def my_page():
    st.title("マイページ")
    user_reports = [r for r in st.session_state["reports"] if r["投稿者"] == st.session_state.user["name"]]

    if not user_reports:
        st.info("まだ投稿がありません。")
        return

    for report in reversed(user_reports):
        with st.container():
            st.subheader(f"カテゴリ: {report['カテゴリ']} - {report['投稿日時']}")
            if report["得意先"]:
                st.write(f"得意先: {report['得意先']}")
            if report["タグ"]:
                st.write(f"タグ: {report['タグ']}")
            st.write(f"実施内容: {report['実施内容']}")
            if report["所感・備考"]:
                st.write(f"所感・備考: {report['所感・備考']}")

            # 修正・削除ボタン
            if st.button("修正", key=f"edit_{report['投稿日時']}"):
                st.write("編集フォーム（未実装）")

            if st.button("削除", key=f"delete_{report['投稿日時']}"):
                st.session_state["reports"].remove(report)
                save_data(data_file, st.session_state["reports"])
                st.success("投稿を削除しました。")
                st.experimental_rerun()


# お知らせ
def notifications():
    st.title("お知らせ")
    if not st.session_state["notifications"]:
        st.info("お知らせはありません。")
        return

    for notification in reversed(st.session_state["notifications"]):
        st.write(notification)
        st.write("---")


# メイン処理
if st.session_state.user is None:
    if st.session_state.last_login and datetime.now() - st.session_state.last_login < SESSION_DURATION:
        st.session_state.user = {"code": "901179", "name": "野村幸男"}
    else:
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
        notifications()
