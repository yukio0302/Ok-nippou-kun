import os
import time
import streamlit as st
import pandas as pd
import base64
from datetime import datetime, timedelta
import json
import logging  # ログ記録用
from collections import defaultdict

# ログ設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# ヘルパー関数: 現在時刻に9時間を加算する
def get_current_time():
    return datetime.now() + timedelta(hours=9)  # JSTで現在時刻を取得

# データベース操作ユーティリティをインポート
from db_utils import (
    init_db, authenticate_user, save_report, load_reports,
    load_notices, mark_notice_as_read, edit_report, delete_report,
    update_reaction, save_comment, load_commented_reports,
    save_weekly_schedule, save_weekly_schedule_comment, 
    add_comments_column, load_weekly_schedules
)

# excel_utils.py をインポート
import excel_utils  # この行を追加

# 絶対パスでCSSファイルを読み込む関数
def load_css(file_name):
    with open(file_name) as f:  # 絶対パスをそのまま使用
        st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

# 絶対パスでCSSファイルを読み込む
css_file_path = "style.css"  # 絶対パスを設定
load_css(css_file_path)

# ✅ PostgreSQL 初期化（データを消さない）
init_db(keep_existing=True)

# コメントカラムの存在確認
add_comments_column()

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
        try:
            st.image("OK-Nippou5.png", use_container_width=True)
        except:
            st.title("日報システム")  # 画像がない場合はタイトルを表示

        # ユーザー名と役割を表示
        user = st.session_state["user"]
        if user.get("admin", False):
            st.caption(f"**{user['name']}** さん（管理者）")
        else:
            st.caption(f"**{user['name']}** さん")
        
        st.caption(f"所属: {', '.join(user['depart'])}")

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

        # 通常のナビゲーションボタン（全ユーザー向け）
        st.markdown("### メニュー")
        
        # 通知の未読数を取得
        from db_utils import get_user_notifications
        unread_notifications = get_user_notifications(st.session_state["user"]["name"], unread_only=True)
        unread_count = len(unread_notifications)
        notification_badge = f"🔔 通知 ({unread_count})" if unread_count > 0 else "🔔 通知"
        
        if st.button("⏳ タイムライン", key="sidebar_timeline"):
            switch_page("タイムライン")

        if st.button(" 週間予定", key="sidebar_weekly"):
            switch_page("週間予定")

        if st.button(" お知らせ", key="sidebar_notice"):
            switch_page("お知らせ")
            
        if st.button(notification_badge, key="sidebar_notifications"):
            st.session_state["page"] = "通知"
            st.rerun()

        if st.button("✈️ 週間予定投稿", key="sidebar_post_schedule"):
            switch_page("週間予定投稿")

        if st.button(" 日報作成", key="sidebar_post_report"):
            switch_page("日報投稿")

        if st.button(" マイページ", key="sidebar_mypage"):
            switch_page("マイページ")
            
        # 管理者向け機能
        if user.get("admin", False):
            st.markdown("### 管理者メニュー")
            if st.button(" お知らせ投稿", key="sidebar_post_notice"):
                switch_page("お知らせ投稿")
            
            if st.button(" データエクスポート", key="sidebar_export"):
                switch_page("データエクスポート")

# ✅ ログイン機能（修正済み）
def login():
    # ロゴ表示（中央揃え）
    col1, col2, col3 = st.columns([1, 3, 1])
    with col2:
        try:
            st.image("OK-Nippou4.png", use_container_width=True)  # 画像をコンテナ幅に合わせる
        except:
            st.title("日報システム")  # 画像がない場合はタイトルを表示

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

def post_weekly_schedule():
    if "user" not in st.session_state or st.session_state["user"] is None:
        st.error("ログインしてください。")
        return

    st.title("週間予定投稿")
    # top_navigation()

    # 週選択用のヘルパー関数
    def generate_week_options():
        """選択可能な週のリストを生成（過去4週～未来4週）"""
        today = datetime.today().date()
        options = []
        for i in range(-4, 5):
            start = today - timedelta(days=today.weekday()) + timedelta(weeks=i)
            end = start + timedelta(days=6)
            week_label = f"{start.month}/{start.day}（月）～{end.month}/{end.day}（日）"
            options.append((start, end, week_label))
        return options

    # 週選択UI
    week_options = generate_week_options()
    selected_week = st.selectbox(
        "該当週を選択",
        options=week_options,
        format_func=lambda x: x[2],
        index=4
    )
    start_date, end_date, _ = selected_week

    # 各日の予定入力
    weekly_plan = {}
    for i in range(7):
        current_date = start_date + timedelta(days=i)
        weekday_jp = ["月", "火", "水", "木", "金", "土", "日"][current_date.weekday()]
        date_label = f"{current_date.month}月{current_date.day}日（{weekday_jp}）"

        weekly_plan[current_date.strftime("%Y-%m-%d")] = st.text_input(
            f"{date_label} の予定",
            key=f"plan_{current_date}"
        )

    if st.button("投稿する"):
        schedule = {
            "投稿者": st.session_state["user"]["name"],
            "開始日": start_date.strftime("%Y-%m-%d"),
            "終了日": end_date.strftime("%Y-%m-%d"),
            "月曜日": weekly_plan[(start_date + timedelta(days=0)).strftime("%Y-%m-%d")],
            "火曜日": weekly_plan[(start_date + timedelta(days=1)).strftime("%Y-%m-%d")],
            "水曜日": weekly_plan[(start_date + timedelta(days=2)).strftime("%Y-%m-%d")],
            "木曜日": weekly_plan[(start_date + timedelta(days=3)).strftime("%Y-%m-%d")],
            "金曜日": weekly_plan[(start_date + timedelta(days=4)).strftime("%Y-%m-%d")],
            "土曜日": weekly_plan[(start_date + timedelta(days=5)).strftime("%Y-%m-%d")],
            "日曜日": weekly_plan[(start_date + timedelta(days=6)).strftime("%Y-%m-%d")]
        }

        save_weekly_schedule(schedule)
        st.success("✅ 週間予定を投稿しました！")
        time.sleep(1)
        switch_page("タイムライン")

def show_weekly_schedules():
    if "user" not in st.session_state or st.session_state["user"] is None:
        st.error("ログインしてください。")
        return

    st.title("週間予定一覧")
    # top_navigation()

    # 週間予定データ取得
    schedules = load_weekly_schedules()

    if not schedules:
        st.info("週間予定はまだありません。")
        return

    # 週間予定を表示（最新のものから）
    for i, schedule in enumerate(schedules):
        # 週間予定用のユニークキー
        schedule_key = f"weekly_schedule_{i}"
        
        with st.expander(f"【{schedule['投稿者']}】 {schedule['開始日']} 〜 {schedule['終了日']}", expanded=True):
            # 週間予定テーブル表示
            data = {
                "項目": ["予定"],
                "月曜日": [schedule["月曜日"]],
                "火曜日": [schedule["火曜日"]],
                "水曜日": [schedule["水曜日"]],
                "木曜日": [schedule["木曜日"]],
                "金曜日": [schedule["金曜日"]],
                "土曜日": [schedule["土曜日"]],
                "日曜日": [schedule["日曜日"]]
            }
            df = pd.DataFrame(data)
            df = df.set_index("項目")  # 項目列をインデックスに設定
            st.table(df)  # テーブル表示

            st.caption(f"投稿者: {schedule['投稿者']} / 投稿日時: {schedule['投稿日時']}")

            # コメント表示
            if schedule["コメント"]:
                st.markdown("#### コメント")
                for comment in schedule["コメント"]:
                    st.markdown(f"""
                    **{comment['投稿者']}** - {comment['投稿日時']}  
                    {comment['内容']}
                    ---
                    """)

            # コメント入力フォーム
            with st.form(key=f"{schedule_key}_schedule_comment_{schedule['id']}"):
                comment_text = st.text_area("コメントを入力", key=f"{schedule_key}_comment_text_{schedule['id']}")
                submit_button = st.form_submit_button("コメントする")

                if submit_button and comment_text.strip():
                    comment = {
                        "投稿者": st.session_state["user"]["name"],
                        "内容": comment_text,
                    }
                    if save_weekly_schedule_comment(schedule["id"], comment):
                        st.success("コメントを投稿しました！")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error("コメントの投稿に失敗しました。")

def timeline():
    if "user" not in st.session_state or st.session_state["user"] is None:
        st.error("ログインしてください。")
        return

    st.title("タイムライン")
    # top_navigation()

    # ログインユーザーの所属部署
    user_depart = st.session_state["user"]["depart"][0] if st.session_state["user"]["depart"] else None

    # 表示件数設定
    display_count = st.slider("表示件数", min_value=5, max_value=50, value=10, step=5)

    # タブ（すべて/所属部署のみ）
    tab1, tab2 = st.tabs(["すべての日報", f"{user_depart}の日報"])

    with tab1:
        reports = load_reports(limit=display_count)
        display_reports(reports)

    with tab2:
        if user_depart:
            depart_reports = load_reports(depart=user_depart, limit=display_count)
            display_reports(depart_reports)
        else:
            st.info("部署が設定されていません。")

def display_reports(reports):
    """日報表示関数"""
    if not reports:
        st.info("表示する日報はありません。")
        return

    for i, report in enumerate(reports):
        # ユニークなインデックスを生成（現在のページとレポートのIDとインデックスを組み合わせる）
        unique_prefix = f"{st.session_state['page']}_{i}_{report['id']}"
        
        with st.expander(f"【{report['投稿者']}】 {report['日付']} の日報 - {report['所属部署']}", expanded=True):
            # 項目ごとにテーブル形式で表示
            data = {
                "項目": ["業務内容", "メンバー状況", "作業時間", "翌日予定", "相談事項"],
                "内容": [
                    report["業務内容"], report["メンバー状況"], report["作業時間"],
                    report["翌日予定"], report["相談事項"]
                ]
            }
            df = pd.DataFrame(data)
            st.table(df)

            st.caption(f"投稿者: {report['投稿者']} ({report['所属部署']}) / 投稿日時: {report['投稿日時']}")

            # 編集・削除ボタン（投稿者のみ表示）
            if st.session_state["user"]["name"] == report["投稿者"]:
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("編集", key=f"{unique_prefix}_edit_{report['id']}"):
                        st.session_state["edit_report"] = report
                        switch_page("日報編集")
                with col2:
                    if st.button("削除", key=f"{unique_prefix}_delete_{report['id']}"):
                        if delete_report(report["id"]):
                            st.success("日報を削除しました！")
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.error("削除に失敗しました。")

            # リアクションボタン
            reaction_col1, reaction_col2, reaction_col3, reaction_col4 = st.columns(4)
            reaction_types = {"👍": "thumbs_up", "👏": "clap", "😊": "smile", "🎉": "party"}

            for j, (emoji, reaction_type) in enumerate(reaction_types.items()):
                col = [reaction_col1, reaction_col2, reaction_col3, reaction_col4][j]
                with col:
                    # リアクション数とユーザー名を表示
                    reaction_users = report.get("reactions", {}).get(reaction_type, [])
                    count = len(reaction_users)
                    button_label = f"{emoji} {count}" if count > 0 else emoji

                    # 自分がリアクション済みかチェック
                    user_reacted = st.session_state["user"]["name"] in reaction_users
                    button_key = f"{unique_prefix}_{reaction_type}_{report['id']}"

                    # ボタン表示と処理
                    if st.button(button_label, key=button_key, help=", ".join(reaction_users) if reaction_users else None):
                        if update_reaction(report["id"], st.session_state["user"]["name"], reaction_type):
                            st.rerun()

            # コメント表示
            if report.get("comments"):
                st.markdown("#### コメント")
                for comment in report["comments"]:
                    st.markdown(f"""
                    **{comment['投稿者']}** - {comment['投稿日時']}  
                    {comment['内容']}
                    ---
                    """)

            # コメント入力フォーム
            with st.form(key=f"{unique_prefix}_comment_{report['id']}"):
                comment_text = st.text_area("コメントを入力", key=f"{unique_prefix}_comment_text_{report['id']}")
                submit_button = st.form_submit_button("コメントする")

                if submit_button and comment_text.strip():
                    comment = {
                        "投稿者": st.session_state["user"]["name"],
                        "内容": comment_text,
                    }
                    if save_comment(report["id"], comment):
                        st.success("コメントを投稿しました！")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error("コメントの投稿に失敗しました。")

def post_report():
    if "user" not in st.session_state or st.session_state["user"] is None:
        st.error("ログインしてください。")
        return

    st.title("日報作成")
    # top_navigation()

    # 所属部署設定
    depart = st.selectbox(
        "所属部署",
        options=st.session_state["user"]["depart"],
        index=0
    )

    # 日付設定（デフォルトは今日の日付）
    today = datetime.now().date()
    date = st.date_input("日付", value=today)

    # 各項目の入力
    業務内容 = st.text_area("業務内容", help="今日行った業務の内容を入力してください")
    メンバー状況 = st.text_area("メンバー状況", help="チームメンバーの状況を入力してください")
    作業時間 = st.text_input("作業時間", help="作業時間を入力してください（例: 9:00-18:00）")
    翌日予定 = st.text_area("翌日予定", help="翌日の予定を入力してください")
    相談事項 = st.text_area("相談事項（任意）", help="相談事項がある場合は入力してください")

    if st.button("日報を投稿"):
        # 必須項目のチェック
        if not 業務内容 or not メンバー状況 or not 作業時間 or not 翌日予定:
            st.error("必須項目を入力してください。")
            return

        # 日報データ作成
        report = {
            "投稿者": st.session_state["user"]["name"],
            "所属部署": depart,
            "日付": date.strftime("%Y-%m-%d"),
            "業務内容": 業務内容,
            "メンバー状況": メンバー状況,
            "作業時間": 作業時間,
            "翌日予定": 翌日予定,
            "相談事項": 相談事項,
        }

        # 日報保存
        if save_report(report):
            st.success("✅ 日報を投稿しました！")
            time.sleep(1)
            switch_page("タイムライン")
        else:
            st.error("❌ 日報の投稿に失敗しました。")

def edit_report_page():
    if "user" not in st.session_state or st.session_state["user"] is None:
        st.error("ログインしてください。")
        return

    if "edit_report" not in st.session_state:
        st.error("編集する日報が選択されていません。")
        return

    report = st.session_state["edit_report"]

    st.title("日報編集")
    # top_navigation()

    # 編集不可の項目表示
    st.subheader(f"{report['日付']} の日報編集")
    st.text(f"投稿者: {report['投稿者']} ({report['所属部署']})")

    # 編集可能な項目
    業務内容 = st.text_area("業務内容", value=report["業務内容"])
    メンバー状況 = st.text_area("メンバー状況", value=report["メンバー状況"])
    作業時間 = st.text_input("作業時間", value=report["作業時間"])
    翌日予定 = st.text_area("翌日予定", value=report["翌日予定"])
    相談事項 = st.text_area("相談事項", value=report["相談事項"])

    if st.button("更新する"):
        # 必須項目のチェック
        if not 業務内容 or not メンバー状況 or not 作業時間 or not 翌日予定:
            st.error("必須項目を入力してください。")
            return

        # 日報データ更新
        updated_report = {
            "業務内容": 業務内容,
            "メンバー状況": メンバー状況,
            "作業時間": 作業時間,
            "翌日予定": 翌日予定,
            "相談事項": 相談事項,
        }

        if edit_report(report["id"], updated_report):
            st.success("✅ 日報を更新しました！")
            # 編集状態をクリア
            del st.session_state["edit_report"]
            time.sleep(1)
            switch_page("タイムライン")
        else:
            st.error("❌ 日報の更新に失敗しました。")

def show_notices():
    if "user" not in st.session_state or st.session_state["user"] is None:
        st.error("ログインしてください。")
        return

    st.title("お知らせ")
    # top_navigation()

    # ユーザーの所属部署
    user_depart = st.session_state["user"]["depart"][0] if st.session_state["user"]["depart"] else None

    # お知らせデータ取得（ユーザーの部署向けのみ）
    notices = load_notices(depart=user_depart)

    if not notices:
        st.info("表示するお知らせはありません。")
        return

    # お知らせを表示
    for i, notice in enumerate(notices):
        # お知らせ用のユニークキー
        notice_key = f"notice_{i}"
        
        # 既読チェック
        is_read = st.session_state["user"]["name"] in notice.get("既読者", [])
        
        # タイトルの前に未読マークを表示
        title_prefix = "" if is_read else "🔴 "
        
        with st.expander(f"{title_prefix}{notice['タイトル']} ({notice['対象部署']})", expanded=not is_read):
            st.markdown(f"**内容:** {notice['内容']}")
            st.caption(f"投稿者: {notice['投稿者']} / 投稿日時: {notice['投稿日時']}")
            
            # 未読の場合は既読ボタン表示
            if not is_read:
                if st.button("既読にする", key=f"{notice_key}_read_{notice['id']}"):
                    if mark_notice_as_read(notice["id"], st.session_state["user"]["name"]):
                        st.success("既読にしました！")
                        time.sleep(1)
                        st.rerun()

def post_notice():
    if "user" not in st.session_state or st.session_state["user"] is None:
        st.error("ログインしてください。")
        return
        
    # 管理者権限をチェック
    if not st.session_state["user"].get("admin", False):
        st.error("このページは管理者のみアクセスできます。")
        return

    st.title("お知らせ投稿")
    # top_navigation()

    # デフォルトでユーザーの所属部署を選択
    user_depart = st.session_state["user"]["depart"][0] if st.session_state["user"]["depart"] else "すべて"
    
    # 入力フォーム
    タイトル = st.text_input("タイトル", help="お知らせのタイトルを入力してください")
    内容 = st.text_area("内容", help="お知らせの内容を入力してください")
    
    # 部署リスト - 新しい部署を含む
    department_options = ["すべて", "業務部", "営業部", "企画部", "国際流通", "総務部", "情報統括", "マーケティング室"] 
    対象部署 = st.selectbox(
        "対象部署",
        options=department_options,
        index=0 if user_depart == "すべて" else (department_options.index(user_depart) if user_depart in department_options else 0)
    )

    if st.button("投稿する"):
        if not タイトル or not 内容:
            st.error("タイトルと内容は必須です。")
            return
            
        notice = {
            "投稿者": st.session_state["user"]["name"],
            "タイトル": タイトル,
            "内容": 内容,
            "対象部署": 対象部署,
        }
        
        # お知らせ保存
        from db_utils import save_notice
        if save_notice(notice):
            st.success("✅ お知らせを投稿しました！")
            time.sleep(1)
            switch_page("お知らせ")
        else:
            st.error("❌ お知らせの投稿に失敗しました。")

def show_mypage():
    if "user" not in st.session_state or st.session_state["user"] is None:
        st.error("ログインしてください。")
        return

    st.title("マイページ")
    # top_navigation()

    # ユーザー情報表示
    user = st.session_state["user"]
    st.subheader(f"{user['name']} さんのマイページ")
    st.write(f"社員コード: {user['code']}")
    st.write(f"所属部署: {', '.join(user['depart'])}")

    # タブで切り替え（自分の日報/コメントした日報）
    tab1, tab2 = st.tabs(["自分の日報", "コメントした日報"])

    with tab1:
        # 自分の投稿した日報を表示
        my_reports = load_reports(limit=None)
        my_reports = [r for r in my_reports if r["投稿者"] == user["name"]]
        
        if not my_reports:
            st.info("投稿した日報はありません。")
        else:
            for i, report in enumerate(my_reports):
                # マイページ用のユニークキー
                mp_key = f"mypage_report_{i}"
                
                with st.expander(f"{report['日付']} の日報 - {report['所属部署']}", expanded=False):
                    # 項目ごとにテーブル形式で表示
                    data = {
                        "項目": ["業務内容", "メンバー状況", "作業時間", "翌日予定", "相談事項"],
                        "内容": [
                            report["業務内容"], report["メンバー状況"], report["作業時間"],
                            report["翌日予定"], report["相談事項"]
                        ]
                    }
                    df = pd.DataFrame(data)
                    st.table(df)
                    st.caption(f"投稿日時: {report['投稿日時']}")
                    
                    # 編集・削除ボタン
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("編集", key=f"{mp_key}_edit_{report['id']}"):
                            st.session_state["edit_report"] = report
                            switch_page("日報編集")
                    with col2:
                        if st.button("削除", key=f"{mp_key}_delete_{report['id']}"):
                            if delete_report(report["id"]):
                                st.success("日報を削除しました！")
                                time.sleep(1)
                                st.rerun()
                            else:
                                st.error("削除に失敗しました。")

    with tab2:
        # コメントした日報を表示
        commented_reports = load_commented_reports(user["name"])
        
        if not commented_reports:
            st.info("コメントした日報はありません。")
        else:
            for i, report in enumerate(commented_reports):
                # コメント済み日報用のユニークキー
                cm_key = f"commented_report_{i}"
                
                with st.expander(f"【{report['投稿者']}】 {report['日付']} の日報 - {report['所属部署']}", expanded=False):
                    # 項目ごとにテーブル形式で表示
                    data = {
                        "項目": ["業務内容", "メンバー状況", "作業時間", "翌日予定", "相談事項"],
                        "内容": [
                            report["業務内容"], report["メンバー状況"], report["作業時間"],
                            report["翌日予定"], report["相談事項"]
                        ]
                    }
                    df = pd.DataFrame(data)
                    st.table(df)
                    
                    st.caption(f"投稿者: {report['投稿者']} ({report['所属部署']}) / 投稿日時: {report['投稿日時']}")
                    
                    # 自分のコメントを強調表示
                    st.markdown("#### コメント")
                    for j, comment in enumerate(report["comments"]):
                        is_my_comment = comment["投稿者"] == user["name"]
                        comment_style = "background-color: #f0f7ff; padding: 10px; border-radius: 5px;" if is_my_comment else ""
                        
                        st.markdown(f"""
                        <div style="{comment_style}">
                        <strong>{comment['投稿者']}</strong> - {comment['投稿日時']}<br>
                        {comment['内容']}
                        </div>
                        <hr>
                        """, unsafe_allow_html=True)

    # お知らせ投稿へのリンク (管理者のみ表示)
    if st.session_state["user"].get("admin", False):
        st.markdown("---")
        st.markdown("### 管理者機能")
        if st.button("お知らせを投稿"):
            switch_page("お知らせ投稿")

def logout():
    st.session_state["user"] = None
    st.session_state["page"] = "ログイン"
    st.rerun()

# メイン処理
def export_data_page():
    """管理者向けデータエクスポートページ"""
    if "user" not in st.session_state or st.session_state["user"] is None:
        st.error("ログインしてください。")
        return
        
    # 管理者権限をチェック
    if not st.session_state["user"].get("admin", False):
        st.error("このページは管理者のみアクセスできます。")
        return
    
    st.title("データエクスポート")
    
    # 日報データエクスポート
    st.header("日報データエクスポート")
    col1, col2 = st.columns(2)
    
    with col1:
        # フィルター設定
        st.subheader("フィルター設定")
        target_depart = st.selectbox(
            "部署で絞り込み", 
            options=["すべて", "業務部", "営業部", "企画部", "国際流通", "総務部", "情報統括", "マーケティング室"],
            index=0
        )
        
        # 日付範囲
        date_range = st.date_input(
            "日付範囲",
            value=[datetime.now().date() - timedelta(days=30), datetime.now().date()],
            key="date_range_reports",
            help="エクスポートする日報の日付範囲を指定",
        )
        
    with col2:
        st.subheader("エクスポート設定")
        # エクスポートボタン
        depart_filter = None if target_depart == "すべて" else target_depart
        if st.button("日報データをエクスポート"):
            reports = load_reports(depart=depart_filter)
            
            # 日付フィルター適用
            if len(date_range) == 2:
                start_date, end_date = date_range
                filtered_reports = [r for r in reports if start_date <= datetime.strptime(r["日付"], "%Y-%m-%d").date() <= end_date]
            else:
                filtered_reports = reports
                
            if filtered_reports:
                from excel_utils import export_to_excel
                filename = export_to_excel(filtered_reports, "日報データ.xlsx")
                
                with open(filename, "rb") as file:
                    st.download_button(
                        label="ダウンロード",
                        data=file,
                        file_name="日報データ.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
                os.remove(filename)  # 一時ファイル削除
            else:
                st.warning("条件に一致する日報はありません。")
    
    # 週間予定データエクスポート
    st.markdown("---")
    st.header("週間予定データエクスポート")
    
    if st.button("週間予定データをエクスポート"):
        schedules = load_weekly_schedules()
        if schedules:
            from excel_utils import export_weekly_schedules_to_excel
            filename = export_weekly_schedules_to_excel(schedules, "週間予定データ.xlsx")
            
            with open(filename, "rb") as file:
                st.download_button(
                    label="ダウンロード",
                    data=file,
                    file_name="週間予定データ.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            os.remove(filename)  # 一時ファイル削除
        else:
            st.warning("週間予定データがありません。")

def show_notifications():
    """通知一覧を表示するページ"""
    if "user" not in st.session_state or st.session_state["user"] is None:
        st.error("ログインしてください。")
        return
    
    from db_utils import get_user_notifications, mark_notification_as_read, mark_all_notifications_as_read
    from db_utils import load_report_by_id
    
    st.title("通知一覧")
    
    # 通知データを取得
    notifications = get_user_notifications(st.session_state["user"]["name"])
    
    if not notifications:
        st.info("通知はありません。")
        return
    
    # 全て既読にするボタン
    col1, col2 = st.columns([3, 1])
    with col2:
        if st.button("すべて既読にする"):
            if mark_all_notifications_as_read(st.session_state["user"]["name"]):
                st.success("すべての通知を既読にしました！")
                time.sleep(1)
                st.rerun()
    
    # 通知を表示
    for i, notification in enumerate(notifications):
        notification_key = f"notification_{i}"
        
        # 未読のものは強調表示
        is_unread = not notification["is_read"]
        prefix = "🔴 " if is_unread else ""
        
        with st.expander(f"{prefix}{notification['content']}", expanded=is_unread):
            st.caption(f"通知日時: {notification['created_at']}")
            
            # リンク先情報によって適切なボタンを表示
            if notification["link_type"] == "report":
                report_id = notification["link_id"]
                report = load_report_by_id(report_id)
                
                if report:
                    st.markdown(f"**日報情報:**")
                    st.markdown(f"投稿日: {report['日付']}")
                    st.markdown(f"投稿者: {report['投稿者']}")
                    
                    if st.button("日報を表示", key=f"{notification_key}_view_report_{report_id}"):
                        # 通知を既読にして日報ページへ移動
                        if is_unread:
                            mark_notification_as_read(notification["id"])
                        
                        # URLパラメータとして日報IDを渡して表示
                        st.session_state["view_report_id"] = report_id
                        switch_page("タイムライン")
                else:
                    st.warning("この日報は削除されています。")
            
            elif notification["link_type"] == "weekly_schedule":
                schedule_id = notification["link_id"]
                if st.button("週間予定を表示", key=f"{notification_key}_view_schedule_{schedule_id}"):
                    # 通知を既読にして週間予定ページへ移動
                    if is_unread:
                        mark_notification_as_read(notification["id"])
                    switch_page("週間予定")
            
            # 既読ボタン
            if is_unread:
                if st.button("既読にする", key=f"{notification_key}_mark_read_{notification['id']}"):
                    if mark_notification_as_read(notification["id"]):
                        st.success("既読にしました！")
                        time.sleep(1)
                        st.rerun()

def main():
    # サイドバー表示（ログイン後のみ）
    if st.session_state["user"]:
        sidebar_navigation()
        # ログアウトボタン
        with st.sidebar:
            st.markdown("---")
            if st.button("ログアウト"):
                logout()

    # 現在のページに応じた内容表示
    if st.session_state["page"] == "ログイン":
        login()
    elif st.session_state["page"] == "タイムライン":
        timeline()
    elif st.session_state["page"] == "日報投稿":
        post_report()
    elif st.session_state["page"] == "日報編集":
        edit_report_page()
    elif st.session_state["page"] == "週間予定":
        show_weekly_schedules()
    elif st.session_state["page"] == "週間予定投稿":
        post_weekly_schedule()
    elif st.session_state["page"] == "お知らせ":
        show_notices()
    elif st.session_state["page"] == "お知らせ投稿":
        post_notice()
    elif st.session_state["page"] == "マイページ":
        show_mypage()
    elif st.session_state["page"] == "データエクスポート":
        export_data_page()
    elif st.session_state["page"] == "通知":
        show_notifications()
    else:
        st.error(f"不明なページ: {st.session_state['page']}")

if __name__ == "__main__":
    main()
