import sys
import os
import time
import streamlit as st
import pandas as pd
import base64
from datetime import datetime, timedelta
import json
import sqlite3

import sys
sys.path.append("/mount/src/ok-nippou-kun/Ok-nippou-kun")

# サブコードから必要な関数をインポート
from db_utils import (
    init_db, authenticate_user, save_report, load_reports,
    load_notices, mark_notice_as_read, edit_report, delete_report,
    update_reaction, save_comment, load_commented_reports,
    save_weekly_schedule_comment, add_comments_column,
    save_weekly_schedule, load_weekly_schedules, update_weekly_schedule
)

# 設定
DB_PATH = "/mount/src/ok-nippou-kun/Ok-nippou-kun/data/reports.db"
init_db(keep_existing=True)
add_comments_column()

# セッション状態の初期化
SESSION_DEFAULTS = {
    "user": None,
    "page": "ログイン",
    "filter_department": "すべて",
    "notice_to_read": None
}

for key, value in SESSION_DEFAULTS.items():
    if key not in st.session_state:
        st.session_state[key] = value

# 共通ユーティリティ関数
def get_current_time():
    return datetime.now() + timedelta(hours=9)

def switch_page(page_name):
    st.session_state["page"] = page_name
    st.rerun()

# UIコンポーネント
def top_navigation():
    st.markdown("""
    <style>
        /* ナビゲーションバーのスタイル（簡潔化） */
        .nav-bar { position: fixed; top: 0; width: 100%; padding: 10px; z-index: 9999; }
        .nav-item { padding: 10px; border-radius: 5px; }
    </style>
    """, unsafe_allow_html=True)

    PAGES = {
        "⏳ タイムライン": "タイムライン",
        "📅 週間予定投稿": "週間予定投稿",
        "🔔 お知らせ": "お知らせ",
        "✏️ 日報投稿": "日報投稿",
        "🚹 マイページ": "マイページ"
    }

    cols = st.columns(len(PAGES))
    for (label, page), col in zip(PAGES.items(), cols):
        with col:
            if st.button(label):
                switch_page(page)

# ページコンポーネント
def login_page():
    st.title("ログイン")
    employee_code = st.text_input("社員コード")
    password = st.text_input("パスワード", type="password")
    
    if st.button("ログイン"):
        if user := authenticate_user(employee_code, password):
            st.session_state.user = user
            st.success(f"ようこそ、{user['name']} さん！")
            time.sleep(1)
            switch_page("タイムライン")
        else:
            st.error("認証に失敗しました")

def report_post_page():
    st.title("日報投稿")
    top_navigation()
    
    today = datetime.today().date()
    date_options = [today - timedelta(days=i) for i in range(7, -1, -1)]
    selected_date = st.selectbox("実施日", date_options).strftime("%Y-%m-%d")
    
    form_data = {
        "location": st.text_input("場所"),
        "category": st.text_input("カテゴリ"),
        "content": st.text_area("実施内容"),
        "remarks": st.text_area("所感"),
        "image": None
    }
    
    if uploaded_file := st.file_uploader("写真を選択", type=["png", "jpg", "jpeg"]):
        form_data["image"] = base64.b64encode(uploaded_file.getvalue()).decode('utf-8')
    
    if st.button("投稿する"):
        save_report({
            "投稿者": st.session_state.user["name"],
            "実行日": selected_date,
            **{k: v for k, v in form_data.items() if k != "image"},
            "image": form_data["image"]
        })
        st.success("✅ 日報を投稿しました！")
        time.sleep(1)
        switch_page("タイムライン")

# 他のページコンポーネントも同様に整理（タイムライン、お知らせ、マイページ等）

# メインルーティング
if not st.session_state.user:
    login_page()
else:
    PAGE_HANDLERS = {
        "タイムライン": timeline_page,
        "日報投稿": report_post_page,
        "お知らせ": notice_page,
        "マイページ": mypage_page,
        "週間予定投稿": weekly_schedule_post_page,
        "週間予定": weekly_schedule_page
    }
    PAGE_HANDLERS.get(st.session_state.page, lambda: st.error("ページが見つかりません"))()
