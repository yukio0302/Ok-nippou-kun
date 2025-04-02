import os
import time
import streamlit as st
import pandas as pd
import base64
from io import BytesIO
from datetime import datetime, timedelta, date
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
    add_comments_column, load_weekly_schedules, get_user_stores,
    get_user_store_visits, get_store_visit_stats, save_stores_data,
    search_stores, load_report_by_id, save_notice, load_reports_by_date,
    save_report_image, get_report_images, delete_report_image
)

# excel_utils.py をインポート
import excel_utils

# 絶対パスでCSSファイルを読み込む関数
def load_css(file_name):
    with open(file_name) as f:  # 絶対パスをそのまま使用
        st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

# 絶対パスでCSSファイルを読み込む
css_file_path = "style.css"  # 絶対パスを設定
try:
    load_css(css_file_path)
except:
    pass  # スタイルファイルがない場合はスキップ

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
                
            if st.button(" 店舗データアップロード", key="sidebar_upload_stores"):
                switch_page("店舗データアップロード")

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

    # ユーザーの担当店舗を取得
    user_stores = get_user_stores(st.session_state["user"]["code"])
    
    # 週間予定入力用の辞書
    weekly_plan = {}
    weekly_visited_stores = {}
    
    # 各曜日の予定と店舗選択
    weekdays = ["月曜日", "火曜日", "水曜日", "木曜日", "金曜日", "土曜日", "日曜日"]
    
    for i, weekday in enumerate(weekdays):
        current_date = start_date + timedelta(days=i)
        date_label = f"{current_date.month}月{current_date.day}日（{weekday}）"
        
        st.markdown(f"### {date_label}")
        
        # 担当店舗マルチセレクト
        store_options = [f"{store['code']}: {store['name']}" for store in user_stores]
        selected_stores = st.multiselect(
            f"{date_label}の訪問店舗",
            options=store_options,
            key=f"stores_{weekday}"
        )
        
        # 選択した店舗情報を保存
        stores_data = []
        store_text = ""
        for selected in selected_stores:
            code, name = selected.split(": ", 1)
            stores_data.append({"code": code, "name": name})
            store_text += f"【{name}】"
        
        weekly_visited_stores[f"{weekday}_visited_stores"] = stores_data
        
        # 予定入力欄（選択した店舗情報も表示）
        weekly_plan[weekday] = st.text_area(
            f"{date_label} の予定",
            value=store_text,
            key=f"plan_{weekday}"
        )

    if st.button("投稿する"):
        schedule = {
            "投稿者": st.session_state["user"]["name"],
            "user_code": st.session_state["user"]["code"],
            "開始日": start_date.strftime("%Y-%m-%d"),
            "終了日": end_date.strftime("%Y-%m-%d"),
            "月曜日": weekly_plan["月曜日"],
            "火曜日": weekly_plan["火曜日"],
            "水曜日": weekly_plan["水曜日"],
            "木曜日": weekly_plan["木曜日"],
            "金曜日": weekly_plan["金曜日"],
            "土曜日": weekly_plan["土曜日"],
            "日曜日": weekly_plan["日曜日"]
        }
        
        # 訪問店舗情報を追加
        for key, stores in weekly_visited_stores.items():
            schedule[key] = stores

        save_weekly_schedule(schedule)
        st.success("✅ 週間予定を投稿しました！")
        time.sleep(1)
        switch_page("タイムライン")
        st.rerun()

def show_weekly_schedules():
    if "user" not in st.session_state or st.session_state["user"] is None:
        st.error("ログインしてください。")
        return

    st.title("週間予定一覧")

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
                "項目": ["予定", "訪問店舗"],
            }
            
            # 各曜日のデータとその訪問店舗
            weekdays = ["月曜日", "火曜日", "水曜日", "木曜日", "金曜日", "土曜日", "日曜日"]
            for day in weekdays:
                data[day] = [schedule[day]]
                
                # 訪問店舗情報
                visited_stores_key = f"{day}_visited_stores"
                visited_stores = schedule.get(visited_stores_key, [])
                store_names = [store["name"] for store in visited_stores] if visited_stores else []
                data[day].append(", ".join(store_names))
            
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

    # ログインユーザーの所属部署
    user_depart = st.session_state["user"]["depart"][0] if st.session_state["user"]["depart"] else None

    # 時間範囲選択（新機能）
    time_range = st.radio(
        "表示期間",
        ["24時間以内", "1週間以内", "すべて表示"],
        horizontal=True,
        index=1
    )
    
    # 選択された時間範囲を変換
    time_range_param = None
    if time_range == "24時間以内":
        time_range_param = "24h"
    elif time_range == "1週間以内":
        time_range_param = "1w"
    # "すべて表示"の場合はNoneのまま

    # タブ（すべて/所属部署のみ）
    tab1, tab2 = st.tabs(["すべての日報", f"{user_depart}の日報"])

    with tab1:
        reports = load_reports(time_range=time_range_param)
        display_reports(reports)

    with tab2:
        if user_depart:
            depart_reports = load_reports(depart=user_depart, time_range=time_range_param)
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
        
        # 日報日付から曜日を取得
        try:
            report_date = datetime.strptime(report["日付"], "%Y-%m-%d")
            weekday = ["月", "火", "水", "木", "金", "土", "日"][report_date.weekday()]
            formatted_date = f"{report_date.month}月{report_date.day}日（{weekday}）"
        except:
            formatted_date = report["日付"]

        # 日報表示カード
        with st.expander(f"【{report['投稿者']}】 {formatted_date} ({report['所属部署']})", expanded=True):
            # 訪問店舗情報
            visited_stores = report.get("visited_stores", [])
            if visited_stores:
                store_names = [store["name"] for store in visited_stores]
                st.markdown(f"**訪問店舗**: {', '.join(store_names)}")
            
            # 実施内容（すべて統合表示）
            content = ""
            if "実施内容" in report and report["実施内容"]:
                content = report["実施内容"]
            elif "業務内容" in report and report["業務内容"]:
                content = report["業務内容"]
                
            # 所感データがあれば追加
            if "所感" in report and report["所感"]:
                if content:
                    content += "\n\n" + report["所感"]
                else:
                    content = report["所感"]
            elif "メンバー状況" in report and report["メンバー状況"]:
                if content:
                    content += "\n\n" + report["メンバー状況"]
                else:
                    content = report["メンバー状況"]
            
            if content:
                st.markdown("#### 実施内容、所感など")
                st.markdown(content.replace("\n", "  \n"))
            
            # 今後のアクション（旧：翌日予定）
            if "今後のアクション" in report and report["今後のアクション"]:
                st.markdown("#### 今後のアクション")
                st.markdown(report["今後のアクション"].replace("\n", "  \n"))
            elif "翌日予定" in report and report["翌日予定"]:
                st.markdown("#### 今後のアクション")
                st.markdown(report["翌日予定"].replace("\n", "  \n"))
            
            # 画像の表示
            report_images = get_report_images(report['id'])
            if report_images:
                st.markdown("#### 添付画像")
                for i, img in enumerate(report_images):
                    st.markdown(f"**{img['file_name']}**")
                    st.markdown(f"<img src='data:{img['file_type']};base64,{img['image_data']}' style='max-width:100%;'>", unsafe_allow_html=True)
            
            st.caption(f"投稿日時: {report['投稿日時']}")
            
            # リアクションボタンバー
            col1, col2, col3, col4 = st.columns(4)
            
            reaction_types = {
                "👍": "thumbsup",
                "👏": "clap",
                "😊": "smile",
                "🎉": "tada"
            }
            
            # 各リアクションボタンを作成
            for i, (emoji, key) in enumerate(reaction_types.items()):
                col = [col1, col2, col3, col4][i]
                with col:
                    # リアクションの数を取得
                    reaction_count = len(report['reactions'].get(key, []))
                    
                    # ユーザーがすでにリアクションしているか確認
                    is_reacted = st.session_state["user"]["name"] in report['reactions'].get(key, [])
                    button_label = f"{emoji} {reaction_count}" if reaction_count else emoji
                    
                    # ボタンスタイルの設定
                    button_style = "primary" if is_reacted else "secondary"
                    
                    # リアクションボタン
                    if st.button(button_label, key=f"{unique_prefix}_reaction_{key}", type=button_style):
                        if update_reaction(report['id'], st.session_state["user"]["name"], key):
                            st.rerun()

            # コメント表示
            if report["comments"]:
                st.markdown("#### コメント")
                for comment in report["comments"]:
                    st.markdown(f"""
                    **{comment['投稿者']}** - {comment['投稿日時']}  
                    {comment['内容']}
                    ---
                    """)
            
            # コメント入力フォーム
            with st.form(key=f"{unique_prefix}_comment_form"):
                comment_text = st.text_area("コメントを入力", key=f"{unique_prefix}_comment_text")
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

            # 自分の投稿であれば編集・削除ボタンを表示
            if report["投稿者"] == st.session_state["user"]["name"] or st.session_state["user"].get("admin", False):
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("編集", key=f"{unique_prefix}_edit"):
                        st.session_state["edit_report_id"] = report["id"]
                        switch_page("日報編集")
                        st.rerun()
                with col2:
                    if st.button("削除", key=f"{unique_prefix}_delete"):
                        if delete_report(report["id"]):
                            st.success("日報を削除しました！")
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.error("日報の削除に失敗しました。")

def post_report():
    if "user" not in st.session_state or st.session_state["user"] is None:
        st.error("ログインしてください。")
        return

    st.title("日報投稿")

    # 投稿フォーム
    with st.form("report_form"):
        st.markdown("### 基本情報")
        # 自動入力情報
        col1, col2 = st.columns(2)
        with col1:
            post_date = st.date_input("日付", value=datetime.now().date())
        with col2:
            department = st.session_state["user"]["depart"][0] if st.session_state["user"]["depart"] else ""
            # 所属部署を選択可能にする
            if len(st.session_state["user"]["depart"]) > 1:
                department = st.selectbox("所属部署", st.session_state["user"]["depart"])
            else:
                st.text_input("所属部署", value=department, disabled=True)

        # 場所入力・選択方法のタブ
        location_tabs = st.tabs(["担当店舗から選択", "店舗を検索", "自由入力"])
        
        with location_tabs[0]:
            # ユーザーの担当店舗を取得
            user_stores = get_user_stores(st.session_state["user"]["code"])
            
            # 担当店舗マルチセレクト
            store_options = [f"{store['code']}: {store['name']}" for store in user_stores]
            selected_assigned_stores = st.multiselect(
                "担当店舗から選択",
                options=store_options,
                key="assigned_stores"
            )
        
        with location_tabs[1]:
            # 店舗検索機能
            search_term = st.text_input("店舗名または住所で検索", key="store_search")
            
            # 検索結果表示
            search_results = []
            if search_term:
                search_results = search_stores(search_term)
                
            search_store_options = [f"{store['code']}: {store['name']}" for store in search_results]
            selected_searched_stores = st.multiselect(
                "検索結果から選択",
                options=search_store_options,
                key="searched_stores"
            )
            
        with location_tabs[2]:
            # 自由入力（見込み客など）
            custom_locations = st.text_area(
                "場所を自由に入力（複数の場合は改行で区切る）",
                key="custom_locations",
                placeholder="例: 〇〇商事（見込み客）\n社内会議\n△△市役所..."
            )
        
        # 選択した店舗情報を保存
        stores_data = []
        
        # 担当店舗から選択
        for selected in selected_assigned_stores:
            code, name = selected.split(": ", 1)
            stores_data.append({"code": code, "name": name})
            
        # 検索結果から選択
        for selected in selected_searched_stores:
            code, name = selected.split(": ", 1)
            stores_data.append({"code": code, "name": name})
            
        # 自由入力から追加
        if custom_locations:
            custom_locations_list = custom_locations.strip().split("\n")
            for location in custom_locations_list:
                if location.strip():
                    stores_data.append({"code": "", "name": location.strip()})
        
        st.markdown("### 日報内容")
        business_content = st.text_area("実施内容、所感など", height=200)
        next_day_plan = st.text_area("今後のアクション", height=150)
        
        # 画像アップロード機能
        st.markdown("### 画像添付（任意）")
        uploaded_files = st.file_uploader("画像をアップロード", type=["jpg", "jpeg", "png"], accept_multiple_files=True)
        
        # 投稿ボタン
        submitted = st.form_submit_button("投稿する")
        
        if submitted:
            # 日報データ作成
            report = {
                "投稿者": st.session_state["user"]["name"],
                "user_code": st.session_state["user"]["code"],
                "所属部署": department,
                "日付": post_date.strftime("%Y-%m-%d"),
                "実施内容": business_content,  # 実施内容と所感を統合
                "所感": "",  # 所感フィールドは空にする
                "今後のアクション": next_day_plan,
                "visited_stores": stores_data
            }
            
            # データベースに保存
            report_id = save_report(report)
            
            if report_id:
                # 画像がアップロードされていれば保存
                if uploaded_files:
                    for file in uploaded_files:
                        # 画像ファイルをBase64エンコード
                        file_bytes = file.getvalue()
                        file_type = file.type
                        file_name = file.name
                        encoded_image = base64.b64encode(file_bytes).decode('utf-8')
                        
                        # 画像を日報に関連付けて保存
                        image_id = save_report_image(report_id, file_name, file_type, encoded_image)
                        if not image_id:
                            st.warning(f"画像の保存に失敗しました：{file_name}")
                
                st.success("✅ 日報を投稿しました！")
                time.sleep(1)  # 成功メッセージを表示する時間
                switch_page("タイムライン")
                st.rerun()
            else:
                st.error("日報の投稿に失敗しました。再度お試しください。")

def edit_report_page():
    if "user" not in st.session_state or st.session_state["user"] is None:
        st.error("ログインしてください。")
        return

    if "edit_report_id" not in st.session_state:
        st.error("編集する日報が選択されていません。")
        return

    report_id = st.session_state["edit_report_id"]
    report = load_report_by_id(report_id)

    if not report:
        st.error("日報の読み込みに失敗しました。")
        return

    st.title("日報編集")

    # 編集フォーム
    with st.form("edit_report_form"):
        st.markdown("### 基本情報")
        # 自動入力情報（編集不可）
        col1, col2 = st.columns(2)
        with col1:
            st.text_input("投稿者", value=report["投稿者"], disabled=True)
        with col2:
            st.text_input("所属部署", value=report["所属部署"], disabled=True)
        
        post_date = st.text_input("日付", value=report["日付"], disabled=True)
        
        # ユーザーの担当店舗を取得
        user_stores = get_user_stores(st.session_state["user"]["code"])
        
        # 既存の訪問店舗を取得
        existing_stores = report.get("visited_stores", [])
        existing_store_ids = [f"{store['code']}: {store['name']}" for store in existing_stores]
        
        # 担当店舗マルチセレクト（既存の選択を初期値に）
        store_options = [f"{store['code']}: {store['name']}" for store in user_stores]
        selected_stores = st.multiselect(
            "訪問店舗",
            options=store_options,
            default=existing_store_ids
        )
        
        # 選択した店舗情報を保存
        stores_data = []
        for selected in selected_stores:
            code, name = selected.split(": ", 1)
            stores_data.append({"code": code, "name": name})
        
        st.markdown("### 日報内容")
        # 実施内容と所感を統合して表示する
        combined_content = ""
        if report.get("実施内容") and report.get("所感"):
            combined_content = f"{report.get('実施内容')}\n\n{report.get('所感')}"
        elif report.get("実施内容"):
            combined_content = report.get("実施内容")
        elif report.get("所感"):
            combined_content = report.get("所感")
        elif report.get("業務内容") and report.get("メンバー状況"):
            combined_content = f"{report.get('業務内容')}\n\n{report.get('メンバー状況')}"
        elif report.get("業務内容"):
            combined_content = report.get("業務内容")
        elif report.get("メンバー状況"):
            combined_content = report.get("メンバー状況")
            
        business_content = st.text_area("実施内容、所感など", value=combined_content, height=200)
        next_day_plan = st.text_area("今後のアクション", value=report.get("今後のアクション", report.get("翌日予定", "")), height=150)
        
        # 既存の画像を表示
        report_images = get_report_images(report_id)
        if report_images:
            st.markdown("### 添付済み画像")
            for i, img in enumerate(report_images):
                cols = st.columns([3, 1])
                with cols[0]:
                    st.markdown(f"**{img['file_name']}**")
                    st.markdown(f"<img src='data:{img['file_type']};base64,{img['image_data']}' style='max-width:100%;'>", unsafe_allow_html=True)
                with cols[1]:
                    if st.button("削除", key=f"delete_image_{i}"):
                        if delete_report_image(img['id']):
                            st.success("画像を削除しました。")
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.error("画像の削除に失敗しました。")
        
        # 新規画像アップロード
        st.markdown("### 画像添付（任意）")
        uploaded_files = st.file_uploader("新規画像をアップロード", type=["jpg", "jpeg", "png"], accept_multiple_files=True)
        
        # 更新ボタン
        submitted = st.form_submit_button("更新する")
        
        if submitted:
            # 更新データ作成
            updated_report = {
                "実施内容": business_content,
                "所感": "",  # 所感フィールドは空にする
                "今後のアクション": next_day_plan,
                "visited_stores": stores_data,
                "user_code": st.session_state["user"]["code"]
            }
            
            # データベースを更新
            if edit_report(report_id, updated_report):
                # 新規画像がアップロードされていれば保存
                if uploaded_files:
                    for file in uploaded_files:
                        # 画像ファイルをBase64エンコード
                        file_bytes = file.getvalue()
                        file_type = file.type
                        file_name = file.name
                        encoded_image = base64.b64encode(file_bytes).decode('utf-8')
                        
                        # 画像を日報に関連付けて保存
                        image_id = save_report_image(report_id, file_name, file_type, encoded_image)
                        if not image_id:
                            st.warning(f"画像の保存に失敗しました：{file_name}")
                
                st.success("✅ 日報を更新しました！")
                time.sleep(1)  # 成功メッセージを表示する時間
                # 編集IDをクリア
                st.session_state.pop("edit_report_id", None)
                switch_page("タイムライン")
                st.rerun()
            else:
                st.error("日報の更新に失敗しました。再度お試しください。")

def show_notices():
    if "user" not in st.session_state or st.session_state["user"] is None:
        st.error("ログインしてください。")
        return

    st.title("お知らせ")

    # ログインユーザーの部署名
    user_depart = st.session_state["user"]["depart"][0] if st.session_state["user"]["depart"] else None

    # お知らせ取得
    if user_depart:
        notices = load_notices(department=user_depart)
    else:
        notices = load_notices()

    if not notices:
        st.info("お知らせはありません。")
        return

    # お知らせ表示
    for i, notice in enumerate(notices):
        # 既読状態を確認
        is_read = st.session_state["user"]["name"] in notice["既読者"]
        
        # 背景色を設定（既読/未読）
        card_style = "read-notice" if is_read else "unread-notice"
        
        # ユニークなプレフィックス
        unique_prefix = f"notice_{i}_{notice['id']}"
        
        # お知らせカード
        with st.container():
            st.markdown(f"<div class='{card_style}'>", unsafe_allow_html=True)
            
            # カード内コンテンツ
            st.markdown(f"#### {notice['タイトル']}")
            st.caption(f"投稿者: {notice['投稿者']} - 投稿日時: {notice['投稿日時']} - 対象: {notice['対象部署']}")
            st.markdown(notice["内容"].replace("\n", "  \n"))
            
            # 既読ボタン（未読の場合のみ表示）
            if not is_read:
                if st.button("既読にする", key=f"{unique_prefix}_read_button"):
                    if mark_notice_as_read(notice["id"], st.session_state["user"]["name"]):
                        st.success("既読にしました！")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error("既読の設定に失敗しました。")
            
            st.markdown("</div>", unsafe_allow_html=True)
            st.markdown("<br>", unsafe_allow_html=True)

def post_notice():
    if "user" not in st.session_state or st.session_state["user"] is None:
        st.error("ログインしてください。")
        return

    # 管理者権限チェック
    if not st.session_state["user"].get("admin", False):
        st.error("お知らせの投稿には管理者権限が必要です。")
        return

    st.title("お知らせ投稿")

    # 投稿フォーム
    with st.form("notice_form"):
        # 基本情報
        title = st.text_input("タイトル")
        content = st.text_area("内容", height=200)
        
        # 対象部署選択（全部署 + ユーザーテーブルから取得した部署一覧）
        target_department = st.selectbox(
            "対象部署",
            ["全体", "営業部", "管理部", "技術部", "総務部"]  # 例：実際には動的に取得する
        )
        
        # 投稿ボタン
        submitted = st.form_submit_button("投稿する")
        
        if submitted:
            if not title or not content:
                st.error("タイトルと内容を入力してください。")
                return
                
            # お知らせデータ作成
            notice = {
                "投稿者": st.session_state["user"]["name"],
                "タイトル": title,
                "内容": content,
                "対象部署": target_department,
                "投稿日時": (datetime.now() + timedelta(hours=9)).strftime("%Y-%m-%d %H:%M:%S"),
                "既読者": []
            }
            
            # データベースに保存
            from db_utils import save_notice
            notice_id = save_notice(notice)
            
            if notice_id:
                st.success("お知らせを投稿しました！")
                time.sleep(1)
                switch_page("お知らせ")
                st.rerun()
            else:
                st.error("お知らせの投稿に失敗しました。")

def show_notifications():
    if "user" not in st.session_state or st.session_state["user"] is None:
        st.error("ログインしてください。")
        return

    st.title("通知")

    # 通知を取得
    from db_utils import get_user_notifications, mark_notification_as_read
    notifications = get_user_notifications(st.session_state["user"]["name"])

    if not notifications:
        st.info("通知はありません。")
        return

    # タブ（すべて/未読のみ）
    tab1, tab2 = st.tabs(["すべての通知", "未読の通知"])

    with tab1:
        display_notifications(notifications, mark_notification_as_read)

    with tab2:
        unread_notifications = [n for n in notifications if not n["is_read"]]
        if unread_notifications:
            display_notifications(unread_notifications, mark_notification_as_read)
        else:
            st.info("未読の通知はありません。")

def display_notifications(notifications, mark_as_read_function):
    for i, notification in enumerate(notifications):
        # 通知カードのスタイル
        card_style = "read-notification" if notification["is_read"] else "unread-notification"
        
        # 通知日時の整形
        created_at = notification["created_at"]
        if isinstance(created_at, str):
            try:
                created_at = datetime.strptime(created_at, "%Y-%m-%d %H:%M:%S")
            except:
                pass
        
        if isinstance(created_at, datetime):
            formatted_time = created_at.strftime("%Y-%m-%d %H:%M:%S")
        else:
            formatted_time = str(created_at)
        
        # 通知カード
        with st.container():
            st.markdown(f"<div class='{card_style}'>", unsafe_allow_html=True)
            
            # 通知内容
            st.markdown(notification["content"])
            st.caption(f"受信日時: {formatted_time}")
            
            # リンクボタン（該当する場合）
            if notification["link_type"] and notification["link_id"]:
                if notification["link_type"] == "report":
                    if st.button(f"日報を確認する", key=f"notification_{i}_link"):
                        # ここで該当日報へのリンク処理（例：URLパラメータセット）
                        st.session_state["view_report_id"] = notification["link_id"]
                        switch_page("日報詳細")
                        st.rerun()
            
            # 既読ボタン（未読の場合のみ表示）
            if not notification["is_read"]:
                if st.button("既読にする", key=f"notification_{i}_read"):
                    if mark_as_read_function(notification["id"]):
                        st.success("既読にしました！")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error("既読の設定に失敗しました。")
            
            st.markdown("</div>", unsafe_allow_html=True)
            st.markdown("<br>", unsafe_allow_html=True)

def my_page():
    if "user" not in st.session_state or st.session_state["user"] is None:
        st.error("ログインしてください。")
        return

    st.title("マイページ")

    # ユーザー情報取得
    user = st.session_state["user"]
    is_admin = user.get("admin", False)
    
    # 管理者向け機能: ユーザー選択
    selected_user_name = user["name"]
    selected_user_code = user["code"]
    
    # タブを設定
    tab1, tab2, tab3 = st.tabs(["プロフィール・統計", "投稿履歴", "担当店舗リスト登録"])

    with tab1:
        # 管理者向け機能: ユーザー選択
        if is_admin:
            st.markdown("### 管理者ビュー")
            
            # ユーザーリスト取得
            from db_utils import get_all_users
            all_users = get_all_users()
            
            # ユーザーを選択
            selected_user_name = st.selectbox(
                "ユーザー選択",
                options=all_users,
                index=all_users.index(user["name"]) if user["name"] in all_users else 0
            )
            
            # 選択したユーザーの社員コードを取得するロジックが必要
            # ここでは簡略化のため、現在のユーザーが選択された場合のみ正確なコードが使われる
            if selected_user_name == user["name"]:
                selected_user_code = user["code"]
            else:
                # 他のユーザーを選択した場合は社員コードがないためnullを使用
                selected_user_code = None
    
        col1, col2 = st.columns([1, 2])
        with col1:
            # プロフィール情報
            st.markdown("### プロフィール")
            st.markdown(f"**名前**: {selected_user_name}")
            if selected_user_name == user["name"]:
                st.markdown(f"**社員コード**: {user['code']}")
                st.markdown(f"**所属部署**: {', '.join(user['depart'])}")
            
            # 日報投稿数サマリー
            st.markdown("### 日報投稿数")
            from db_utils import get_user_monthly_report_summary
            # ユーザーコードがある場合はコードで、ない場合はユーザー名で検索
            report_summary = get_user_monthly_report_summary(
                user_code=selected_user_code if selected_user_name == user["name"] else None,
                user_name=selected_user_name
            )
            
            if report_summary:
                # 最近6ヶ月分のデータを表示
                months = list(report_summary.keys())[:6]
                counts = [report_summary[m] for m in months]
                
                # 月表示を "YYYY-MM" から "YYYY年MM月" に変換
                formatted_months = []
                for m in months:
                    year, month = m.split("-")
                    formatted_months.append(f"{year}年{month}月")
                
                # 棒グラフで表示
                report_data = {
                    "月": formatted_months,
                    "投稿数": counts
                }
                report_df = pd.DataFrame(report_data)
                
                st.bar_chart(report_df.set_index("月"), use_container_width=True)
            else:
                st.info("日報投稿記録がありません。")
        
        with col2:
            # 訪問店舗統計
            st.markdown("### 店舗訪問統計")
            
            # 年月選択
            current_date = datetime.now()
            year = st.selectbox("年", options=range(current_date.year-2, current_date.year+1), index=2)
            month = st.selectbox("月", options=range(1, 13), index=current_date.month-1)
            
            # 統計データ取得
            from db_utils import get_store_visit_stats
            # 選択したユーザーの店舗訪問統計を取得
            if selected_user_name == user["name"]:
                # 自分自身の場合はuser_codeを使用
                stats = get_store_visit_stats(
                    user_code=selected_user_code, 
                    year=year, 
                    month=month
                )
            else:
                # 他のユーザーの場合はuser_nameを使用
                stats = get_store_visit_stats(
                    user_name=selected_user_name,
                    year=year, 
                    month=month
                )
            
            if stats:
                # 訪問回数の棒グラフ
                visit_data = {
                    "店舗名": [f"{s['name']} ({s['code']})" for s in stats],
                    "訪問回数": [s["count"] for s in stats]
                }
                
                chart_data = pd.DataFrame(visit_data)
                st.bar_chart(chart_data.set_index("店舗名"), use_container_width=True)
                
                # 詳細データをテーブルで表示
                table_data = []
                for s in stats:
                    table_data.append({
                        "店舗コード": s["code"],
                        "店舗名": s["name"],
                        "訪問回数": s["count"],
                        "訪問日": ", ".join(s["dates"])
                    })
                
                st.markdown("#### 訪問詳細")
                st.table(pd.DataFrame(table_data))
            else:
                st.info(f"{year}年{month}月の店舗訪問記録はありません。")
    
        with tab2:
            # 管理者でない場合または自分自身のページを見ている場合のみ投稿一覧を表示
            if not is_admin or selected_user_name == user["name"]:
                st.markdown("### 自分の投稿")
            
            # 時間範囲選択
            time_range = st.radio(
                "表示期間",
                ["24時間以内", "1週間以内", "すべて表示"],
                horizontal=True,
                index=1
            )
            
            # 選択された時間範囲を変換
            time_range_param = None
            if time_range == "24時間以内":
                time_range_param = "24h"
            elif time_range == "1週間以内":
                time_range_param = "1w"
            # "すべて表示"の場合はNoneのまま
            
            # タブ（日報/コメント）
            tab1_reports, tab2_reports = st.tabs(["投稿した日報", "コメントした日報"])
            
            with tab1_reports:
                # 自分の投稿した日報
                my_reports = load_reports(time_range=time_range_param)
                my_reports = [r for r in my_reports if r["投稿者"] == user["name"]]
                
                if my_reports:
                    display_reports(my_reports)
                else:
                    st.info("表示できる日報はありません。")
            
            with tab2_reports:
                # 自分がコメントした日報
                commented_reports = load_commented_reports(user["name"])
                
                # 時間範囲でフィルタリング（簡易的な実装）
                if time_range_param:
                    current_time = datetime.now() + timedelta(hours=9)  # JST
                    filtered_reports = []
                    
                    for report in commented_reports:
                        post_time = datetime.strptime(report["投稿日時"], "%Y-%m-%d %H:%M:%S")
                        
                        if time_range_param == "24h" and (current_time - post_time).total_seconds() <= 86400:  # 24時間以内
                            filtered_reports.append(report)
                        elif time_range_param == "1w" and (current_time - post_time).total_seconds() <= 604800:  # 1週間（7日）以内
                            filtered_reports.append(report)
                    
                    commented_reports = filtered_reports
                
                if commented_reports:
                    display_reports(commented_reports)
                else:
                    st.info("表示できるコメント付き日報はありません。")
    
        with tab3:
            # 担当店舗リスト登録
            st.markdown("### 担当店舗リストの登録")
            st.markdown("""
            担当店舗リストの画像をアップロードして、自動的に担当店舗を登録できます。
            
            **注意事項**：
            - 画像は店舗コードと店舗名が明確に記載されたものを使用してください
            - 読み取り精度を上げるため、できるだけ鮮明な画像をアップロードしてください
            """)
            
            # 画像アップロード
            uploaded_file = st.file_uploader("担当店舗リスト画像", type=["png", "jpg", "jpeg"])
            
            if uploaded_file is not None:
                # 画像表示
                img_bytes = uploaded_file.read()
                st.image(img_bytes, caption="アップロードされた担当店舗リスト", use_column_width=True)
                
                # OCR処理ボタン
                if st.button("画像から店舗リストを読み取る"):
                    from ocr_utils import process_store_image_and_extract_list
                    
                    st.info("店舗リストを読み取っています...")
                    # OCR処理
                    stores = process_store_image_and_extract_list(img_bytes)
                    
                    if stores and len(stores) > 0:
                        st.success(f"{len(stores)}件の店舗情報を抽出しました")
                        
                        # 抽出結果の表示
                        st.markdown("### 抽出された店舗リスト")
                        store_df = pd.DataFrame(stores)
                        store_df = store_df.rename(columns={
                            "code": "店舗コード",
                            "name": "店舗名"
                        })
                        st.dataframe(store_df)
                        
                        # システムに登録する際に必要な情報を追加
                        for store in stores:
                            store["担当者社員コード"] = user.get('code')
                            store["postal_code"] = ""
                            store["address"] = ""
                            store["staff_name"] = user.get('name')
                        
                        # 登録ボタン
                        if st.button("これらの店舗を担当店舗として登録する"):
                            from db_utils import save_stores_data
                            if save_stores_data(stores):
                                st.success("担当店舗として登録しました")
                            else:
                                st.error("登録に失敗しました")
                    else:
                        st.error("店舗情報を抽出できませんでした。別の画像をお試しください。")

def export_data():
    if "user" not in st.session_state or st.session_state["user"] is None:
        st.error("ログインしてください。")
        return

    # 管理者権限チェック
    if not st.session_state["user"].get("admin", False):
        st.error("データエクスポートには管理者権限が必要です。")
        return

    st.title("データエクスポート")

    tab1, tab2, tab3, tab4 = st.tabs(["日報データ", "週間予定データ", "投稿統計", "店舗訪問データ"])

    with tab1:
        st.markdown("### 日報データのエクスポート")
        
        # 期間指定
        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input("開始日", value=date.today() - timedelta(days=30), key="report_start_date")
        with col2:
            end_date = st.date_input("終了日", value=date.today(), key="report_end_date")
        
        # 部署選択
        department = st.selectbox(
            "部署を選択（任意）",
            ["すべての部署", "営業部", "管理部", "技術部", "総務部"],
            index=0
        )
        
        if st.button("日報データをエクスポート"):
            # 条件に合った日報データを取得
            from db_utils import load_reports_by_date
            
            # 部署フィルタ
            dept = None if department == "すべての部署" else department
            
            # データ取得
            reports = load_reports(depart=dept)
            
            # 日付フィルタリング
            start_date_str = start_date.strftime("%Y-%m-%d")
            end_date_str = end_date.strftime("%Y-%m-%d")
            filtered_reports = [r for r in reports if start_date_str <= r["日付"] <= end_date_str]
            
            if filtered_reports:
                # 日付範囲をファイル名に含める
                filename = f"日報データ_{start_date_str}_{end_date_str}.xlsx"
                
                # Excelエクスポート処理
                download_link = excel_utils.export_to_excel(filtered_reports, filename)
                st.markdown(download_link, unsafe_allow_html=True)
            else:
                st.warning("指定された条件に一致する日報データがありません。")

    with tab2:
        st.markdown("### 週間予定データのエクスポート")
        
        # 期間指定
        col1, col2 = st.columns(2)
        with col1:
            start_month = st.date_input("開始月", value=date.today().replace(day=1) - timedelta(days=30), key="schedule_start_date")
        with col2:
            end_month = st.date_input("終了月", value=date.today().replace(day=28), key="schedule_end_date")
        
        if st.button("週間予定データをエクスポート"):
            # 週間予定データを取得
            schedules = load_weekly_schedules()
            
            # 期間でフィルタリング
            start_date_str = start_month.strftime("%Y-%m-%d")
            end_date_str = end_month.strftime("%Y-%m-%d")
            filtered_schedules = [s for s in schedules if start_date_str <= s["開始日"] <= end_date_str]
            
            if filtered_schedules:
                # 日付範囲をファイル名に含める
                filename = f"週間予定データ_{start_date_str}_{end_date_str}.xlsx"
                
                # Excelエクスポート処理
                download_link = excel_utils.export_weekly_schedules_to_excel(filtered_schedules, filename)
                st.markdown(download_link, unsafe_allow_html=True)
            else:
                st.warning("指定された期間に一致する週間予定データがありません。")

    with tab3:
        st.markdown("### 投稿統計データ")
        
        # 期間指定
        col1, col2 = st.columns(2)
        with col1:
            year = st.selectbox("年", options=range(date.today().year - 2, date.today().year + 1), index=2)
        with col2:
            month = st.selectbox("月", options=[0] + list(range(1, 13)), format_func=lambda x: "すべての月" if x == 0 else f"{x}月")
        
        # 統計データを取得
        from db_utils import get_monthly_report_count
        month_value = None if month == 0 else month
        stats = get_monthly_report_count(year=year, month=month_value)
        
        if stats:
            # テーブル表示用にデータを整形
            if month_value:
                # 特定月のデータをユーザー別に表示
                st.markdown(f"#### {year}年{month}月の投稿数")
                
                # 年月でフィルタリング
                year_month = f"{year}-{month_value:02d}"
                filtered_stats = [s for s in stats if s["年月"] == year_month]
                
                if filtered_stats:
                    # データフレームに変換して表示
                    df = pd.DataFrame(filtered_stats)
                    df = df.rename(columns={"投稿者": "名前", "年月": "年月", "投稿数": "投稿数"})
                    st.table(df)
                    
                    # グラフで表示
                    st.bar_chart(df.set_index("名前")["投稿数"])
                else:
                    st.info(f"{year}年{month}月のデータはありません。")
            else:
                # 全月のデータを表示（ピボットテーブル形式）
                st.markdown(f"#### {year}年の月別投稿数")
                
                # 年でフィルタリング
                year_prefix = f"{year}-"
                filtered_stats = [s for s in stats if s["年月"].startswith(year_prefix)]
                
                if filtered_stats:
                    # ピボットテーブル形式に整形
                    pivot_data = {}
                    
                    for stat in filtered_stats:
                        user = stat["投稿者"]
                        year_month = stat["年月"]
                        count = stat["投稿数"]
                        
                        if user not in pivot_data:
                            pivot_data[user] = {"名前": user}
                        
                        # 月だけを取り出して列名にする（例: "2024-01" -> "1月"）
                        month_str = f"{int(year_month.split('-')[1])}月"
                        pivot_data[user][month_str] = count
                    
                    # データフレームに変換して表示
                    pivot_df = pd.DataFrame(list(pivot_data.values()))
                    
                    # 月の列を正しい順序に並べ替え
                    month_cols = [f"{m}月" for m in range(1, 13)]
                    existing_cols = [col for col in month_cols if col in pivot_df.columns]
                    
                    if existing_cols:
                        st.table(pivot_df[["名前"] + existing_cols])
                        
                        # 合計を計算して追加
                        pivot_df["合計"] = pivot_df[existing_cols].sum(axis=1)
                        st.markdown("#### 年間投稿数（降順）")
                        st.bar_chart(pivot_df.sort_values("合計", ascending=False).set_index("名前")["合計"])
                    else:
                        st.info(f"{year}年のデータはありません。")
                else:
                    st.info(f"{year}年のデータはありません。")
                
            # エクスポートボタン
            if st.button("投稿統計データをエクスポート"):
                # 統計データをExcelにエクスポート
                output = BytesIO()
                with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                    # フィルタリングされたデータをDataFrameに変換
                    year_prefix = f"{year}-"
                    filtered_stats = [s for s in stats if s["年月"].startswith(year_prefix)]
                    
                    if filtered_stats:
                        # 通常の形式（1シート目）
                        df = pd.DataFrame(filtered_stats)
                        df.to_excel(writer, sheet_name="投稿統計", index=False)
                        
                        # ピボット形式（2シート目）
                        pivot_data = {}
                        for stat in filtered_stats:
                            user = stat["投稿者"]
                            year_month = stat["年月"]
                            count = stat["投稿数"]
                            
                            if user not in pivot_data:
                                pivot_data[user] = {"名前": user}
                            
                            # 月だけを取り出して列名にする
                            month_str = f"{int(year_month.split('-')[1])}月"
                            pivot_data[user][month_str] = count
                        
                        # データフレームに変換
                        pivot_df = pd.DataFrame(list(pivot_data.values()))
                        
                        # 月の列を正しい順序に並べ替え
                        month_cols = [f"{m}月" for m in range(1, 13)]
                        existing_cols = [col for col in month_cols if col in pivot_df.columns]
                        
                        if existing_cols:
                            # 合計を計算して追加
                            pivot_df["合計"] = pivot_df[existing_cols].sum(axis=1)
                            pivot_df = pivot_df.sort_values("合計", ascending=False)
                            
                            # 2シート目に保存
                            pivot_df.to_excel(writer, sheet_name="ユーザー別サマリー", index=False)
                
                # Excel ファイルのダウンロードリンク
                output.seek(0)
                b64 = base64.b64encode(output.read()).decode()
                filename = f"投稿統計_{year}年.xlsx"
                href = f'<a href="data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{b64}" download="{filename}">ダウンロード: {filename}</a>'
                st.markdown(href, unsafe_allow_html=True)
        else:
            st.info("投稿統計データがありません。")
    
    with tab4:
        st.markdown("### 店舗訪問データのエクスポート")
        
        # 期間指定
        col1, col2 = st.columns(2)
        with col1:
            year = st.selectbox("年", options=range(date.today().year - 2, date.today().year + 1), index=2, key="visit_year")
        with col2:
            month = st.selectbox("月", options=[0] + list(range(1, 13)), 
                             format_func=lambda x: "すべての月" if x == 0 else f"{x}月", key="visit_month")
        
        # データを取得するボタン
        if st.button("店舗訪問データを集計"):
            # 全ユーザーの店舗訪問データを取得
            from db_utils import get_all_users_store_visits
            
            # 月の値を適切に設定
            month_value = None if month == 0 else month
            
            # データ取得
            all_visits = get_all_users_store_visits(year=year, month=month_value)
            
            if all_visits:
                # テーブル表示用にデータを整形
                st.markdown("#### 訪問店舗データサマリー")
                
                # ユーザーごとの訪問店舗数・訪問回数の合計
                summary_data = []
                for user_name, stores in all_visits.items():
                    total_visits = sum(store["count"] for store in stores)
                    summary_data.append({
                        "ユーザー名": user_name,
                        "訪問店舗数": len(stores),
                        "訪問回数合計": total_visits
                    })
                
                # データフレームに変換して表示
                summary_df = pd.DataFrame(summary_data)
                summary_df = summary_df.sort_values("訪問回数合計", ascending=False)
                st.table(summary_df)
                
                # 詳細データ（折りたたみ）
                with st.expander("店舗訪問詳細データ（ユーザー別）"):
                    for user_name, stores in all_visits.items():
                        st.markdown(f"##### {user_name}")
                        
                        user_data = []
                        for store in stores:
                            user_data.append({
                                "店舗コード": store["code"],
                                "店舗名": store["name"],
                                "訪問回数": store["count"],
                                "訪問日": ", ".join(store["dates"])
                            })
                        
                        user_df = pd.DataFrame(user_data)
                        if not user_df.empty:
                            user_df = user_df.sort_values("訪問回数", ascending=False)
                            st.table(user_df)
                        else:
                            st.info(f"{user_name}の訪問データはありません。")
                        
                        st.markdown("---")
                
                # エクスポートボタン
                if st.button("店舗訪問データをエクスポート"):
                    # 期間を含めたファイル名
                    period = f"{year}年"
                    if month_value:
                        period += f"{month_value}月"
                    else:
                        period += "全月"
                    
                    filename = f"店舗訪問データ_{period}.xlsx"
                    
                    # Excelエクスポート処理
                    download_link = excel_utils.export_store_visits_to_excel(all_visits, filename)
                    st.markdown(download_link, unsafe_allow_html=True)
            else:
                st.info("指定された期間の店舗訪問データはありません。")

def upload_stores_data():
    if "user" not in st.session_state or st.session_state["user"] is None:
        st.error("ログインしてください。")
        return

    # 管理者権限チェック
    if not st.session_state["user"].get("admin", False):
        st.error("店舗データのアップロードには管理者権限が必要です。")
        return

    st.title("店舗データアップロード")
    
    st.markdown("""
    ### 店舗データのアップロード
    
    Excelファイルから店舗データをアップロードします。
    
    #### 必要なカラム:
    - 得意先c
    - 得意先名
    - 郵便番号
    - 住所
    - 部門c
    - 担当者c
    - 担当者名
    - 担当者社員コード
    """)
    
    # ファイルアップロード
    uploaded_file = st.file_uploader("Excelファイルを選択", type=["xlsx", "xls"])
    
    if uploaded_file is not None:
        # Excelファイルを処理
        stores_data, error = excel_utils.convert_excel_to_json(uploaded_file, "stores")
        
        if error:
            st.error(f"エラー: {error}")
        elif stores_data:
            # データプレビュー
            st.markdown("### データプレビュー")
            
            preview_data = []
            for i, store in enumerate(stores_data[:10]):  # 最初の10件のみ表示
                preview_data.append({
                    "コード": store["code"],
                    "名称": store["name"],
                    "郵便番号": store["postal_code"],
                    "住所": store["address"],
                    "担当者": store["staff_name"],
                    "社員コード": store["担当者社員コード"]
                })
            
            st.table(pd.DataFrame(preview_data))
            
            # 続きがある場合
            if len(stores_data) > 10:
                st.caption(f"他 {len(stores_data) - 10} 件のデータがあります。")
            
            # 保存ボタン
            if st.button("店舗データを保存"):
                if save_stores_data(stores_data):
                    st.success(f"店舗データを保存しました。合計: {len(stores_data)}件")
                else:
                    st.error("店舗データの保存に失敗しました。")
        else:
            st.error("データの変換に失敗しました。")

# ✅ メインアプリ
def main():
    # アプリタイトル設定
    # st.set_page_config(page_title="OK-Nippou", layout="wide")  

    # ログイン状態に応じてページをレンダリング
    if st.session_state["user"] is None:
        login()
    else:
        # サイドバーナビゲーション
        sidebar_navigation()
        
        # 現在のページをレンダリング
        page = st.session_state["page"]
        
        if page == "タイムライン":
            timeline()
        elif page == "週間予定":
            show_weekly_schedules()
        elif page == "お知らせ":
            show_notices()
        elif page == "日報投稿":
            post_report()
        elif page == "日報編集":
            edit_report_page()
        elif page == "週間予定投稿":
            post_weekly_schedule()
        elif page == "お知らせ投稿":
            post_notice()
        elif page == "マイページ":
            my_page()
        elif page == "データエクスポート":
            export_data()
        elif page == "通知":
            show_notifications()
        elif page == "店舗データアップロード":
            upload_stores_data()
        else:
            st.error(f"不明なページ: {page}")

if __name__ == "__main__":
    main()
