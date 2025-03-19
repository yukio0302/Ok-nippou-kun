import sys
import os
import time
import streamlit as st
import pandas as pd
import base64
from datetime import datetime, timedelta
import json
import sqlite3

# ヘルパー関数: 現在時刻に9時間を加算する
def get_current_time():
    return datetime.now() + timedelta(hours=9)

# サブコーディングから必要な関数をインポート
from db_utils import (
    init_db, authenticate_user, save_report, load_reports, 
    load_notices, mark_notice_as_read, edit_report, delete_report, 
    update_reaction, save_comment, load_commented_reports,
    save_weekly_schedule_comment, add_comments_column,
    save_weekly_schedule, load_weekly_schedules  # 追加
)

# データベースのパス
DB_PATH = "/mount/src/ok-nippou-kun/Ok-nippou-kun/data/reports.db"

# SQLite 初期化（データを消さない）
init_db(keep_existing=True)
add_comments_column()

# ログイン状態を管理
if "user" not in st.session_state:
    st.session_state["user"] = None
if "page" not in st.session_state:
    st.session_state["page"] = "ログイン"

# ページ遷移関数
def switch_page(page_name):
    st.session_state["page"] = page_name

# ナビゲーションバー
def top_navigation():
    st.markdown("""
    <style>
        .nav-bar {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            background-color: #ffffff;
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 10px;
            padding: 10px;
            border-bottom: 1px solid #ccc;
            box-shadow: 0 2px 5px rgba(0, 0, 0, 0.1);
            z-index: 9999;
        }
        .nav-item {
            text-align: center;
            font-size: 14px;
            padding: 10px;
            cursor: pointer;
            color: #666;
            background-color: #f8f8f8;
            border-radius: 5px;
        }
        .nav-item.active {
            color: black;
            font-weight: bold;
            background-color: #ddd;
        }
        @media (max-width: 600px) {
            .nav-bar {
                grid-template-columns: repeat(2, 1fr);
            }
        }
    </style>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        if st.button("⏳ タイムライン"):
            st.session_state.page = "タイムライン"
            st.rerun()
        if st.button(" 週間予定投稿"):
            st.session_state.page = "週間予定投稿"
            st.rerun()
    with col2:
        if st.button(" お知らせ"):
            st.session_state.page = "お知らせ"
            st.rerun()
        if st.button("✏️ 日報投稿"):
            st.session_state.page = "日報投稿"
            st.rerun()

    if st.button(" マイページ"):
        st.session_state.page = "マイページ"
        st.rerun()

    if "page" not in st.session_state:
        st.session_state.page = "タイムライン"
        
# ログイン機能
def login():
    st.title(" ログイン")
    employee_code = st.text_input("社員コード")
    password = st.text_input("パスワード", type="password")
    login_button = st.button("ログイン")

    if login_button:
        user = authenticate_user(employee_code, password)
        if user:
            st.session_state["user"] = user
            st.success(f"ようこそ、{user['name']} さん！（{', '.join(user['depart'])}）")
            time.sleep(1)
            st.session_state["page"] = "タイムライン"
            st.rerun()
        else:
            st.error("社員コードまたはパスワードが間違っています。")

# 週間予定投稿
def post_weekly_schedule():
    if "user" not in st.session_state or st.session_state["user"] is None:
        st.error("ログインしてください。")
        return

    st.title("週間予定投稿")
    top_navigation()

    today = datetime.today().date()
    start_date = st.date_input("開始日", today)
    end_date = st.date_input("終了日", today + timedelta(days=6))

    st.subheader("各曜日の予定を入力してください")
    monday = st.text_area("月曜日の予定")
    tuesday = st.text_area("火曜日の予定")
    wednesday = st.text_area("水曜日の予定")
    thursday = st.text_area("木曜日の予定")
    friday = st.text_area("金曜日の予定")
    saturday = st.text_area("土曜日の予定")
    sunday = st.text_area("日曜日の予定")

    submit_button = st.button("投稿する")
    if submit_button:
        schedule = {
            "投稿者": st.session_state["user"]["name"],
            "開始日": start_date.strftime("%Y-%m-%d"),
            "終了日": end_date.strftime("%Y-%m-%d"),
            "月曜日": monday,
            "火曜日": tuesday,
            "水曜日": wednesday,
            "木曜日": thursday,
            "金曜日": friday,
            "土曜日": saturday,
            "日曜日": sunday
        }
        save_weekly_schedule(schedule)
        st.success("✅ 週間予定を投稿しました！")
        time.sleep(1)
        switch_page("タイムライン")

# 週間予定表示
def show_weekly_schedules():
    if "user" not in st.session_state or st.session_state["user"] is None:
        st.error("ログインしてください。")
        return

    st.title("週間予定")
    top_navigation()

    schedules = load_weekly_schedules()

    if not schedules:
        st.info("週間予定はありません。")
        return

    for schedule in schedules:
        with st.expander(f"{schedule['投稿者']} さんの週間予定 ({schedule['開始日']} ～ {schedule['終了日']})"):
            st.write(f"**月曜日:** {schedule['月曜日']}")
            st.write(f"**火曜日:** {schedule['火曜日']}")
            st.write(f"**水曜日:** {schedule['水曜日']}")
            st.write(f"**木曜日:** {schedule['木曜日']}")
            st.write(f"**金曜日:** {schedule['金曜日']}")
            st.write(f"**土曜日:** {schedule['土曜日']}")
            st.write(f"**日曜日:** {schedule['日曜日']}")
            st.write(f"**投稿日時:** {schedule['投稿日時']}")
            
            comment_str = schedule.get("コメント")
            if not isinstance(comment_str, str):
                comment_str = "[]" # 文字列でない場合は空のJSON配列を使用
            comments = json.loads(comment_str)
            st.subheader(" コメント")
            for c in comments:
                st.write(f"️ {c['投稿者']} ({c['日時']}): {c['コメント']}")

            comment_text = st.text_area(f"コメントを入力 (ID: {schedule['id']})", key=f"comment_{schedule['id']}")
            if st.button(f"コメントを投稿", key=f"submit_{schedule['id']}"):
                if comment_text.strip():
                    save_weekly_schedule_comment(schedule["id"], st.session_state["user"]["name"], comment_text)
                    st.rerun()
                else:
                    st.warning("コメントを入力してください。")

# 日報投稿
def post_report():
    if "user" not in st.session_state or st.session_state["user"] is None:
        st.error("ログインしてください。")
        return

    st.title("日報投稿")
    top_navigation()

    today = datetime.today().date()
    date_options = [(today + timedelta(days=1) - timedelta(days=i)) for i in range(9)]
    date_options_formatted = [f"{d.strftime('%Y年%m月%d日 (%a)')}" for d in date_options]

    selected_date = st.selectbox("実施日", date_options_formatted)
    location = st.text_input("場所")
    category = st.text_input("カテゴリ（商談やイベント提案など）")
    content = st.text_area("実施内容")
    remarks = st.text_area("所感")

    uploaded_file = st.file_uploader("写真を選択", type=["png", "jpg", "jpeg"])
    image_base64 = None
    if uploaded_file is not None:
        image_bytes = uploaded_file.getvalue()
        image_base64 = base64.b64encode(image_bytes).decode('utf-8')

    submit_button = st.button("投稿する")
    if submit_button:
        date_mapping = {d.strftime('%Y年%m月%d日 (%a)'): d.strftime('%Y-%m-%d') for d in date_options}
        formatted_date = date_mapping[selected_date]

        save_report({
            "投稿者": st.session_state["user"]["name"],
            "実行日": formatted_date,
            "カテゴリ": category, 
            "場所": location,
            "実施内容": content,
            "所感": remarks,
            "image": image_base64
        })
        st.success("✅ 日報を投稿しました！")
        time.sleep(1)
        switch_page("タイムライン")

# タイムライン
def timeline():
    if "user" not in st.session_state or st.session_state["user"] is None:
        st.error("ログインしてください。")
        return

    st.title(" タイムライン")
    top_navigation()

    if st.button(" 週間予定"):
        st.session_state["page"] = "週間予定"
        st.rerun()

    reports = load_reports()

    st.sidebar.subheader("表示期間を選択")
    period_option = st.sidebar.radio(
        "表示する期間を選択",
        ["24時間以内の投稿", "1週間以内の投稿", "過去の投稿"],
        index=0
    )

    if period_option == "24時間以内の投稿":
        start_datetime = datetime.now() + timedelta(hours=9) - timedelta(hours=24)
        end_datetime = datetime.now() + timedelta(hours=9)
    elif period_option == "1週間以内の投稿":
        start_datetime = datetime.now() + timedelta(hours=9) - timedelta(days=7)
        end_datetime = datetime.now() + timedelta(hours=9)
    else:
        st.sidebar.subheader("過去の投稿を表示")
        col1, col2 = st.sidebar.columns(2)
        with col1:
            start_date = st.date_input("開始日", datetime.now().date() - timedelta(days=365), max_value=datetime.now().date() - timedelta(days=1))
        with col2:
            end_date = st.date_input("終了日", datetime.now().date() - timedelta(days=1), min_value=start_date, max_value=datetime.now().date() - timedelta(days=1))
        start_datetime = datetime(start_date.year, start_date.month, start_date.day)
        end_datetime = datetime(end_date.year, end_date.month, end_date.day) + timedelta(days=1)

    filtered_reports = []
    for report in reports:
        report_datetime = datetime.strptime(report["投稿日時"], "%Y-%m-%d %H:%M:%S")
        if start_datetime <= report_datetime <= end_datetime:
            filtered_reports.append(report)

    user_departments = st.session_state["user"]["depart"]

    if "filter_department" not in st.session_state:
        st.session_state["filter_department"] = "すべて"

    col1, col2 = st.columns(2)
    with col1:
        if st.button(" すべての投稿を見る"):
            st.session_state["filter_department"] = "すべて"
            st.rerun()
    
    with col2:
        if st.button(" 自分の部署のメンバーの投稿を見る"):
            st.session_state["filter_department"] = "自分の部署"
            st.rerun()

    if st.session_state["filter_department"] == "自分の部署":
        try:
            USER_FILE = "data/users_data.json"
            with open(USER_FILE, "r", encoding="utf-8-sig") as file:
                users = json.load(file)

            department_members = {
                user["name"] for user in users if any(dept in user_departments for dept in user["depart"])
            }

            filtered_reports = [report for report in filtered_reports if report["投稿者"] in department_members]
        
        except Exception as e:
            st.error(f"⚠️ 部署情報の読み込みエラー: {e}")
            return

    search_query = st.text_input(" 投稿を検索", "")

    if search_query:
        filtered_reports = [
            report for report in filtered_reports
            if search_query.lower() in report["実施内容"].lower()
            or search_query.lower() in report["所感"].lower()
            or search_query.lower() in report["カテゴリ"].lower()
            or search_query.lower() in report["投稿者"].lower()
        ]

    if not filtered_reports:
        st.warning(" 該当する投稿が見つかりませんでした。")
        return

    for report in filtered_reports:
        st.subheader(f"{report['投稿者']} さんの日報 ({report['実行日']})")
        st.write(f" **実施日:** {report['実行日']}")
        st.write(f" **場所:** {report['場所']}")
        st.write(f" **実施内容:** {report['実施内容']}")
        st.write(f" **所感:** {report['所感']}")

        if report.get("image"):
            try:
                image_data = base64.b64decode(report["image"])
                st.image(image_data, caption="投稿画像", use_container_width=True)
            except Exception as e:
                st.error(f"⚠️ 画像の表示中にエラーが発生しました: {e}")

        col1, col2 = st.columns(2)
        with col1:
            if st.button(f"❤️ {report['いいね']} いいね！", key=f"like_{report['id']}"):
                update_reaction(report["id"], "いいね")
                st.rerun()
        with col2:
            if st.button(f" {report['ナイスファイト']} ナイスファイト！", key=f"nice_{report['id']}"):
                update_reaction(report["id"], "ナイスファイト")
                st.rerun()

        comment_count = len(report["コメント"]) if report["コメント"] else 0
        with st.expander(f" ({comment_count}件)のコメントを見る・追加する "):
            if report["コメント"]:
                for c in report["コメント"]:
                    st.write(f" {c['投稿者']} ({c['日時']}): {c['コメント']}")

            if report.get("id") is None:
                st.error("⚠️ 投稿の ID が見つかりません。")
                continue

            commenter_name = st.session_state["user"]["name"] if st.session_state["user"] else "匿名"
            new_comment = st.text_area(f"✏️ {commenter_name} さんのコメント", key=f"comment_{report['id']}")

            if st.button(" コメントを投稿", key=f"submit_comment_{report['id']}"):
                if new_comment and new_comment.strip():
                    print(f"️ コメント投稿デバッグ: report_id={report['id']}, commenter={commenter_name}, comment={new_comment}")
                    save_comment(report["id"], commenter_name, new_comment)
                    st.success("✅ コメントを投稿しました！")
                    st.rerun()
                else:
                    st.warning("⚠️ 空白のコメントは投稿できません！")

    st.write("----")

# お知らせ表示
def show_notices():
    if "user" not in st.session_state or st.session_state["user"] is None:
        st.error("ログインしてください。")
        return

    st.title(" お知らせ")
    top_navigation()

    user_name = st.session_state["user"]["name"]

    notices = load_notices(user_name)

    if not notices:
        st.info(" お知らせはありません。")
        return

    if "notice_to_read" not in st.session_state:
        st.session_state["notice_to_read"] = None

    new_notices = [n for n in notices if n["既読"] == 0]
    old_notices = [n for n in notices if n["既読"] == 1]

    if new_notices:
        st.subheader(" 新着お知らせ")
        for notice in new_notices:
            with st.container():
                st.markdown(f"### {notice['タイトル']} ✅")
                st.write(f" {notice['日付']}")
                st.write(notice["内容"])

                if st.button(f"✔️ 既読にする", key=f"read_{notice['id']}"):
                    st.session_state["notice_to_read"] = notice["id"]

    if st.session_sion_state["notice_to_read"] is not None:
        mark_notice_as_read(st.session_state["notice_to_read"])
        st.session_state["notice_to_read"] = None
        st.rerun()

    if old_notices:
        with st.expander(" 過去のお知らせを見る"):
            for notice in old_notices:
                with st.container():
                    st.markdown(f"**{notice['タイトル']}**")
                    st.write(f" {notice['日付']}")
                    st.write(notice["内容"])

# マイページ
def my_page():
    if "user" not in st.session_state or st.session_state["user"] is None:
        st.error("ログインしてください。")
        return

    st.title("マイページ")
    top_navigation()

    reports = load_reports()
    my_reports = [r for r in reports if r["投稿者"] == st.session_state["user"]["name"]]

    with st.expander("今週の投稿", expanded=False):
        now = datetime.utcnow()
        start_of_week = now - timedelta(days=now.weekday())
        end_of_week = start_of_week + timedelta(days=4)
        
        weekly_reports = [
            r for r in my_reports
            if start_of_week.date() <= datetime.strptime(r["実行日"], "%Y-%m-%d").date() <= end_of_week.date()
        ]

        if weekly_reports:
            for report in weekly_reports:
                st.markdown(f"**{report['実行日']} / {report['場所']}**")
                show_report_details(report)
        else:
            st.info("今週の投稿はありません。")

    with st.expander("過去の投稿", expanded=False):
        past_reports = [r for r in my_reports if r not in weekly_reports]

        if past_reports:
            for report in past_reports:
                st.markdown(f"**{report['実行日']} / {report['場所']}**")
                show_report_details(report)
        else:
            st.info("過去の投稿はありません。")

    with st.expander("コメントした投稿", expanded=False):
        commented_reports = load_commented_reports(st.session_state["user"]["name"])

        if commented_reports:
            for report in commented_reports:
                st.markdown(f"**{report['投稿者']} さんの日報 ({report['実行日']})**")
                show_report_details(report)
        else:
            st.info("コメントした投稿はありません。")

def show_report_details(report):
    st.write(f" **場所:** {report['場所']}")
    st.write(f" **実施内容:** {report['実施内容']}")
    st.write(f" **所感:** {report['所感']}")

    if report.get("image"):
        try:
            image_data = base64.b64decode(report["image"])
            st.image(image_data, caption="投稿画像", use_container_width=True)
        except Exception as e:
            st.error(f"⚠️ 画像の表示中にエラーが発生しました: {e}")

    col1, col2 = st.columns(2)
    with col1:
        st.write(f"❤️ {report['いいね']} いいね！")
    with col2:
        st.write(f" {report['ナイスファイト']} ナイスファイト！")

    if report["コメント"]:
        for c in report["コメント"]:
            st.write(f" {c['投稿者']} ({c['日時']}): {c['コメント']}")
    st.write("----")

# ページの表示
if st.session_state["user"] is None:
    login()
elif st.session_state["page"] == "タイムライン":
    timeline()
elif st.session_state["page"] == "日報投稿":
    post_report()
elif st.session_state["page"] == "お知らせ":
    show_notices()
elif st.session_state["page"] == "マイページ":
    my_page()
elif st.session_state["page"] == "週間予定投稿":
    post_weekly_schedule()
elif st.session_state["page"] == "週間予定":
    show_weekly_schedules()
