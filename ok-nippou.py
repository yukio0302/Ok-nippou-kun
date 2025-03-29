import os
import time
import streamlit as st
import pandas as pd
import base64
from datetime import datetime, timedelta, timezone  # timezoneを追加
import json
import psycopg2
from collections import defaultdict
import sys
sys.path.append('/mount/src/ok-nippou-kun/')  # db_utils.py があるディレクトリ

from db_utils import (
    init_db, authenticate_user, save_report, load_reports,
    load_notices, mark_notice_as_read, edit_report, delete_report,
    update_reaction, save_comment, load_commented_reports,
    save_weekly_schedule_comment, load_weekly_schedules, load_comments,
    get_db_connection
)

# ヘルパー関数: 現在時刻に9時間を加算する
def get_current_time():
    return datetime.now() + timedelta(hours=9)  # JSTで現在時刻を取得

# excel_utils.py をインポート
import excel_utils  # この行を追加

# 絶対パスでCSSファイルを読み込む関数
def load_css(file_name):
    with open(file_name) as f:  # 絶対パスをそのまま使用
        st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

# 絶対パスでCSSファイルを読み込む
css_file_path = "style.css"  # 絶対パスを設定
load_css(css_file_path)

# ✅ データベースの初期化
init_db()

# ✅ ログイン状態を管理
if "user" not in st.session_state:
    st.session_state["user"] = None
if "page" not in st.session_state:
    st.session_state["page"] = "ログイン"

# ✅ ページ遷移関数（修正済み）
def switch_page(page_name):
    """ページを切り替える（即時リロードはなし！）"""
    st.session_state["page"] = page_name

# ✅ サイドバーナビゲーションの追加
def sidebar_navigation():
    with st.sidebar:
         # 画像表示（サイドバー上部）
        st.image("OK-Nippou5.png", use_container_width=True)
        
        # ナビゲーションボタン
        st.markdown("""
        <style>
            /* 画像とボタンの間隔調整 */
            .stImage {
                margin-bottom: 30px !important;
            }
        </style>
        """, unsafe_allow_html=True)
        st.markdown("""
        <style>
            .sidebar-menu {
                color: white !important;
                margin-bottom: 30px;
            }
        </style>
        """, unsafe_allow_html=True)
        
        # ナビゲーションボタン
        if st.button("⏳ タイムライン", key="sidebar_timeline"):
            switch_page("タイムライン")
            
        if st.button(" 週間予定", key="sidebar_weekly"):
            switch_page("週間予定")
            
        if st.button(" お知らせ", key="sidebar_notice"):
            switch_page("お知らせ")
            
        if st.button("✈️ 週間予定投稿", key="sidebar_post_schedule"):
            switch_page("週間予定投稿")
            
        if st.button(" 日報作成", key="sidebar_post_report"):
            switch_page("日報投稿")
            
        if st.button(" マイページ", key="sidebar_mypage"):
            switch_page("マイページ")

# ✅ ログイン機能（修正済み）
def login():
    # ロゴ表示（中央揃え）
    col1, col2, col3 = st.columns([1, 3, 1])
    with col2:
        st.image("OK-Nippou4.png", use_container_width=True)  # 画像をコンテナ幅に合わせる

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
            st.rerun()  # ✅ ここで即リロード！
        else:
            st.error("社員コードまたはパスワードが間違っています。")

def save_weekly_schedule(schedule):
    """週間予定をデータベースに保存"""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO posts (投稿者ID) VALUES (%s) RETURNING id
    """, (st.session_state["user"]["id"],))
    post_id = cur.fetchone()[0]
    cur.execute("""
        INSERT INTO weekly_schedules (postId, 開始日, 終了日, 月曜日, 火曜日, 水曜日, 木曜日, 金曜日, 土曜日, 日曜日)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """, (post_id, schedule["開始日"], schedule["終了日"], schedule["月曜日"], schedule["火曜日"], schedule["水曜日"], schedule["木曜日"], schedule["金曜日"], schedule["土曜日"], schedule["日曜日"]))
    conn.commit()
    conn.close()

# ✅ 週間予定投稿ページ
def post_weekly_schedule():
    st.title("週間予定投稿")
    start_date = st.date_input("開始日")
    end_date = st.date_input("終了日")

    weekdays = ["月曜日", "火曜日", "水曜日", "木曜日", "金曜日", "土曜日", "日曜日"]
    schedule = {"開始日": start_date, "終了日": end_date}
    for day in weekdays:
        schedule[day] = st.text_area(day)

    if st.button("投稿"):
        save_weekly_schedule(schedule)
        st.success("週間予定を投稿しました！")

# ✅ 週間予定ページ
def weekly_schedule():
    schedules = load_weekly_schedules()
    st.title("週間予定")

    for schedule in schedules:
        st.subheader(f"{schedule['投稿者']} さんの週間予定 ({schedule['開始日']} ~ {schedule['終了日']})")
        
        # タイムゾーンを日本時間に変更
        jst = timezone(timedelta(hours=+9), name='JST')
        schedule_time = schedule['投稿日時'].astimezone(jst) if schedule['投稿日時'] else None
        
        st.caption(f"投稿日時: {schedule_time.strftime('%Y-%m-%d %H:%M:%S')}")

        weekdays = ["月曜日", "火曜日", "水曜日", "木曜日", "金曜日", "土曜日", "日曜日"]
        for day in weekdays:
            st.write(f"**{day}**: {schedule[day]}")
            
        comment_count = len(schedule["コメント"]) if schedule["コメント"] else 0  # コメント件数を取得
        with st.expander(f" ({comment_count}件)のコメントを見る・追加する "):  # 件数を表示
            if schedule["コメント"]:
                for c in schedule["コメント"]:
                    st.write(f" {c['投稿者']} ({c['投稿日時']}): {c['コメント内容']}")

            comment_content = st.text_area("コメントを入力")
            if st.button("コメントを投稿", key=f"comment_{schedule['id']}"):
                save_weekly_schedule_comment(schedule["id"], st.session_state["user"]["id"], comment_content)
                st.success("コメントを投稿しました！")
                st.rerun()

# ✅ 日報投稿ページ（修正済み）
def post_report():
    st.title("日報作成")
    report = {
        "投稿者ID": st.session_state["user"]["id"],
        "実行日": st.date_input("実行日"),
        "カテゴリ": st.selectbox("カテゴリ", ["営業", "開発", "その他"]),
        "場所": st.text_input("場所"),
        "実施内容": st.text_area("実施内容"),
        "所感": st.text_area("所感")
    }

    uploaded_file = st.file_uploader("画像アップロード", type=["png", "jpg", "jpeg"])
    if uploaded_file is not None:
        report["image"] = base64.b64encode(uploaded_file.getvalue()).decode("utf-8")

    if st.button("投稿"):
        save_report(report)
        st.success("日報を投稿しました！")

# ✅ タイムライン（コメント機能修正）
def timeline():
    st.title("タイムライン")
    reports = load_reports()

    # 部署フィルタリング（修正済み）
    if st.session_state["user"]["depart"]:  # 部署情報がある場合のみフィルタリング
        filtered_reports = [report for report in reports if any(dept in report["投稿者"] for dept in st.session_state["user"]["depart"])]
    else:
        filtered_reports = reports

    # ✅ 投稿を表示
    for report in filtered_reports:
        st.subheader(f"{report['投稿者']} さんの日報 ({report['実行日']})")
        st.write(f"**場所**: {report['場所']}")
        st.write(f"**カテゴリ**: {report['カテゴリ']}")
        st.write(f"**実施内容**: {report['実施内容']}")
        st.write(f"**所感**: {report['所感']}")
        
        if report["画像パス"]:
            try:
                img_data = base64.b64decode(report["画像パス"])
                st.image(img_data, caption="添付画像", use_column_width=True)
            except Exception as e:
                st.error(f"画像の表示に失敗しました: {e}")

        # 投稿日時
        st.caption(f"投稿日時: {report['投稿日時']}")

        # いいね！ボタン
        if st.button("いいね！", key=f"like_{report['id']}"):
            update_reaction(report["id"], "いいね")
            st.success("いいね！しました")
            st.rerun()

        # ナイスファイト！ボタン
        if st.button("ナイスファイト！", key=f"nice_fight_{report['id']}"):
            update_reaction(report["id"], "ナイスファイト")
            st.success("ナイスファイト！しました")
            st.rerun()

        # コメント欄
        comment_count = len(report["コメント"]) if report["コメント"] else 0  # コメント件数を取得
        with st.expander(f" ({comment_count}件)のコメントを見る・追加する "):  # 件数を表示
            if report["コメント"]:
                for c in report["コメント"]:
                    st.write(f" {c['投稿者']} ({c['投稿日時']}): {c['コメント内容']}")

            comment_content = st.text_area("コメントを入力")
            if st.button("コメントを投稿", key=f"comment_{report['id']}"):
                save_comment(report["id"], st.session_state["user"]["id"], comment_content)
                st.success("コメントを投稿しました！")
                st.rerun()

        # 編集・削除ボタン（投稿者のみ）
        if report["投稿者ID"] == st.session_state["user"]["id"]:
            if st.button("編集", key=f"edit_{report['id']}"):
                st.session_state["edit_report"] = report
                st.session_state["page"] = "日報編集"
                st.rerun()
            if st.button("削除", key=f"delete_{report['id']}"):
                delete_report(report["id"])
                st.success("投稿を削除しました")
                st.rerun()

# ✅ マイページ
def mypage():
    st.title("マイページ")
    st.write(f"**社員コード**: {st.session_state['user']['employee_code']}")
    st.write(f"**名前**: {st.session_state['user']['name']}")
    st.write(f"**部署**: {', '.join(st.session_state['user']['depart'])}")

    # コメントした投稿一覧
    commented_reports = load_commented_reports(st.session_state["user"]["id"])
    if commented_reports:
        st.subheader("コメントした投稿")
        for report in commented_reports:
            st.write(f"- {report['投稿者']} さんの日報 ({report['実行日']})")
    else:
        st.write("コメントした投稿はありません")

# ✅ お知らせページ
def notice():
    st.title("お知らせ")
    notices = load_notices(st.session_state["user"]["id"])

    for notice in notices:
        st.subheader(notice["タイトル"])
        st.write(f"日付: {notice['日付']}")
        st.write(notice["内容"])
        if notice["既読"] == 0:
            if st.button("既読にする", key=f"read_{notice['id']}"):
                mark_notice_as_read(notice["id"])
                st.success("既読にしました")
                st.rerun()

# ✅ 日報編集ページ
def edit_report_page():
    report = st.session_state["edit_report"]
    st.title("日報編集")

    edited_report = {
        "id": report["id"],
        "実行日": st.date_input("実行日", datetime.strptime(report["実行日"], "%Y-%m-%d").date()),
        "カテゴリ": st.selectbox("カテゴリ", ["営業", "開発", "その他"], index=["営業", "開発", "その他"].index(report["カテゴリ"])),
        "場所": st.text_input("場所", report["場所"]),
        "実施内容": st.text_area("実施内容", report["実施内容"]),
        "所感": st.text_area("所感", report["所感"])
    }

    if st.button("保存"):
        edit_report(edited_report)
        st.success("日報を編集しました")
        st.session_state["page"] = "タイムライン"
        st.rerun()

# ✅ ページ表示
if st.session_state["user"] is None:
    login()
else:
    sidebar_navigation()
    
    page_functions = {
        "タイムライン": timeline,
        "日報投稿": post_report,
        "お知らせ": notice,
        "マイページ": mypage,
        "日報編集": edit_report_page,
        "週間予定投稿": post_weekly_schedule,
        "週間予定": weekly_schedule
    }
    
    current_page = st.session_state["page"]
    if current_page in page_functions:
        page_functions[current_page]()
    else:
        st.error("無効なページです")

    # ログアウトボタン
    if st.session_state["user"] and st.sidebar.button("ログアウト"):
        st.session_state["user"] = None
        st.session_state["page"] = "ログイン"
        st.rerun()
        
