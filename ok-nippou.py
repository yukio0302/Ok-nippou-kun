import sys
import os
import time
import streamlit as st
import pandas as pd
import base64
import io
from datetime import datetime, timedelta, timezone
from db_utils import (
    init_db, authenticate_user, save_report, load_reports,
    load_notices, mark_notice_as_read, edit_report, delete_report,
    update_reaction, save_comment, load_commented_reports,
    save_weekly_schedule_comment, load_weekly_schedules, load_comments
)

# 初期設定
init_db()
os.makedirs("uploads", exist_ok=True)

# CSS読み込み
def load_css(file_name):
    with open(file_name) as f:
        st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

load_css("style.css")

# セッション状態管理
if "user" not in st.session_state:
    st.session_state.user = None
if "page" not in st.session_state:
    st.session_state.page = "ログイン"

# ヘルパー関数
def switch_page(page_name):
    st.session_state.page = page_name
    st.rerun()

def get_current_time():
    return datetime.now(timezone.utc) + timedelta(hours=9)

def sidebar_navigation():
    with st.sidebar:
        st.image("OK-Nippou5.png", use_container_width=True)
        
        menu_items = {
            "⏳ タイムライン": "タイムライン",
            "📅 週間予定": "週間予定",
            "📢 お知らせ": "お知らせ",
            "✈️ 週間予定投稿": "週間予定投稿",
            "📝 日報作成": "日報投稿",
            "👤 マイページ": "マイページ"
        }
        
        for label, page in menu_items.items():
            if st.button(label, key=f"menu_{page}"):
                switch_page(page)
                
        if st.session_state.user and st.button("🚪 ログアウト"):
            st.session_state.clear()
            st.rerun()

def login():
    col1, col2, col3 = st.columns([1, 3, 1])
    with col2:
        st.image("OK-Nippou4.png", use_container_width=True)
    
    with st.form("login_form"):
        employee_code = st.text_input("社員コード")
        password = st.text_input("パスワード", type="password")
        
        if st.form_submit_button("ログイン"):
            user = authenticate_user(employee_code, password)
            if user:
                st.session_state.user = {
                    "id": user["id"],
                    "employee_code": user["employee_code"],
                    "name": user["name"],
                    "depart": user["depart"]
                }
                st.session_state.page = "タイムライン"
                st.rerun()
            else:
                st.error("認証に失敗しました")

def export_to_excel(report):
    df = pd.DataFrame([{
        '実行日': report['実行日'],
        'カテゴリ': report['カテゴリ'],
        '場所': report['場所'],
        '実施内容': report['実施内容'],
        '所感': report['所感']
    }])
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False)
    return output.getvalue()

def post_report():
    st.title("日報作成")
    with st.form("report_form"):
        report = {
            "投稿者ID": st.session_state.user["id"],
            "実行日": st.date_input("実行日"),
            "カテゴリ": st.selectbox("カテゴリ", ["営業", "開発", "その他"]),
            "場所": st.text_input("場所"),
            "実施内容": st.text_area("実施内容"),
            "所感": st.text_area("所感"),
            "image_path": None
        }
        
        uploaded_file = st.file_uploader("画像アップロード", type=["png", "jpg", "jpeg"])
        if uploaded_file:
            # Base64とファイル保存のハイブリッド
            report["image_path"] = f"uploads/{uploaded_file.name}"
            with open(report["image_path"], "wb") as f:
                f.write(uploaded_file.getbuffer())
            # Base64も保存
            report["image_base64"] = base64.b64encode(uploaded_file.getvalue()).decode()
        
        if st.form_submit_button("投稿"):
            save_report(report)
            st.success("日報を投稿しました！")
            switch_page("タイムライン")

def timeline():
    st.title("タイムライン")
    reports = load_reports()
    
    # 部署フィルタリング
    if st.session_state.user["depart"]:
        filtered_reports = [
            r for r in reports 
            if any(dept in r["投稿者"] for dept in st.session_state.user["depart"])
        ]
    else:
        filtered_reports = reports

    for report in filtered_reports:
        with st.container(border=True):
            st.markdown(f"**{report['投稿者']}** `{report['カテゴリ']}` **{report['実行日']}**")
            st.caption(f"投稿日時: {report['投稿日時']}")
            
            # 画像表示
            if report["画像パス"]:
                try:
                    if hasattr(report, "image_base64"):  # Base64優先
                        img_data = base64.b64decode(report["image_base64"])
                        st.image(img_data, use_column_width=True)
                    else:
                        st.image(report["画像パス"], use_column_width=True)
                except Exception as e:
                    st.error(f"画像表示エラー: {e}")
            
            # Excel出力
            excel_data = export_to_excel(report)
            st.download_button(
                label="Excelで保存",
                data=excel_data,
                file_name=f"report_{report['id']}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
            
            # リアクションボタン
            col1, col2 = st.columns(2)
            with col1:
                if st.button(f"👍 {report['いいね']}", key=f"like_{report['id']}"):
                    update_reaction(report["id"], "いいね")
                    st.rerun()
            with col2:
                if st.button(f"✨ {report['ナイスファイト']}", key=f"nice_{report['id']}"):
                    update_reaction(report["id"], "ナイスファイト")
                    st.rerun()
            
            # コメントセクション
            with st.expander(f"💬 コメント ({len(report['コメント'])})"):
                for comment in report["コメント"]:
                    st.markdown(f"**{comment['投稿者']}** ({comment['投稿日時']})")
                    st.write(comment["コメント内容"])
                
                with st.form(key=f"comment_{report['id']}"):
                    new_comment = st.text_area("新しいコメントを入力")
                    if st.form_submit_button("コメント投稿"):
                        save_comment(report["id"], st.session_state.user["id"], new_comment)
                        st.rerun()
            
            # 編集/削除ボタン
            if report["投稿者ID"] == st.session_state.user["id"]:
                cols = st.columns(2)
                with cols[0]:
                    if st.button("✏️ 編集", key=f"edit_{report['id']}"):
                        st.session_state.edit_report = report
                        switch_page("日報編集")
                with cols[1]:
                    if st.button("🗑️ 削除", key=f"delete_{report['id']}"):
                        delete_report(report["id"])
                        st.rerun()

def post_weekly_schedule():
    st.title("週間予定投稿")
    with st.form("weekly_schedule_form"):
        start_date = st.date_input("開始日")
        end_date = st.date_input("終了日")
        
        schedule = {
            "開始日": start_date,
            "終了日": end_date,
            "月曜日": st.text_area("月曜日"),
            "火曜日": st.text_area("火曜日"),
            "水曜日": st.text_area("水曜日"),
            "木曜日": st.text_area("木曜日"),
            "金曜日": st.text_area("金曜日"),
            "土曜日": st.text_area("土曜日"),
            "日曜日": st.text_area("日曜日")
        }
        
        if st.form_submit_button("投稿"):
            save_weekly_schedule({
                "投稿者ID": st.session_state.user["id"],
                **schedule
            })
            st.success("週間予定を投稿しました！")
            time.sleep(1)
            switch_page("週間予定")

def weekly_schedule():
    st.title("週間予定")
    schedules = load_weekly_schedules()
    
    for schedule in schedules:
        with st.container(border=True):
            st.subheader(f"{schedule['投稿者']} さんの週間予定")
            st.caption(f"{schedule['開始日']} 〜 {schedule['終了日']}")
            st.write(f"投稿日時: {schedule['投稿日時']}")
            
            # 曜日別予定表示
            weekdays = ["月曜日", "火曜日", "水曜日", "木曜日", "金曜日", "土曜日", "日曜日"]
            cols = st.columns(3)
            for i, day in enumerate(weekdays):
                with cols[i % 3]:
                    st.markdown(f"**{day}**")
                    st.write(schedule[day] or "予定なし")
            
            # コメント機能
            comment_count = len(schedule.get("コメント", []))
            with st.expander(f"コメント ({comment_count})"):
                if comment_count > 0:
                    for comment in schedule["コメント"]:
                        st.markdown(f"**{comment['投稿者']}** ({comment['投稿日時']})")
                        st.write(comment["コメント内容"])
                
                with st.form(key=f"weekly_comment_{schedule['id']}"):
                    comment_input = st.text_area("新しいコメントを入力")
                    if st.form_submit_button("コメントを投稿"):
                        save_weekly_schedule_comment(
                            schedule["id"],
                            st.session_state.user["id"],
                            comment_input
                        )
                        st.rerun()

def notice():
    st.title("お知らせ")
    notices = load_notices(st.session_state.user["id"])
    
    for notice in notices:
        with st.container(border=True):
            cols = st.columns([4, 1])
            with cols[0]:
                st.subheader(notice["タイトル"])
                st.write(f"日付: {notice['日付']}")
                st.write(notice["内容"])
            with cols[1]:
                if notice["既読"] == 0:
                    if st.button("既読にする", key=f"read_{notice['id']}"):
                        mark_notice_as_read(notice["id"])
                        st.rerun()
                else:
                    st.markdown("✅ 既読")

def mypage():
    st.title("マイページ")
    
    with st.container(border=True):
        st.markdown("### 基本情報")
        st.write(f"**社員コード**: {st.session_state.user['employee_code']}")
        st.write(f"**名前**: {st.session_state.user['name']}")
        st.write(f"**部署**: {', '.join(st.session_state.user['depart'])}")
    
    with st.container(border=True):
        st.markdown("### コメント履歴")
        commented_reports = load_commented_reports(st.session_state.user["id"])
        if commented_reports:
            for report in commented_reports:
                st.write(f"📝 {report['投稿者']} さんの日報 ({report['実行日']})")
                st.write(f"内容: {report['実施内容'][:50]}...")
        else:
            st.write("コメントした投稿はありません")

def edit_report_page():
    st.title("日報編集")
    report = st.session_state.get("edit_report", None)
    
    if not report:
        st.error("編集する日報が見つかりません")
        switch_page("タイムライン")
        return
    
    with st.form("edit_report_form"):
        edited_report = {
            "id": report["id"],
            "実行日": st.date_input(
                "実行日",
                datetime.strptime(report["実行日"], "%Y-%m-%d").date()
            ),
            "カテゴリ": st.selectbox(
                "カテゴリ",
                ["営業", "開発", "その他"],
                index=["営業", "開発", "その他"].index(report["カテゴリ"])
            ),
            "場所": st.text_input("場所", report["場所"]),
            "実施内容": st.text_area("実施内容", report["実施内容"]),
            "所感": st.text_area("所感", report["所感"])
        }
        
        if st.form_submit_button("保存"):
            edit_report(edited_report)
            st.success("日報を更新しました")
            time.sleep(1)
            switch_page("タイムライン")

# ページ表示制御
if st.session_state.user is None:
    login()
else:
    sidebar_navigation()
    
    page_mapping = {
        "タイムライン": timeline,
        "日報投稿": post_report,
        "お知らせ": notice,
        "マイページ": mypage,
        "日報編集": edit_report_page,
        "週間予定投稿": post_weekly_schedule,
        "週間予定": weekly_schedule
    }
    
    current_page = st.session_state.get("page", "タイムライン")
    if current_page in page_mapping:
        page_mapping[current_page]()
    else:
        st.error("ページが見つかりません")
        switch_page("タイムライン")
