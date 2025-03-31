# ok-nippou.py
import sys
import os
import time
import streamlit as st
import pandas as pd
import base64
from datetime import datetime, timedelta
import json
import sqlite3
from collections import defaultdict
import psycopg2
from psycopg2.extras import DictCursor

# データベース接続の最適化
@st.cache_data
def get_db_connection():
    try:
        conn = st.connection(
            name="neon",
            type="sql",
            url=st.secrets.connections.neon.url
        )
        return conn
    except Exception as e:
        print(f"⚠️ データベース接続エラー: {e}")
        raise

# ヘルパー関数: 現在時刻に9時間を加算
def get_current_time():
    return datetime.now() + timedelta(hours=9)  # JSTで現在時刻を取得

# CSSファイルの読み込み
def load_css(file_name):
    with open(file_name) as f:
        st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

# データベースのパス
DB_PATH = "/mount/src/ok-nippou-kun/data/reports.db"

# セッション状態の最適化
def initialize_session_state():
    if "user" not in st.session_state:
        st.session_state["user"] = None
    if "page" not in st.session_state:
        st.session_state["page"] = "ログイン"

# ページ遷移の改善
def switch_page(page_name):
    """ページを切り替える（必要な場合のみリロード）"""
    st.session_state["page"] = page_name
    if st.session_state.get("needs_rerun", False):
        st.experimental_rerun()

# サイドバーナビゲーションの改善
def sidebar_navigation():
    with st.sidebar:
        # 画像表示（サイドバー上部）
        st.image("OK-Nippou5.png", use_container_width=True)
        
        # ナビゲーションボタン
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
            
        if st.button("📅 週間予定", key="sidebar_weekly"):
            switch_page("週間予定")
            
        if st.button("🔔 お知らせ", key="sidebar_notice"):
            switch_page("お知らせ")
            
        if st.button("✈️ 週間予定投稿", key="sidebar_post_schedule"):
            switch_page("週間予定投稿")
            
        if st.button("📝 日報作成", key="sidebar_post_report"):
            switch_page("日報投稿")
            
        if st.button("👤 マイページ", key="sidebar_mypage"):
            switch_page("マイページ")

# ログイン機能の改善
def login():
    # ロゴ表示（中央揃え）
    col1, col2, col3 = st.columns([1, 3, 1])
    with col2:
        st.image("OK-Nippou4.png", use_container_width=True)
    
    st.title(" ログイン")
    employee_code = st.text_input("社員コード")
    password = st.text_input("パスワード", type="password")
    login_button = st.button("ログイン")
    
    if login_button:
        user = authenticate_user(employee_code, password)
        if user:
            st.session_state["user"] = user
            st.success(f"ようこそ、{user['name']} さん！（{', '.join(user['depart'])}）")
            switch_page("タイムライン")
        else:
            st.error("社員コードまたはパスワードが間違っています。")

# データベース操作の最適化
@st.cache_data
def load_reports():
    """日報データを取得（最新の投稿順にソート）"""
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=DictCursor)
    
    try:
        # データ取得を最適化
        cur.execute("""
            SELECT * FROM reports 
            WHERE 投稿日時 >= (NOW() - INTERVAL '7 days')
            ORDER BY 投稿日時 DESC
            LIMIT 100
        """)
        
        rows = cur.fetchall()
        return [dict(row) for row in rows]
    except Exception as e:
        print(f"⚠️ データ取得エラー: {e}")
        return []
    finally:
        cur.close()

# タイムライン表示の改善
def timeline():
    if "user" not in st.session_state or st.session_state["user"] is None:
        st.error("ログインしてください。")
        return
    
    st.title(" タイムライン")
    reports = load_reports()
    
    # 期間選択の改善
    st.sidebar.subheader("表示期間を選択")
    period_option = st.sidebar.radio(
        "表示する期間を選択",
        ["24時間以内の投稿", "1週間以内の投稿", "過去の投稿"],
        index=0,
        key="timeline_period_selector"
    )
    
    # データフィルタリングの最適化
    filtered_reports = []
    for report in reports:
        report_datetime = datetime.strptime(report["投稿日時"], "%Y-%m-%d %H:%M:%S")
        
        if period_option == "24時間以内の投稿":
            if report_datetime >= (datetime.now() + timedelta(hours=9)) - timedelta(hours=24):
                filtered_reports.append(report)
        elif period_option == "1週間以内の投稿":
            if report_datetime >= (datetime.now() + timedelta(hours=9)) - timedelta(days=7):
                filtered_reports.append(report)
        else:
            filtered_reports.append(report)
    
    # 部署フィルタの改善
    if st.session_state.get("filter_department") == "自分の部署":
        user_departments = st.session_state["user"]["depart"]
        try:
            USER_FILE = "data/users_data.json"
            with open(USER_FILE, "r", encoding="utf-8-sig") as file:
                users = json.load(file)
            
            department_members = {
                user["name"] for user in users 
                if any(dept in user_departments for dept in user["depart"])
            }
            filtered_reports = [
                report for report in filtered_reports 
                if report["投稿者"] in department_members
            ]
        except Exception as e:
            st.error(f"⚠️ 部署情報の読み込みエラー: {e}")
            return
    
    # 検索機能の改善
    search_query = st.text_input(" 投稿を検索", "")
    if search_query:
        filtered_reports = [
            report for report in filtered_reports
            if search_query.lower() in report["実施内容"].lower() or
               search_query.lower() in report["所感"].lower() or
               search_query.lower() in report["カテゴリ"].lower() or
               search_query.lower() in report["投稿者"].lower()
        ]
    
    # 投稿表示の最適化
    for report in filtered_reports:
        st.subheader(f"{report['投稿者']} さんの日報 ({report['実行日']})")
        st.write(f" **実施日:** {report['実行日']}")
        st.write(f" **場所:** {report['場所']}")
        st.write(f" **実施内容:** {report['実施内容']}")
        st.write(f" **所感:** {report['所感']}")
        
        # 画像表示の改善
        if report.get("image"):
            try:
                image_data = base64.b64decode(report["image"])
                st.image(image_data, caption="投稿画像", use_container_width=True)
            except Exception as e:
                st.error(f"⚠️ 画像の表示中にエラーが発生しました: {e}")
        
        # リアクションの改善
        col1, col2 = st.columns(2)
        with col1:
            if st.button(f"❤️ {report['いいね']} いいね！", key=f"like_{report['id']}"):
                update_reaction(report["id"], "いいね")
                st.session_state["needs_rerun"] = True
        with col2:
            if st.button(f"💪 {report['ナイスファイト']} ナイスファイト！", key=f"nice_{report['id']}"):
                update_reaction(report["id"], "ナイスファイト")
                st.session_state["needs_rerun"] = True

# コメント機能の改善
def save_comment(report_id, commenter, comment):
    """コメントを保存（トランザクションを使用）"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        with conn:
            # コメントを保存
            cur.execute("""
                UPDATE reports 
                SET コメント = コメント || %s 
                WHERE id = %s
            """, (json.dumps([{
                "投稿者": commenter,
                "日時": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "コメント": comment
            }]), report_id))
            
            # 通知を追加（必要な場合のみ）
            if should_notify(commenter):
                add_notification(report_id, commenter, comment)
                
    except Exception as e:
        print(f"⚠️ コメント保存エラー: {e}")
        raise
    finally:
        cur.close()

# メインアプリケーション
def main():
    initialize_session_state()
    
    if st.session_state["user"] is None:
        login()
    else:
        sidebar_navigation()
        
        if st.session_state["page"] == "タイムライン":
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

if __name__ == "__main__":
    main()
