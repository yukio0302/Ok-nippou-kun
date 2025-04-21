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
import calendar

# ライトモードを強制設定（.streamlit/config.tomlで設定）
st.set_page_config(page_title="OK-NIPPOU", initial_sidebar_state="expanded", layout="wide", page_icon="📝")

# モバイル用のCSS調整はstatic/style.cssファイルで管理

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
    add_weekly_schedule_columns, load_weekly_schedules, get_user_stores,
    get_user_store_visits, get_store_visit_stats, save_stores_data,
    search_stores, load_report_by_id, save_notice, load_reports_by_date,
    save_report_image, get_report_images, delete_report_image
)

# excel_utils.py をインポート
import excel_utils

# CSSファイルを読み込む関数
def load_css(file_name):
    try:
        with open(file_name) as f:
            st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)
    except Exception as e:
        logging.warning(f"スタイルファイル読み込みエラー: {e}")

# カスタムCSSファイルの読み込み (スタイルファイルは static ディレクトリに配置)
css_file_path = "static/style.css"
load_css(css_file_path)

# ✅ PostgreSQL 初期化（データを消さない）
init_db(keep_existing=True)

# 週間予定テーブルの必要なカラムの確認・追加
add_weekly_schedule_columns()

# ✅ ログイン状態を管理
if "user" not in st.session_state:
    st.session_state["user"] = None
if "page" not in st.session_state:
    st.session_state["page"] = "ログイン"

# ✅ ページ遷移関数（修正済み）
def switch_page(page_name, hide_sidebar=False):
    """
    ページを切り替える（即時リロードはなし！）
    
    Args:
        page_name: 切り替えるページ名
        hide_sidebar: サイドバーを自動的に隠すかどうか（デフォルトはFalse）
    """
    st.session_state["page"] = page_name
    # サイドバーの自動非表示は無効化 (ユーザーリクエストにより)
    # if hide_sidebar:
    #     st.session_state["hide_sidebar"] = True

# ✅ サイドバーナビゲーションの追加
def sidebar_navigation():
    with st.sidebar:
        # ロゴ表示
        try:
            st.image("static/images/logo.png", use_container_width=True)
        except:
            st.title("OK-NIPPOU")  # 画像がない場合はタイトルを表示

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

        # メニューヘッダー
        st.markdown("### メニュー")
        
        # 「メニューを閉じる」ボタンは削除（ナビゲーションボタンで自動的にサイドバーが閉じるため不要）
        
        # 通知の未読数を取得
        from db_utils import get_user_notifications
        unread_notifications = get_user_notifications(st.session_state["user"]["name"], unread_only=True)
        unread_count = len(unread_notifications)
        notification_badge = f"🔔 通知 ({unread_count})" if unread_count > 0 else "🔔 通知"
        
        if st.button(" マイページ", key="sidebar_mypage"):
            switch_page("マイページ")
            # モバイル表示の場合はサイドバーを自動的に閉じる
            st.session_state["hide_sidebar"] = True
            st.rerun()
        
        if st.button(" 日報作成", key="sidebar_post_report"):
            switch_page("日報投稿")
            # モバイル表示の場合はサイドバーを自動的に閉じる
            st.session_state["hide_sidebar"] = True
            st.rerun()
        
        if st.button(notification_badge, key="sidebar_notifications"):
            switch_page("通知")
            # モバイル表示の場合はサイドバーを自動的に閉じる
            st.session_state["hide_sidebar"] = True
            st.rerun()
        
        if st.button("⏳ タイムライン", key="sidebar_timeline"):
            switch_page("タイムライン")
            # モバイル表示の場合はサイドバーを自動的に閉じる
            st.session_state["hide_sidebar"] = True
            st.rerun()

            
        # 管理者向け機能
        if user.get("admin", False):
            st.markdown("### 管理者メニュー")
            
            if st.button(" データエクスポート", key="sidebar_export"):
                switch_page("データエクスポート")
                # モバイル表示の場合はサイドバーを自動的に閉じる
                st.session_state["hide_sidebar"] = True
                st.rerun()
                
            if st.button("⭐ お気に入りメンバー管理", key="sidebar_favorite_members"):
                switch_page("お気に入りメンバー管理")
                # モバイル表示の場合はサイドバーを自動的に閉じる
                st.session_state["hide_sidebar"] = True
                st.rerun()

# ✅ ログイン機能（修正済み）
def login():
    # ロゴ表示（中央揃え、サイズを小さく）
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        try:
            # ロゴを表示 - CSSクラスを適用してサイズを制限（2倍サイズに変更）
            st.markdown('<div class="login-logo">', unsafe_allow_html=True)
            st.image("static/images/logo.png", width=600)  # 幅を600pxに拡大
            st.markdown('</div>', unsafe_allow_html=True)
        except:
            st.title("OK-NIPPOU")  # 画像がない場合はタイトルを表示

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
            st.session_state["page"] = "マイページ"
            st.rerun()  # ✅ ここで即リロード！
        else:
            st.error("社員コードまたはパスワードが間違っています。")

def post_weekly_schedule():
    if "user" not in st.session_state or st.session_state["user"] is None:
        st.error("ログインしてください。")
        return
        
    # 営業部のユーザーまたは管理者のみ週間予定投稿可能
    if "営業部" not in st.session_state["user"]["depart"] and not st.session_state["user"].get("admin", False):
        st.warning("週間予定投稿は営業部のメンバーまたは管理者のみ可能です。")
        return

    st.title("週間予定投稿")

    # 編集モードかどうかを確認
    is_editing = "editing_schedule" in st.session_state
    editing_schedule = st.session_state.get("editing_schedule", None)
    
    if is_editing:
        st.info(f"週間予定を編集しています。(ID: {editing_schedule.get('id', 'N/A')})")

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
    
    # 編集モードでは、その週を選択（デフォルトは現在の週）
    index = 4  # デフォルトは現在の週(index=4)
    if is_editing and "年" in editing_schedule and "週" in editing_schedule:
        # 編集対象の週の日付を見つける処理
        for i, (start, end, label) in enumerate(week_options):
            # 開始日を比較
            if isinstance(editing_schedule.get('開始日'), str):
                try:
                    schedule_start = datetime.strptime(editing_schedule['開始日'], "%Y-%m-%d").date()
                    if start == schedule_start:
                        index = i
                        break
                except:
                    pass
            
    selected_week = st.selectbox(
        "該当週を選択",
        options=week_options,
        format_func=lambda x: x[2],
        index=index
    )
    start_date, end_date, _ = selected_week

    # ユーザーの担当店舗を取得（ここでは一度だけ取得してキャッシュ）
    if 'user_stores' not in st.session_state:
        st.session_state.user_stores = get_user_stores(st.session_state["user"]["code"])
    user_stores = st.session_state.user_stores
    
    # 検索結果を一度だけキャッシュ
    if 'weekly_search_results' not in st.session_state:
        st.session_state.weekly_search_results = {}
    
    # 週間予定入力用の辞書
    weekly_plan = {}
    weekly_visited_stores = {}
    
    # 選択済みの店舗を保持するための辞書型の状態変数（初期値設定）
    if 'weekly_selected_stores' not in st.session_state:
        st.session_state.weekly_selected_stores = {
            "月曜日": [], "火曜日": [], "水曜日": [], "木曜日": [],
            "金曜日": [], "土曜日": [], "日曜日": []
        }
    
    # 編集モードの場合、既存データからweekly_selected_storesを初期化
    if is_editing and not st.session_state.get("initialized_edit_weekly", False):
        # 編集用に店舗データを準備
        for day in ["月曜日", "火曜日", "水曜日", "木曜日", "金曜日"]:
            # 日付と店舗データのキー
            stores_key = f"{day}_visited_stores"
            
            # 店舗データが存在する場合
            if stores_key in editing_schedule and editing_schedule[stores_key]:
                st.session_state.weekly_selected_stores[day] = editing_schedule[stores_key]
                
        # 初期化済みフラグを設定
        st.session_state["initialized_edit_weekly"] = True
    
    # 各曜日の予定と店舗選択
    weekdays = ["月曜日", "火曜日", "水曜日", "木曜日", "金曜日", "土曜日", "日曜日"]
    
    # 1列レイアウトに変更（2列だとレイアウトが崩れる問題を修正）
    for i, weekday in enumerate(weekdays):
        current_date = start_date + timedelta(days=i)
        date_label = f"{current_date.month}月{current_date.day}日（{weekday}）"
        
        # 各曜日ごとにセクションを分ける
        st.markdown(f"## {date_label}")
        
        # 日ごとに選択された店舗を表示/保存するリスト
        day_stores = []
        
        # この曜日用の選択済み店舗を保存するための配列
        selected_in_this_session = []
        
        # 予定入力の場合は店舗名自動入力なし - この変数は完全に不要
        # 以前は店舗名が自動的にテキストエリアに追加されていたが、それをやめる
        # store_text変数は使用しない
        
        st.markdown("### 店舗選択")
        
        # 場所入力・選択方法のタブ
        location_tabs = st.tabs(["担当店舗から選択", "店舗を検索", "自由入力"])
        
        with location_tabs[0]:
            # 担当店舗マルチセレクト
            store_options = [f"{store['code']}: {store['name']}" for store in user_stores]
            selected_assigned_stores = st.multiselect(
                f"担当店舗から選択",
                options=store_options,
                key=f"assigned_stores_{weekday}"
            )
            
            # 選択した担当店舗を処理
            for selected in selected_assigned_stores:
                code, name = selected.split(": ", 1)
                store_dict = {"code": code, "name": name}
                
                # 重複確認（同じ店舗が存在しない場合のみ追加）
                if not any(s.get("code") == code and s.get("name") == name for s in selected_in_this_session):
                    selected_in_this_session.append(store_dict)
                    day_stores.append(store_dict)
                    # 店舗名のテキスト追加は不要に
                    
                    # セッション状態に保存
                    if weekday not in st.session_state.weekly_selected_stores:
                        st.session_state.weekly_selected_stores[weekday] = []
                    if not any(s.get("code") == code and s.get("name") == name 
                           for s in st.session_state.weekly_selected_stores[weekday]):
                        st.session_state.weekly_selected_stores[weekday].append(store_dict)
        
        with location_tabs[1]:
            # 店舗検索機能 - 入力フィールドと検索ボタンを横に配置
            col1, col2 = st.columns([4, 1])
            with col1:
                search_term = st.text_input("店舗名または住所で検索", key=f"store_search_{weekday}")
            
            # 検索キーをセッション状態に保存
            if f"last_search_term_{weekday}" not in st.session_state:
                st.session_state[f"last_search_term_{weekday}"] = ""
                
            with col2:
                # 検索ボタンを押したときにセッション状態を更新するだけ
                search_button = st.button("検索", key=f"search_button_{weekday}")
                if search_button and search_term:
                    st.session_state[f"last_search_term_{weekday}"] = search_term
            
            # 検索結果表示（キャッシュを利用）
            search_results = []
            # 検索ボタンが押されたか、または前回の検索キーワードがある場合
            current_search_term = st.session_state[f"last_search_term_{weekday}"] if f"last_search_term_{weekday}" in st.session_state else ""
            if current_search_term:
                cache_key = f"{weekday}_{current_search_term}"
                if cache_key in st.session_state.weekly_search_results:
                    search_results = st.session_state.weekly_search_results[cache_key]
                else:
                    search_results = search_stores(current_search_term)
                    st.session_state.weekly_search_results[cache_key] = search_results
            # この部分は不要になったので削除（current_search_termで管理）
                
            search_store_options = [f"{store['code']}: {store['name']}" for store in search_results]
            # ここでの選択は一時的なものなので普通のselectboxを使う（マルチセレクトを使わない）
            # セッション状態用のキーを分けて管理
            select_key = f"searched_store_{weekday}"
            reset_key = f"reset_searched_store_{weekday}"
            
            # リセットフラグが立っている場合、初期インデックスを0に設定
            initial_index = 0
            
            selected_store = st.selectbox(
                "検索結果から選択",
                options=["選択してください"] + search_store_options,
                key=select_key,
                index=initial_index
            )
            
            # 選択が行われた場合のみ処理
            selected_searched_stores = []
            if selected_store and selected_store != "選択してください":
                selected_searched_stores = [selected_store]
            
            # 選択した検索結果店舗を処理
            for selected in selected_searched_stores:
                code, name = selected.split(": ", 1)
                store_dict = {"code": code, "name": name}
                
                # 重複確認（同じ店舗が存在しない場合のみ追加）
                if not any(s.get("code") == code and s.get("name") == name for s in selected_in_this_session):
                    selected_in_this_session.append(store_dict)
                    day_stores.append(store_dict)
                    # 店舗名のテキスト追加は不要に
                    
                    # セッション状態に保存
                    if weekday not in st.session_state.weekly_selected_stores:
                        st.session_state.weekly_selected_stores[weekday] = []
                    if not any(s.get("code") == code and s.get("name") == name 
                           for s in st.session_state.weekly_selected_stores[weekday]):
                        st.session_state.weekly_selected_stores[weekday].append(store_dict)
            
        with location_tabs[2]:
            # 自由入力（見込み客など）
            custom_locations = st.text_area(
                "場所を自由に入力（複数の場合は改行で区切る）",
                key=f"custom_locations_{weekday}",
                placeholder="例: 〇〇商事（見込み客）\n社内会議\n△△市役所..."
            )
            
            if st.button("追加", key=f"add_custom_{weekday}"):
                if custom_locations:
                    custom_locations_list = custom_locations.strip().split("\n")
                    for location in custom_locations_list:
                        if location.strip():
                            store_dict = {"code": "", "name": location.strip()}
                            
                            # 重複確認（同じ店舗が存在しない場合のみ追加）
                            if not any(s.get("name") == location.strip() and not s.get("code") 
                                   for s in selected_in_this_session):
                                selected_in_this_session.append(store_dict)
                                day_stores.append(store_dict)
                                # 店舗名のテキスト追加は不要に
                                
                                # セッション状態に保存
                                if weekday not in st.session_state.weekly_selected_stores:
                                    st.session_state.weekly_selected_stores[weekday] = []
                                if not any(s.get("name") == location.strip() and not s.get("code") 
                                       for s in st.session_state.weekly_selected_stores[weekday]):
                                    st.session_state.weekly_selected_stores[weekday].append(store_dict)
        
        # この曜日の店舗情報を保存
        weekly_visited_stores[f"{weekday}_visited_stores"] = day_stores
        
        # 訪問予定店の欄を表示（赤いマークで強調）- 予定欄の上に配置
        st.markdown("### 📍 訪問予定店")
        
        # 既存の選択がある場合
        if st.session_state.weekly_selected_stores.get(weekday, []):
            # 選択された店舗を表示するための枠を作成
            with st.container(border=True):
                for store_dict in st.session_state.weekly_selected_stores[weekday]:
                    # 選択済み店舗を表示し、削除ボタンをつける
                    col1, col2 = st.columns([5, 1])
                    with col1:
                        store_name = store_dict.get("name", "")
                        store_code = store_dict.get("code", "")
                        if store_code:
                            st.markdown(f"<span style='color:red; font-weight:bold;'>🏢 {store_name}</span> (コード: {store_code})", unsafe_allow_html=True)
                        else:
                            st.markdown(f"<span style='color:red; font-weight:bold;'>🏢 {store_name}</span>", unsafe_allow_html=True)
                    with col2:
                        # ユニークなキーを生成
                        remove_key = f"remove_{weekday}_{store_code}_{store_name}"
                        if st.button("削除", key=remove_key):
                            # 選択済み店舗から削除
                            st.session_state.weekly_selected_stores[weekday] = [
                                s for s in st.session_state.weekly_selected_stores[weekday]
                                if not (s.get("code", "") == store_code and s.get("name", "") == store_name)
                            ]
                            st.rerun()
        else:
            # 選択がない場合のメッセージ
            st.info("店舗が選択されていません。以下から訪問予定の店舗を選択してください。")
            
        # 予定入力欄 - 店舗名を表示しない
        weekly_plan[weekday] = st.text_area(
            f"{date_label} の予定",
            value="",  # 空の値を使用して店舗名を表示しない
            key=f"plan_{weekday}",
            height=100
        )

    # 編集モードの場合は、既存データをロード
    if is_editing:
        # 曜日フィールドに既存の値を設定
        for day in weekdays:
            if day in editing_schedule:
                default_text = editing_schedule.get(day, "")
                # セッションでキーが初期化済みの場合は、そのまま使用
                if f"plan_{day}" in st.session_state:
                    pass
                else:
                    # 初回の場合は値をセット
                    st.session_state[f"plan_{day}"] = default_text

    # 投稿ボタンラベル
    button_label = "編集を保存する" if is_editing else "投稿する"
    
    if st.button(button_label):
        schedule = {
            "投稿者": st.session_state["user"]["name"],
            "user_code": st.session_state["user"]["code"],
            "開始日": start_date.strftime("%Y-%m-%d"),
            "終了日": end_date.strftime("%Y-%m-%d"),
            "期間": f"{start_date.strftime('%Y-%m-%d')} 〜 {end_date.strftime('%Y-%m-%d')}",  # 期間フィールドも追加
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
        
        # 編集モードの場合、IDを追加
        if is_editing and "id" in editing_schedule:
            schedule["id"] = editing_schedule["id"]

        save_weekly_schedule(schedule)
        
        # 投稿後は選択をクリア
        st.session_state.weekly_selected_stores = {
            "月曜日": [], "火曜日": [], "水曜日": [], "木曜日": [],
            "金曜日": [], "土曜日": [], "日曜日": []
        }
        
        # 編集モードをクリア
        if "editing_schedule" in st.session_state:
            del st.session_state["editing_schedule"]
        if "initialized_edit_weekly" in st.session_state:
            del st.session_state["initialized_edit_weekly"]
            
        success_message = "✅ 週間予定を編集しました！" if is_editing else "✅ 週間予定を投稿しました！"
        st.success(success_message)
        time.sleep(1)
        switch_page("タイムライン")
        st.rerun()

def show_weekly_schedules():
    if "user" not in st.session_state or st.session_state["user"] is None:
        st.error("ログインしてください。")
        return

    st.title("週間予定一覧")
    
    # 週選択ヘルパー関数
    def generate_week_options_for_schedules():
        """選択可能な週のリストを生成（過去8週～今週および未来4週）"""
        today = datetime.today().date()
        options = []
        
        # 当日を含む週の月曜日を計算
        current_monday = today - timedelta(days=today.weekday())
        
        # 今週を含めて過去8週と未来4週を表示
        for i in range(-8, 5):
            start = current_monday + timedelta(weeks=i)
            end = start + timedelta(days=6)
            week_label = f"{start.month}/{start.day}（月）～{end.month}/{end.day}（日）"
            options.append((start, end, week_label, f"{start.strftime('%Y-%m-%d')} 〜 {end.strftime('%Y-%m-%d')}"))
        return options
    
    # 週選択UIの準備
    week_options = generate_week_options_for_schedules()
    
    # 現在の週のインデックスを計算（過去8週から始まるので、現在は8番目=インデックス8）
    current_week_index = 8
    
    # セッション状態の初期化（初期値は現在の週）
    if 'schedule_selected_week' not in st.session_state:
        st.session_state.schedule_selected_week = current_week_index
        
    # 表示方法を選択（ラジオボタン）
    st.markdown("### 表示オプション")
    view_option = st.radio(
        "表示オプション",
        ["今週の週間予定を見る", "先週の週間予定を見る", "該当週を選択", "すべての週間予定を見る"],
        horizontal=True,
        index=0  # デフォルトは「今週の週間予定を見る」
    )
    
    # 選択する週を決定
    if view_option == "今週の週間予定を見る":
        # 今週を表示
        selected_week_index = current_week_index
        selected_start_date, selected_end_date, _, selected_period = week_options[selected_week_index]
        st.info(f"今週 {week_options[selected_week_index][2]} の週間予定を表示しています")
    elif view_option == "先週の週間予定を見る":
        # 先週のインデックス（現在週の1つ前）
        selected_week_index = current_week_index - 1
        selected_start_date, selected_end_date, _, selected_period = week_options[selected_week_index]
        st.info(f"先週 {week_options[selected_week_index][2]} の週間予定を表示しています")
    elif view_option == "該当週を選択":
        # 週選択UIを表示
        st.markdown("### 該当週を選択")
        selected_week_index = st.selectbox(
            "週を選択",
            options=range(len(week_options)),
            format_func=lambda i: week_options[i][2],
            index=st.session_state.schedule_selected_week,
            key="schedule_week_selector",
            label_visibility="collapsed"
        )
        
        # 選択した週を保存
        st.session_state.schedule_selected_week = selected_week_index
        selected_start_date, selected_end_date, _, selected_period = week_options[selected_week_index]
    else:  # すべての週間予定を見る
        # すべての期間を表示するので期間選択は不要
        selected_period = None
        st.info("すべての週間予定を表示しています")
        # 値はエラー防止のため設定
        selected_week_index = current_week_index
    
    # ユーザー一覧を取得
    from db_utils import get_all_users
    all_users = get_all_users()
    
    # 「すべての週間予定を見る」が選択されているときのみユーザー検索を表示
    if view_option == "すべての週間予定を見る":
        # メンバー検索機能を追加
        st.markdown("### メンバーを検索")
        
        # 検索ボックスとユーザー選択
        user_search = st.text_input("ユーザー名で検索", key="weekly_user_search")
        
        # 検索に一致するユーザーをフィルタリング
        filtered_users = [user for user in all_users if user_search.lower() in user.lower()]
        
        # セッション状態の初期化
        if 'selected_schedule_user' not in st.session_state:
            st.session_state.selected_schedule_user = "すべて表示"
        
        # ユーザー選択（すべて表示のオプションを追加）
        user_options = ["すべて表示"] + filtered_users
        selected_user = st.selectbox(
            "ユーザーを選択",
            options=user_options,
            index=user_options.index(st.session_state.selected_schedule_user) if st.session_state.selected_schedule_user in user_options else 0,
            key="weekly_user_selector"
        )
        
        # 選択したユーザーを保存
        st.session_state.selected_schedule_user = selected_user
    else:
        # 「すべての週間予定を見る」以外の場合は、すべてのユーザーを表示
        selected_user = "すべて表示"
    
    # 週間予定データ取得
    schedules = load_weekly_schedules()

    if not schedules:
        st.info("週間予定はまだありません。")
        return
        
    # 選択した期間で絞り込み
    if selected_period is None:
        # すべての週間予定を表示
        filtered_schedules = schedules
    else:
        # 選択した期間で絞り込み（開始日と終了日で検索）
        selected_start_str = selected_start_date.strftime("%Y-%m-%d")
        selected_end_str = selected_end_date.strftime("%Y-%m-%d")
        
        # 期間が一致、または開始日・終了日が一致する週間予定を表示
        filtered_schedules = []
        for s in schedules:
            # 期間が完全に一致する場合
            if s.get("期間") == selected_period:
                filtered_schedules.append(s)
                continue
                
            # 開始日と終了日が一致する場合
            if s.get("開始日") == selected_start_str and s.get("終了日") == selected_end_str:
                filtered_schedules.append(s)
                continue
                
            # 開始日のみで比較する場合
            if s.get("開始日") == selected_start_str:
                filtered_schedules.append(s)
                continue
    
    # ユーザーで絞り込み（すべて表示以外の場合）
    if selected_user != "すべて表示":
        filtered_schedules = [s for s in filtered_schedules if s.get("投稿者") == selected_user]
    
    if not filtered_schedules:
        st.info(f"選択された期間とユーザーに一致する週間予定はありません。")
        return
    
    # 週間予定を期間でグループ化
    period_group = {}
    for schedule in filtered_schedules:
        period = schedule.get("期間")
        if period not in period_group:
            period_group[period] = []
        period_group[period].append(schedule)
    
    # 期間ごとに表示
    for period, period_schedules in period_group.items():
        # 投稿者でさらにグループ化
        user_group = {}
        for schedule in period_schedules:
            user = schedule.get("投稿者")
            if user not in user_group:
                user_group[user] = []
            user_group[user].append(schedule)
        
        # 期間の見出し
        st.markdown(f"## {period}の予定")
        
        # ユーザーごとに表示
        for user, user_schedules in user_group.items():
            for i, schedule in enumerate(user_schedules):
                # 週間予定用のユニークキー
                schedule_key = f"weekly_schedule_{schedule.get('id')}"
                
                # ユーザー名と期間でエクスパンダーを作成
                with st.expander(f"【{user}】 {schedule['開始日']} 〜 {schedule['終了日']}"):
                    # 開始日から各曜日の日付を計算
                    # 開始日が文字列かdatetimeかを確認して適切に処理
                    if isinstance(schedule['開始日'], str):
                        start_date = datetime.strptime(schedule['開始日'], "%Y-%m-%d")
                    else:
                        # すでにdatetimeオブジェクトの場合
                        start_date = datetime.combine(schedule['開始日'], datetime.min.time())
            
                    weekday_dates = {}
                    weekday_labels = {}
                    
                    # 各曜日のデータとその訪問店舗
                    weekdays = ["月曜日", "火曜日", "水曜日", "木曜日", "金曜日", "土曜日", "日曜日"]
                    japanese_weekdays = ["月", "火", "水", "木", "金", "土", "日"]
                    
                    # 各曜日の日付を計算
                    for i, day in enumerate(weekdays):
                        day_date = start_date + timedelta(days=i)
                        weekday_dates[day] = day_date
                        weekday_labels[day] = f"{day_date.month}/{day_date.day} ({japanese_weekdays[i]})"
                    
                    # 日ごとのデータを作成（行ごとに1日のスケジュール）
                    data = []
                    
                    for day in weekdays:
                        # 訪問店舗情報
                        visited_stores_key = f"{day}_visited_stores"
                        visited_stores = schedule.get(visited_stores_key, [])
                        store_names = [store["name"] for store in visited_stores] if visited_stores else []
                        store_text = ", ".join(store_names) if store_names else "なし"
                        
                        # 日ごとの行データ
                        row = {
                            "日付": weekday_labels[day],
                            "予定": schedule[day] if schedule[day] else "予定なし",
                            "訪問店舗": store_text
                        }
                        data.append(row)
                    
                    # DataFrameに変換
                    df = pd.DataFrame(data)
                    
                    # テーブル表示（インデックス列なし）
                    st.write(df.to_html(index=False), unsafe_allow_html=True)

                    st.caption(f"投稿者: {schedule['投稿者']} / 投稿日時: {schedule['投稿日時']}")

                    # コメント表示
                    if schedule["コメント"]:
                        st.markdown("#### コメント")
                        for comment in schedule["コメント"]:
                            st.markdown(f"""
                            <div class="comment-text">
                            <strong>{comment['投稿者']}</strong> - {comment['投稿日時']}<br/>
                            {comment['内容']}
                            </div>
                            ---
                            """, unsafe_allow_html=True)

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

def display_search_results(search_results_by_month, tab_suffix="search"):
    """検索結果表示関数"""
    if not search_results_by_month:
        st.info("検索結果はありません。")
        return
    
    # 月ごとに分類されたデータを表示
    # キーを年月の降順でソート
    sorted_months = sorted(search_results_by_month.keys(), reverse=True)
    
    for month_key in sorted_months:
        # 月の表示名をフォーマット
        try:
            month_date = datetime.strptime(month_key, "%Y-%m")
            month_display = f"{month_date.year}年{month_date.month}月"
        except:
            month_display = month_key
        
        # 月見出し（エクスパンダーではなく通常の見出し）
        st.markdown(f"## 📅 {month_display} ({len(search_results_by_month[month_key])}件)")
        
        # この月の日報を表示
        for i, report in enumerate(search_results_by_month[month_key]):
            # タブ区別用サフィックスを追加して、ユニークなインデックスを生成
            unique_prefix = f"{tab_suffix}_{month_key}_{i}_{report['id']}"
            
            # 日報日付から曜日を取得
            try:
                report_date = datetime.strptime(report["日付"], "%Y-%m-%d")
                weekday = ["月", "火", "水", "木", "金", "土", "日"][report_date.weekday()]
                formatted_date = f"{report_date.month}月{report_date.day}日（{weekday}）"
            except:
                formatted_date = report["日付"]
            
            # 日報表示カード（コンテナでスタイリング）
            with st.container(border=True):
                # タイトル部分
                st.markdown(f"### 【{report['投稿者']}】 {formatted_date} ({report['所属部署']})")
                
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
                    st.markdown("**実施内容、所感など**")
                    formatted_content = content.replace('\n', '<br>')
                    st.markdown(f"<div class='content-text'>{formatted_content}</div>", unsafe_allow_html=True)
                
                # 今後のアクション（旧：翌日予定）
                if "今後のアクション" in report and report["今後のアクション"]:
                    st.markdown("**今後のアクション**")
                    formatted_action = report["今後のアクション"].replace('\n', '<br>')
                    st.markdown(f"<div class='content-text'>{formatted_action}</div>", unsafe_allow_html=True)
                elif "翌日予定" in report and report["翌日予定"]:
                    st.markdown("**今後のアクション**")
                    formatted_action = report["翌日予定"].replace('\n', '<br>')
                    st.markdown(f"<div class='content-text'>{formatted_action}</div>", unsafe_allow_html=True)
                
                # 画像の表示
                report_images = get_report_images(report['id'])
                if report_images:
                    st.markdown("#### 添付画像")
                    for i, img in enumerate(report_images):
                        st.markdown(f"**{img['file_name']}**")
                        st.markdown(f"<img src='data:{img['file_type']};base64,{img['image_data']}' style='max-width:100%;'>", unsafe_allow_html=True)
                
                st.caption(f"投稿日時: {report['投稿日時']}")
                
                # リアクションボタンバー - 横並びにするためのHTMLクラスを追加
                st.markdown('<div class="reaction-buttons">', unsafe_allow_html=True)
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
                        
                        # リアクション済みの場合は色を変える
                        button_text = f"{emoji} {reaction_count}" if reaction_count > 0 else emoji
                        button_key = f"{unique_prefix}_reaction_{key}"
                        
                        if is_reacted:
                            if st.button(button_text, key=button_key, use_container_width=True, 
                                        help="リアクションを取り消す", type="primary"):
                                # リアクションを更新
                                update_reaction(report['id'], st.session_state["user"]["name"], key)
                                st.rerun()
                        else:
                            if st.button(button_text, key=button_key, use_container_width=True, 
                                        help="リアクションする"):
                                # リアクションを更新
                                update_reaction(report['id'], st.session_state["user"]["name"], key)
                                st.rerun()
                
                st.markdown('</div>', unsafe_allow_html=True)

                # コメント表示
                if report["comments"]:
                    st.markdown("#### コメント")
                    for comment in report["comments"]:
                        st.markdown(f"""
                        <div class="comment-text">
                        <strong>{comment['投稿者']}</strong> - {comment['投稿日時']}<br/>
                        {comment['内容']}
                        </div>
                        ---
                        """, unsafe_allow_html=True)
                
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
                
                # マイページからのみ編集・削除可能
                # 編集・削除ボタンは表示しない

def timeline():
    if "user" not in st.session_state or st.session_state["user"] is None:
        st.error("ログインしてください。")
        return

    st.title("タイムライン")

    # 検索部分を追加
    st.markdown("### 日報検索")
    col1, col2 = st.columns([4, 1])
    with col1:
        search_query = st.text_input("キーワード検索（実施内容、所感、投稿者名などで検索）", key="timeline_search_query")
    with col2:
        search_button = st.button("検索", key="timeline_search_button")
    
    # 検索結果がある場合は表示
    if search_button and search_query:
        from db_utils import search_reports
        search_results = search_reports(search_query)
        st.markdown("### 検索結果")
        display_search_results(search_results, tab_suffix="search")
        return  # 検索表示時は通常のタイムラインを表示しない
    
    st.markdown("### タイムライン")
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
    
    # 週選択機能の追加
    st.markdown("### 該当週を選択")
    
    # 週選択ヘルパー関数
    def generate_week_options_for_timeline():
        """選択可能な週のリストを生成（過去8週～今週）"""
        today = datetime.today().date()
        options = []
        # 今週も含めて過去8週を表示
        for i in range(-8, 1):
            start = today - timedelta(days=today.weekday()) + timedelta(weeks=i)
            end = start + timedelta(days=6)
            week_label = f"{start.month}/{start.day}（月）～{end.month}/{end.day}（日）"
            options.append((start, end, week_label))
        return options
    
    # 週選択UI
    week_options = generate_week_options_for_timeline()
    
    # セッション状態の初期化
    if 'timeline_selected_week' not in st.session_state:
        st.session_state.timeline_selected_week = 0  # 初期値としてインデックス0（今週）を設定
        
    selected_week_index = st.selectbox(
        "週を選択",
        options=range(len(week_options)),
        format_func=lambda i: week_options[i][2],
        index=st.session_state.timeline_selected_week,
        key="timeline_week_selector",
        label_visibility="collapsed"
    )
    
    # 選択した週を保存
    st.session_state.timeline_selected_week = selected_week_index
    
    # 選択した週の開始日と終了日
    selected_start_date, selected_end_date, _ = week_options[selected_week_index]
    
    # 時間範囲が指定されている場合は優先し、それ以外は週で絞り込み
    if time_range_param:
        # レポート読み込み - 時間範囲に基づく
        reports = load_reports(time_range=time_range_param)
    else:
        # 選択した週のレポートを読み込む
        reports = load_reports_by_date(selected_start_date, selected_end_date)
    
    display_reports(reports, tab_suffix="all")

def display_reports(reports, tab_suffix="all"):
    """日報表示関数"""
    if not reports:
        st.info("表示する日報はありません。")
        return

    for i, report in enumerate(reports):
        # タブ区別用サフィックスを追加して、ユニークなインデックスを生成
        unique_prefix = f"{st.session_state['page']}_{tab_suffix}_{i}_{report['id']}"
        
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
                st.markdown("**実施内容、所感など**")
                formatted_content = content.replace('\n', '<br>')
                st.markdown(f"<div class='content-text'>{formatted_content}</div>", unsafe_allow_html=True)
            
            # 今後のアクション（旧：翌日予定）
            if "今後のアクション" in report and report["今後のアクション"]:
                st.markdown("**今後のアクション**")
                formatted_action = report["今後のアクション"].replace('\n', '<br>')
                st.markdown(f"<div class='content-text'>{formatted_action}</div>", unsafe_allow_html=True)
            elif "翌日予定" in report and report["翌日予定"]:
                st.markdown("**今後のアクション**")
                formatted_action = report["翌日予定"].replace('\n', '<br>')
                st.markdown(f"<div class='content-text'>{formatted_action}</div>", unsafe_allow_html=True)
            
            # 画像の表示
            report_images = get_report_images(report['id'])
            if report_images:
                st.markdown("#### 添付画像")
                for i, img in enumerate(report_images):
                    st.markdown(f"**{img['file_name']}**")
                    st.markdown(f"<img src='data:{img['file_type']};base64,{img['image_data']}' style='max-width:100%;'>", unsafe_allow_html=True)
            
            st.caption(f"投稿日時: {report['投稿日時']}")
            
            # リアクションボタン - 👍のみに簡素化
            # リアクションの数を取得
            reaction_count = len(report['reactions'].get("thumbsup", []))
            
            # ユーザーがすでにリアクションしているか確認
            is_reacted = st.session_state["user"]["name"] in report['reactions'].get("thumbsup", [])
            button_label = f"👍 {reaction_count}" if reaction_count else "👍"
            
            # ボタンスタイルの設定
            button_style = "primary" if is_reacted else "secondary"
            
            # リアクションボタン
            if st.button(button_label, key=f"{unique_prefix}_reaction_thumbsup", type=button_style):
                if update_reaction(report['id'], st.session_state["user"]["name"], "thumbsup"):
                    st.rerun()

            # コメント表示
            if report["comments"]:
                st.markdown("#### コメント")
                for comment in report["comments"]:
                    st.markdown(f"""
                    <div class="comment-text">
                    <strong>{comment['投稿者']}</strong> - {comment['投稿日時']}<br/>
                    {comment['内容']}
                    </div>
                    ---
                    """, unsafe_allow_html=True)
            
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

            # マイページからのみ編集・削除可能
            # 編集・削除ボタンは表示しない

def post_report():
    if "user" not in st.session_state or st.session_state["user"] is None:
        st.error("ログインしてください。")
        return
        
    # 営業部のユーザーまたは管理者のみ日報投稿可能
    if "営業部" not in st.session_state["user"]["depart"] and not st.session_state["user"].get("admin", False):
        st.warning("日報投稿は営業部のメンバーまたは管理者のみ可能です。")
        return

    st.title("日報投稿")
    
    # 日報投稿の外側の部分: 検索機能
    # セッション状態の初期化
    if 'search_term' not in st.session_state:
        st.session_state.search_term = ""
    if 'search_results' not in st.session_state:
        st.session_state.search_results = []
    if 'selected_stores' not in st.session_state:
        st.session_state.selected_stores = []
    if 'custom_locations' not in st.session_state:
        st.session_state.custom_locations = ""
    
    # 訪問予定店の欄を表示（赤いマークで強調）
    st.markdown("### 📍 訪問予定店")
    
    # 選択された店舗があれば表示
    if st.session_state.selected_stores:
        with st.container(border=True):
            for selected in st.session_state.selected_stores:
                # 店舗情報の整形
                try:
                    code, name = selected.split(": ", 1)
                    if code:
                        st.markdown(f"<span style='color:red; font-weight:bold;'>🏢 {name}</span> (コード: {code})", unsafe_allow_html=True)
                    else:
                        st.markdown(f"<span style='color:red; font-weight:bold;'>🏢 {name}</span>", unsafe_allow_html=True)
                except ValueError:
                    # フォーマットが不正な場合
                    st.markdown(f"<span style='color:red; font-weight:bold;'>🏢 {selected}</span>", unsafe_allow_html=True)
            
            # クリアボタン
            if st.button("選択をクリア"):
                st.session_state.selected_stores = []
                st.session_state.custom_locations = ""
                st.rerun()
    else:
        # 選択がない場合のメッセージ
        st.info("店舗が選択されていません。以下から訪問場所を選択してください。")
    
    st.markdown("---")
    st.markdown("### 店舗選択")
    
    # タブを作成（フォームの外側）
    tab_options = ["予定から選択", "担当店舗から選択", "店舗を検索", "自由入力"]
    location_tab_index = st.radio("場所の選択方法:", tab_options, horizontal=True, label_visibility="collapsed")
    
    # ユーザーの担当店舗を取得
    user_stores = get_user_stores(st.session_state["user"]["code"])
    
    # タブの内容（フォームの外側）
    if location_tab_index == "予定から選択":
        # 直近の週間予定を取得
        from db_utils import load_weekly_schedules
        schedules = load_weekly_schedules()
        
        # 自分の予定だけをフィルタリング
        user_schedules = [s for s in schedules if s["投稿者"] == st.session_state["user"]["name"]]
        
        if not user_schedules:
            st.info("週間予定の登録がありません。まずは週間予定を登録してください。")
        else:
            # 期間ごとに分類
            schedule_periods = {}
            for schedule in user_schedules:
                period = schedule.get("期間", "")
                if period not in schedule_periods:
                    schedule_periods[period] = []
                schedule_periods[period].append(schedule)
            
            # 期間選択（新しい順）
            periods = list(schedule_periods.keys())
            periods.sort(reverse=True)  # 新しい期間が先頭に来るようにソート
            
            selected_period = st.selectbox(
                "期間を選択",
                options=periods,
                index=0 if periods else 0,
                key="schedule_period_select"
            )
            
            if selected_period:
                # 選択された期間の予定
                period_schedules = schedule_periods[selected_period]
                first_schedule = period_schedules[0]  # 同一期間なら最初のものを使用
                
                # 曜日ごとの店舗リスト
                weekdays = ["月曜日", "火曜日", "水曜日", "木曜日", "金曜日", "土曜日", "日曜日"]
                weekday_stores = []
                
                for weekday in weekdays:
                    # 各曜日の訪問店舗データを取得する際、キーに「_visited_stores」が付いていることを考慮
                    stores_key = f"{weekday}_visited_stores"
                    store_list = first_schedule.get(stores_key, [])
                    
                    if store_list:
                        for store in store_list:
                            store_key = f"{store.get('code', '')}: {store.get('name', '')}"
                            if store_key not in [s[0] for s in weekday_stores]:
                                weekday_stores.append((store_key, f"{weekday}の予定: {store.get('name', '')}"))
                
                if weekday_stores:
                    # 重複を除去して店舗リストとして表示
                    store_options = [s[0] for s in weekday_stores]
                    store_labels = [s[1] for s in weekday_stores]
                    
                    # selectboxに表示する選択肢とラベルのマッピング
                    store_dict = {option: label for option, label in zip(store_options, store_labels)}
                    
                    # デフォルト値設定
                    if st.session_state.selected_stores and st.session_state.selected_stores[0] in store_options:
                        default_index = store_options.index(st.session_state.selected_stores[0])
                    else:
                        default_index = 0
                    
                    # 店舗選択
                    selected = st.selectbox(
                        "予定から店舗を選択",
                        options=store_options,
                        index=default_index,
                        format_func=lambda x: store_dict[x],
                        key="schedule_stores_select"
                    )
                    
                    # 選択された店舗を記録（1つだけ）
                    if selected:
                        st.session_state.selected_stores = [selected]
                else:
                    st.info("この期間の予定には店舗が登録されていません。")
    
    elif location_tab_index == "店舗を検索":
        col1, col2 = st.columns([4, 1])
        with col1:
            search_term = st.text_input("店舗名または住所で検索", value=st.session_state.search_term)
        with col2:
            search_btn = st.button("検索", use_container_width=True)
        
        # 検索ボタンが押された場合のみ検索実行
        if search_btn:
            st.session_state.search_term = search_term
            if search_term:
                # 検索実行
                st.session_state.search_results = search_stores(search_term)
                if not st.session_state.search_results:
                    st.info("検索結果はありません。別のキーワードで試してください。")
            else:
                st.session_state.search_results = []
        
        # 検索結果を表示
        if st.session_state.search_results:
            search_store_options = [f"{store['code']}: {store['name']}" for store in st.session_state.search_results]
            # selectboxに変更（1つだけ選択可能）
            if st.session_state.selected_stores and st.session_state.selected_stores[0] in search_store_options:
                default_index = search_store_options.index(st.session_state.selected_stores[0])
            else:
                default_index = 0
            
            selected = st.selectbox(
                "検索結果から選択",
                options=search_store_options,
                index=default_index,
                key="search_stores_select"
            )
            
            # 選択された店舗を記録（1つだけ）
            if selected:
                st.session_state.selected_stores = [selected]
    
    # 担当店舗から選択タブ
    elif location_tab_index == "担当店舗から選択":
        if user_stores:
            store_options = [f"{store['code']}: {store['name']}" for store in user_stores]
            # マルチセレクトボックスに変更（複数選択可能）
            selected_stores = st.multiselect(
                "担当店舗から選択",
                options=store_options,
                default=st.session_state.selected_stores,
                key="assigned_stores_select"
            )
            
            # 選択された店舗を記録
            if selected_stores:
                st.session_state.selected_stores = selected_stores
        else:
            st.info("担当店舗がありません。")
    
    # 自由入力タブ
    elif location_tab_index == "自由入力":
        custom_location = st.text_input(
            "場所を自由に入力",
            value=st.session_state.custom_locations,
            placeholder="例: 〇〇商事（見込み客）または社内会議など",
            key="custom_locations_input"
        )
        
        if custom_location != st.session_state.custom_locations:
            st.session_state.custom_locations = custom_location
    
# この部分は削除（訪問予定店欄に統合したため）
    
    # 投稿フォーム - 店舗選択は完了した後に表示
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
        
        st.markdown("### 日報内容")
        business_content = st.text_area("実施内容、所感など", height=200)
        next_day_plan = st.text_area("今後のアクション", height=150)
        
        # 画像アップロード機能
        st.markdown("### 画像添付（任意）")
        uploaded_files = st.file_uploader("画像をアップロード", type=["jpg", "jpeg", "png"], accept_multiple_files=True)
        
        # 投稿ボタン
        submitted = st.form_submit_button("投稿する")
        
        if submitted:
            # 選択した店舗情報を保存
            stores_data = []
            
            # マルチセレクトから選択した店舗を処理
            for selected in st.session_state.selected_stores:
                try:
                    code, name = selected.split(": ", 1)
                    stores_data.append({"code": code, "name": name})
                except ValueError:
                    # フォーマットが不正な場合
                    stores_data.append({"code": "", "name": selected})
            
            # 自由入力から追加（単一の値として扱う）
            if st.session_state.custom_locations:
                if st.session_state.custom_locations.strip():
                    stores_data.append({"code": "", "name": st.session_state.custom_locations.strip()})
            
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
                
                # 選択をクリア
                st.session_state.selected_stores = []
                st.session_state.custom_locations = ""
                st.session_state.search_term = ""
                st.session_state.search_results = []
                
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
        
        # タブ選択
        tab_options = ["予定から選択", "担当店舗から選択", "店舗を検索", "自由入力"]
        location_tab_index = st.radio("場所の選択方法:", tab_options, horizontal=True, label_visibility="collapsed")
        
        stores_data = []
        
        # 予定から選択
        if location_tab_index == "予定から選択":
            # 直近の週間予定を取得
            from db_utils import load_weekly_schedules
            schedules = load_weekly_schedules()
            
            # 自分の予定だけをフィルタリング
            user_schedules = [s for s in schedules if s["投稿者"] == st.session_state["user"]["name"]]
            
            if not user_schedules:
                st.info("週間予定の登録がありません。まずは週間予定を登録してください。")
                # 既存の店舗データを保持
                if existing_stores:
                    stores_data = existing_stores
            else:
                # 期間ごとに分類
                schedule_periods = {}
                for schedule in user_schedules:
                    period = schedule.get("期間", "")
                    if period not in schedule_periods:
                        schedule_periods[period] = []
                    schedule_periods[period].append(schedule)
                
                # 期間選択（新しい順）
                periods = list(schedule_periods.keys())
                periods.sort(reverse=True)  # 新しい期間が先頭に来るようにソート
                
                selected_period = st.selectbox(
                    "期間を選択",
                    options=periods,
                    index=0 if periods else 0,
                    key="edit_schedule_period_select"
                )
                
                if selected_period:
                    # 選択された期間の予定
                    period_schedules = schedule_periods[selected_period]
                    first_schedule = period_schedules[0]  # 同一期間なら最初のものを使用
                    
                    # 曜日ごとの店舗リスト
                    weekdays = ["月曜日", "火曜日", "水曜日", "木曜日", "金曜日", "土曜日", "日曜日"]
                    weekday_stores = []
                    
                    for weekday in weekdays:
                        # 各曜日の訪問店舗データを取得する際、キーに「_visited_stores」が付いていることを考慮
                        stores_key = f"{weekday}_visited_stores"
                        store_list = first_schedule.get(stores_key, [])
                        
                        if store_list:
                            for store in store_list:
                                store_key = f"{store.get('code', '')}: {store.get('name', '')}"
                                if store_key not in [s[0] for s in weekday_stores]:
                                    weekday_stores.append((store_key, f"{weekday}の予定: {store.get('name', '')}"))
                    
                    if weekday_stores:
                        # 重複を除去して店舗リストとして表示
                        store_options = [s[0] for s in weekday_stores]
                        store_labels = [s[1] for s in weekday_stores]
                        
                        # selectboxに表示する選択肢とラベルのマッピング
                        store_dict = {option: label for option, label in zip(store_options, store_labels)}
                        
                        # デフォルト値設定（既存の値があれば優先）
                        if existing_store_ids and existing_store_ids[0] in store_options:
                            default_index = store_options.index(existing_store_ids[0])
                        else:
                            default_index = 0
                        
                        # 店舗選択
                        selected = st.selectbox(
                            "予定から店舗を選択",
                            options=store_options,
                            index=default_index,
                            format_func=lambda x: store_dict[x],
                            key="edit_schedule_stores_select"
                        )
                        
                        # 選択された店舗を保存
                        if selected:
                            try:
                                code, name = selected.split(": ", 1)
                                stores_data = [{"code": code, "name": name}]
                            except ValueError:
                                stores_data = [{"code": "", "name": selected}]
                    else:
                        st.info("この期間の予定には店舗が登録されていません。")
                        # 既存の店舗データを保持
                        if existing_stores:
                            stores_data = existing_stores
                
        # 担当店舗から選択
        elif location_tab_index == "担当店舗から選択":
            # 担当店舗をセレクトボックスで選択（1つだけ）
            store_options = [f"{store['code']}: {store['name']}" for store in user_stores]
            
            # 選択店舗のインデックスを設定
            if existing_store_ids and existing_store_ids[0] in store_options:
                default_index = store_options.index(existing_store_ids[0])
            else:
                default_index = 0
            
            if store_options:
                selected_store = st.selectbox(
                    "担当店舗から選択",
                    options=store_options,
                    index=default_index,
                    key="edit_assigned_stores_select"
                )
                
                # 選択した店舗情報を保存
                code, name = selected_store.split(": ", 1)
                stores_data = [{"code": code, "name": name}]
            else:
                # 店舗選択肢がない場合
                st.info("担当店舗がありません。")
                # 既存の店舗データを保持
                if existing_stores:
                    stores_data = existing_stores
        
        # 店舗を検索
        elif location_tab_index == "店舗を検索":
            col1, col2 = st.columns([4, 1])
            with col1:
                search_term = st.text_input("店舗名または住所で検索", key="edit_search_term")
            with col2:
                search_btn = st.button("検索", key="edit_search_btn")
            
            search_results = []
            if search_btn and search_term:
                # 検索実行
                search_results = search_stores(search_term)
                if not search_results:
                    st.info("検索結果はありません。別のキーワードで試してください。")
            
            # 検索結果を表示
            if search_results:
                search_store_options = [f"{store['code']}: {store['name']}" for store in search_results]
                
                # 既存選択を反映
                if existing_store_ids and existing_store_ids[0] in search_store_options:
                    default_index = search_store_options.index(existing_store_ids[0])
                else:
                    default_index = 0
                
                selected = st.selectbox(
                    "検索結果から選択",
                    options=search_store_options,
                    index=default_index,
                    key="edit_search_stores_select"
                )
                
                # 選択された店舗を保存
                if selected:
                    try:
                        code, name = selected.split(": ", 1)
                        stores_data = [{"code": code, "name": name}]
                    except ValueError:
                        stores_data = [{"code": "", "name": selected}]
            else:
                # 既存の店舗データを保持
                if existing_stores:
                    stores_data = existing_stores
        
        # 自由入力
        elif location_tab_index == "自由入力":
            # 既存値がある場合は自由入力フィールドにデフォルト表示
            default_custom = ""
            if existing_stores and not existing_stores[0].get("code"):
                default_custom = existing_stores[0].get("name", "")
                
            custom_location = st.text_input(
                "場所を自由に入力",
                value=default_custom,
                placeholder="例: 〇〇商事（見込み客）または社内会議など",
                key="edit_custom_locations_input"
            )
            
            if custom_location and custom_location.strip():
                stores_data = [{"code": "", "name": custom_location.strip()}]
            elif existing_stores:
                # 入力がなければ既存値を保持
                stores_data = existing_stores
        
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
        try:
            # 通知カードのスタイル
            card_style = "read-notification" if notification.get("is_read", False) else "unread-notification"
            
            # 通知日時の整形
            created_at = notification.get("created_at", datetime.now())
            if isinstance(created_at, str):
                try:
                    created_at = datetime.strptime(created_at, "%Y-%m-%d %H:%M:%S")
                except:
                    pass
            
            if isinstance(created_at, datetime):
                formatted_time = created_at.strftime("%Y-%m-%d %H:%M:%S")
            else:
                formatted_time = str(created_at)
            
            # 一意のキーを生成（通知IDとインデックスの組み合わせ）
            notification_id = notification.get("id", f"unknown_{i}")
            unique_prefix = f"notification_{notification_id}_{i}"
            
            # 通知カード
            with st.container():
                st.markdown(f"<div class='{card_style}'>", unsafe_allow_html=True)
                
                # 通知内容
                st.markdown(notification.get("content", "通知内容が表示できません"))
                st.caption(f"受信日時: {formatted_time}")
                
                # リンクボタン（該当する場合）
                if notification.get("link_type") and notification.get("link_id"):
                    if notification.get("link_type") == "report":
                        if st.button(f"日報を確認する", key=f"{unique_prefix}_report_link"):
                            # 日報IDをセッションに保存して遷移（ページは"タイムライン"に修正）
                            st.session_state["view_report_id"] = notification.get("link_id")
                            # タイムラインに戻ってから該当の日報を表示
                            switch_page("タイムライン")
                            st.rerun()
                    elif notification.get("link_type") == "weekly_schedule":
                        if st.button(f"週間予定を確認する", key=f"{unique_prefix}_schedule_link"):
                            # 週間予定への遷移処理
                            st.session_state["view_schedule_id"] = notification.get("link_id")
                            # 正しいページ名に修正
                            switch_page("週間予定")
                            st.rerun()
                
                # 既読ボタン（未読の場合のみ表示）
                if not notification.get("is_read", False):
                    if st.button("既読にする", key=f"{unique_prefix}_read_button"):
                        if notification_id and notification_id != f"unknown_{i}" and mark_as_read_function(notification_id):
                            st.success("既読にしました！")
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.error("既読設定に失敗しました。")
                
                st.markdown("</div>", unsafe_allow_html=True)
                st.markdown("<br>", unsafe_allow_html=True)
        except Exception as e:
            st.error(f"通知の表示中にエラーが発生しました: {e}")
            continue

def my_page():
    if "user" not in st.session_state or st.session_state["user"] is None:
        st.error("ログインしてください。")
        return

    # pandas をインポート
    import pandas as pd

    st.title("マイページ")

    # ユーザー情報取得
    user = st.session_state["user"]
    is_admin = user.get("admin", False)
    
    # 管理者向け機能: ユーザー選択
    selected_user_name = user["name"]
    selected_user_code = user["code"]
    
    # タブを設定（投稿詳細と訪問詳細の位置を交換）
    tab1, tab2, tab3 = st.tabs(["プロフィール・統計", "投稿詳細", "週間予定投稿履歴"])

    with tab1:
        # 管理者向け機能: ユーザー選択
        if is_admin:
            st.markdown("### 管理者ビュー")
            
            # ユーザーデータを取得
            try:
                with open("data/users_data.json", "r", encoding="utf-8") as f:
                    users_json = json.load(f)
                
                # 選択用のユーザー名リスト
                user_options = []
                user_code_map = {}  # ユーザー名からコードへのマッピング
                
                for u in users_json:
                    name = u.get("name")
                    code = u.get("code")
                    if name and code:
                        user_options.append(name)
                        user_code_map[name] = code
                
                # ユーザーを選択
                selected_user_name = st.selectbox(
                    "ユーザー選択",
                    options=user_options,
                    index=user_options.index(user["name"]) if user["name"] in user_options else 0
                )
                
                # 選択したユーザーの社員コードを取得
                selected_user_code = user_code_map.get(selected_user_name)
                
                # 選択したユーザーの部署情報を取得
                selected_user_departments = None
                for u in users_json:
                    if u.get("name") == selected_user_name:
                        selected_user_departments = u.get("depart", [])
                        break
                
            except Exception as e:
                st.error(f"ユーザーデータの読み込みに失敗しました: {e}")
                selected_user_name = user["name"]
                selected_user_code = user["code"]
                selected_user_departments = user.get("depart", [])
    
        # プロフィール情報
        st.markdown("### プロフィール")
        st.markdown(f"**名前**: {selected_user_name}")
        
        # 社員コードと所属部署の表示
        if selected_user_name == user["name"]:
            # 自分自身の場合
            st.markdown(f"**社員コード**: {user['code']}")
            st.markdown(f"**所属部署**: {', '.join(user['depart'])}")
        else:
            # 他のユーザーの場合
            if selected_user_code:
                st.markdown(f"**社員コード**: {selected_user_code}")
            if selected_user_departments:
                st.markdown(f"**所属部署**: {', '.join(selected_user_departments)}")
        
        # 期間選択（旧・店舗訪問統計のヘッダを期間に変更）
        st.markdown("### 期間")
        current_date = datetime.now()
        col1, col2 = st.columns(2)
        with col1:
            year = st.selectbox("年", options=range(current_date.year-2, current_date.year+1), index=2)
        with col2:
            month = st.selectbox("月", options=range(1, 13), index=current_date.month-1)
        
        # 日報投稿数サマリー
        st.markdown("### 日報投稿数")
        from db_utils import get_user_monthly_report_summary, load_reports_by_date
        # ユーザーコードがある場合はコードで、ない場合はユーザー名で検索
        report_summary = get_user_monthly_report_summary(
            user_code=selected_user_code,
            user_name=selected_user_name
        )
        
        if report_summary:
            # 最近6ヶ月分のデータを表示
            months = list(report_summary.keys())[:6]
            counts = [report_summary[m] for m in months]
            
            # 月表示を "YYYY-MM" から "YYYY年MM月" に変換
            formatted_months = []
            month_year_dict = {}  # 元の形式と表示形式のマッピング用
            for m in months:
                year_val, month_val = m.split("-")
                formatted_month = f"{year_val}年{month_val}月"
                formatted_months.append(formatted_month)
                month_year_dict[formatted_month] = m
            
            # 表形式で表示
            report_data = []
            for i, month_name in enumerate(formatted_months):
                report_data.append({
                    "月": month_name,
                    "投稿数": f"{max(1, counts[i])}件"
                })
            df_reports = pd.DataFrame(report_data)
            
            # Streamlit専用のデータフレーム表示
            st.dataframe(
                df_reports,
                hide_index=True,
                use_container_width=True
            )
        else:
            st.info("日報投稿記録がありません。")

        # 選択された月と年の投稿詳細を取得・表示
        year_month = f"{year}-{month:02d}"
        
        # 月の初日と末日
        start_date = f"{year}-{month:02d}-01"
        last_day = calendar.monthrange(int(year), int(month))[1]
        end_date = f"{year}-{month:02d}-{last_day}"
        
        # 期間内の報告を取得
        reports = load_reports_by_date(start_date, end_date)
        
        # ユーザーのレポートだけをフィルタリング
        user_reports = [r for r in reports if r["投稿者"] == selected_user_name or 
                       (r.get("user_code") == selected_user_code and selected_user_code is not None)]
        
        # 投稿詳細を表示
        st.markdown(f"#### {year}年{month}月の投稿詳細 ({len(user_reports)}件)")
        
        if user_reports:
            # テーブル形式でサマリーを表示
            summary_data = []
            for report in user_reports:
                visited_stores = report.get('visited_stores', [])
                store_names = [s.get('name', '無名') for s in visited_stores]
                store_text = ", ".join(store_names) if store_names else "記録なし"
                
                summary_data.append({
                    "日付": report['日付'],
                    "場所": store_text[:20] + ('...' if len(store_text) > 20 else ''),
                    "内容": report['実施内容'][:30] + ('...' if len(report['実施内容']) > 30 else ''),
                    "今後のアクション": report['今後のアクション'][:30] + ('...' if len(report['今後のアクション']) > 30 else ''),
                    "コメント数": len(report.get('comments', []))
                })
            
            # テーブル表示
            if summary_data:
                # インデックスを非表示にしてデータフレーム表示
                summary_df = pd.DataFrame(summary_data)
                
                # Streamlit専用のデータフレーム表示
                st.dataframe(
                    summary_df,
                    hide_index=True,
                    use_container_width=True
                )
        else:
            st.info(f"{year}年{month}月の投稿はありません。")
        
        # 訪問詳細をプロフィール・統計タブの一番下に表示
        st.markdown(f"#### {year}年{month}月の訪問履歴")
        
        # 統計データ取得
        from db_utils import get_store_visit_stats
        # 選択したユーザーの店舗訪問統計を取得 - コード情報がある場合はそれを優先
        if selected_user_code:
            stats = get_store_visit_stats(
                user_code=selected_user_code, 
                year=year, 
                month=month
            )
        else:
            # コード情報がない場合はユーザー名で検索
            stats = get_store_visit_stats(
                user_name=selected_user_name,
                year=year, 
                month=month
            )
            
        if stats:
            # Excelエクスポート用のボタン
            if st.button("Excelでダウンロード", key="store_visits_excel"):
                # stats形式を汎用エクスポート関数用に変換
                visits_data = {selected_user_name: stats}
                download_link = excel_utils.export_store_visits_to_excel(
                    visits_data, 
                    f"{selected_user_name}_{year}年{month}月_店舗訪問履歴.xlsx"
                )
                st.markdown(download_link, unsafe_allow_html=True)
                # デバッグ情報を表示
                st.info("ダウンロードリンクが表示されない場合は、ページを再読み込みしてからもう一度試してください。")
            
            st.markdown("---")
            
            # 詳細データをテーブルで表示
            table_data = []
            for s in stats:
                # 日付ごとの訪問内容を整形
                visit_details = []
                for detail in s.get("details", []):
                    date = detail["date"]
                    content = detail.get("content", "")
                    if content:
                        visit_details.append(f"{date}: {content}")
                    else:
                        visit_details.append(date)
                
                # 訪問内容をまとめる - st.tableで表示するので改行はそのまま
                visit_info = "\n".join(visit_details)
                
                table_data.append({
                    "店舗コード": s["code"],
                    "店舗名": s["name"],
                    "訪問回数": max(1, s["count"]),
                    "訪問日と内容": visit_info
                })
            
            # データフレームを作成
            table_df = pd.DataFrame(table_data)
            
            # インデックスをリセット
            table_df = table_df.reset_index(drop=True)
            
            # Streamlit専用の表形式表示
            st.dataframe(
                table_df,
                hide_index=True,
                use_container_width=True,
                column_config={
                    "店舗コード": st.column_config.TextColumn("店舗コード"),
                    "店舗名": st.column_config.TextColumn("店舗名"),
                    "訪問回数": st.column_config.NumberColumn("訪問回数"),
                    "訪問日と内容": st.column_config.TextColumn("訪問日と内容")
                }
            )
        else:
            st.info(f"{year}年{month}月の訪問記録はありません。")

    with tab2:
        # 新しいセクション：日報履歴
        st.markdown("### 日報履歴")
        
        # 管理者でない場合または自分自身のページを見ている場合のみ投稿一覧を表示
        if not is_admin or selected_user_name == user["name"]:
            st.markdown("#### 自分の投稿")
            
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
                    # Excelエクスポート用のボタン
                    if st.button("Excelでダウンロード", key="my_reports_excel"):
                        download_link = excel_utils.export_to_excel(my_reports, f"マイ日報_{user['name']}.xlsx", include_content=True)
                        st.markdown(download_link, unsafe_allow_html=True)
                    
                    st.markdown("---")
                    
                    # 専用の表示関数を作成せず、my_reportsを直接表示
                    for i, report in enumerate(my_reports):
                        # ユニークなプレフィックス
                        unique_prefix = f"mypage_reports_{i}_{report['id']}"
                        
                        # 日報日付から曜日を取得
                        try:
                            report_date = datetime.strptime(report["日付"], "%Y-%m-%d")
                            weekday = ["月", "火", "水", "木", "金", "土", "日"][report_date.weekday()]
                            formatted_date = f"{report_date.month}月{report_date.day}日（{weekday}）"
                        except:
                            formatted_date = report["日付"]

                        # 日報表示カード
                        with st.expander(f"{formatted_date} ({report['所属部署']})", expanded=(i==0)):
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
                                st.markdown("**実施内容、所感など**")
                                formatted_content = content.replace('\n', '<br>')
                                st.markdown(f"<div class='content-text'>{formatted_content}</div>", unsafe_allow_html=True)
                            
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
                                for img_idx, img in enumerate(report_images):
                                    st.markdown(f"**{img['file_name']}**")
                                    st.markdown(f"<img src='data:{img['file_type']};base64,{img['image_data']}' style='max-width:100%;'>", unsafe_allow_html=True)
                            
                            st.caption(f"投稿日時: {report['投稿日時']}")
                            
                            # コメント表示
                            if report.get("comments", []):
                                st.markdown("#### コメント")
                                for comment in report["comments"]:
                                    st.markdown(f"""
                                    <div class="comment-text">
                                    <strong>{comment['投稿者']}</strong> - {comment['投稿日時']}<br/>
                                    {comment['内容']}
                                    </div>
                                    ---
                                    """, unsafe_allow_html=True)
                            
                            # 編集・削除ボタン
                            col1, col2 = st.columns(2)
                            with col1:
                                if st.button("編集", key=f"{unique_prefix}_edit"):
                                    st.session_state["edit_report_id"] = report["id"]
                                    switch_page("日報編集")
                                    st.rerun()
                            with col2:
                                if st.button("削除", key=f"{unique_prefix}_delete"):
                                    from db_utils import delete_report
                                    if delete_report(report["id"]):
                                        st.success("日報を削除しました！")
                                        time.sleep(1)
                                        st.rerun()
                                    else:
                                        st.error("日報の削除に失敗しました。")
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
                        # 日付が文字列かdatetime型かをチェック
                        if isinstance(report["投稿日時"], str):
                            post_time = datetime.strptime(report["投稿日時"], "%Y-%m-%d %H:%M:%S")
                        else:
                            # 既にdatetime型の場合はそのまま使用
                            post_time = report["投稿日時"]
                        
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
        # 週間予定投稿履歴
        st.markdown("### 自分の週間予定")
            
        # 時間範囲選択
        time_range = st.radio(
            "表示期間",
            ["1ヶ月以内", "3ヶ月以内", "すべて表示"],
            horizontal=True,
            index=1
        )
            
        # 週間予定取得
        from db_utils import load_weekly_schedules, save_weekly_schedule_comment, delete_report
        weekly_schedules = load_weekly_schedules()
        
        # 自分の週間予定だけをフィルタリング
        my_schedules = [s for s in weekly_schedules if s.get("投稿者") == user["name"]]
            
        if not my_schedules:
            st.info("表示できる週間予定はありません。")
        else:
            # 時間範囲に基づいてフィルタリング
            now = datetime.now()
            filtered_schedules = []
            
            for schedule in my_schedules:
                # 投稿日時を日付オブジェクトに変換
                post_time_str = schedule.get('投稿日時', '')
                if isinstance(post_time_str, str) and post_time_str:
                    try:
                        post_time = datetime.strptime(post_time_str, "%Y-%m-%d %H:%M:%S")
                        time_diff = now - post_time
                        
                        if time_range == "1ヶ月以内" and time_diff.days <= 30:
                            filtered_schedules.append(schedule)
                        elif time_range == "3ヶ月以内" and time_diff.days <= 90:
                            filtered_schedules.append(schedule)
                        elif time_range == "すべて表示":
                            filtered_schedules.append(schedule)
                    except:
                        # 日付変換エラーの場合はすべての範囲に含める
                        filtered_schedules.append(schedule)
                else:
                    # 投稿日時がない場合もすべての範囲に含める
                    filtered_schedules.append(schedule)
                
            if not filtered_schedules:
                st.info(f"選択した期間内の週間予定はありません。")
            else:
                # Excelエクスポート用のボタン
                if st.button("Excelでダウンロード", key="my_schedules_excel"):
                    download_link = excel_utils.export_weekly_schedules_to_excel(filtered_schedules, f"マイ週間予定_{user['name']}.xlsx")
                    st.markdown(download_link, unsafe_allow_html=True)
                
                st.markdown("---")
            
            # 週間予定を表示
            for i, schedule in enumerate(filtered_schedules):
                # 投稿日時が文字列かdatetime型かチェック
                post_time_str = schedule.get('投稿日時', 'N/A')
                if isinstance(post_time_str, datetime):
                    post_time_str = post_time_str.strftime("%Y-%m-%d %H:%M:%S")
                    
                # 開始日と終了日を表示タイトルに使用
                start_date = schedule.get('開始日', '不明日')
                end_date = schedule.get('終了日', '不明日') 
                
                # スケジュール期間を表示タイトルに使用
                period = schedule.get('期間', '')
                if period:
                    # 期間フィールドがある場合はそれを使用
                    expander_title = f"期間: {period} （投稿日: {post_time_str}）"
                elif start_date and end_date and isinstance(start_date, str) and isinstance(end_date, str):
                    # 開始日と終了日から期間を生成
                    expander_title = f"期間: {start_date} 〜 {end_date} （投稿日: {post_time_str}）"
                else:
                    # どちらもない場合
                    expander_title = f"期間: （投稿日: {post_time_str}）"
                        
                with st.expander(expander_title, expanded=(i==0)):
                    # 編集ボタンを追加
                    col1, col2, col3 = st.columns([4, 1, 1])
                    with col1:
                        st.markdown(f"**投稿者**: {schedule.get('投稿者', '不明')}")
                    with col2:
                        # 編集ボタン
                        edit_button_key = f"mypage_edit_schedule_{schedule.get('id', 'unknown')}"
                        if st.button("編集", key=edit_button_key):
                            # 編集対象のスケジュールをセッションに保存
                            st.session_state["editing_schedule"] = schedule
                            # 週間予定ページに遷移
                            switch_page("週間予定投稿")
                            st.rerun()
                    with col3:
                        # 削除ボタン
                        delete_button_key = f"mypage_delete_schedule_{schedule.get('id', 'unknown')}"
                        if st.button("削除", key=delete_button_key):
                            schedule_id = schedule.get('id')
                            if schedule_id:
                                # 確認用のセッション変数を設定
                                if "confirming_delete_schedule" not in st.session_state:
                                    st.session_state["confirming_delete_schedule"] = {}
                                
                                if st.session_state["confirming_delete_schedule"].get(schedule_id):
                                    # 確認済み - 実際に削除
                                    try:
                                        # 週間予定削除のためにDB削除関数を呼び出す
                                        from db_utils import delete_report
                                        if delete_report(schedule_id):
                                            st.success("週間予定を削除しました！")
                                            # 確認状態をリセット
                                            st.session_state["confirming_delete_schedule"][schedule_id] = False
                                            # セッションから削除したデータを除外
                                            if "filtered_schedules" in st.session_state:
                                                st.session_state["filtered_schedules"] = [s for s in st.session_state["filtered_schedules"] if s.get("id") != schedule_id]
                                            time.sleep(1)
                                            st.rerun()
                                        else:
                                            st.error("週間予定の削除に失敗しました。")
                                    except Exception as e:
                                        st.error(f"削除エラー: {str(e)}")
                                else:
                                    # 確認
                                    st.session_state["confirming_delete_schedule"][schedule_id] = True
                                    st.warning("本当に削除しますか？もう一度「削除」ボタンをクリックすると削除されます。")
                            else:
                                st.error("IDが不明な週間予定は削除できません。")
                        
                    # 開始日と終了日の情報表示は削除（既にexpanderのタイトルに表示されているため）
                    
                    # 曜日ごとの表をDataFrameで表示
                    weekdays = ["月曜日", "火曜日", "水曜日", "木曜日", "金曜日", "土曜日", "日曜日"]
                    japanese_weekdays = ["月", "火", "水", "木", "金", "土", "日"]
                    
                    try:
                        # 開始日から各曜日の日付を計算
                        if isinstance(schedule.get('開始日'), str):
                            start_dt = datetime.strptime(schedule['開始日'], "%Y-%m-%d")
                            weekday_labels = {}
                            
                            # 各曜日の日付を計算
                            for i, day in enumerate(weekdays):
                                day_date = start_dt + timedelta(days=i)
                                weekday_labels[day] = f"{day_date.month}/{day_date.day} ({japanese_weekdays[i]})"
                            
                            # 日ごとのデータを作成（行ごとに1日のスケジュール）
                            data = []
                            
                            for day in weekdays:
                                # 訪問店舗情報
                                visited_stores_key = f"{day}_visited_stores"
                                visited_stores = schedule.get(visited_stores_key, [])
                                store_names = [store["name"] for store in visited_stores] if visited_stores else []
                                store_text = ", ".join(store_names) if store_names else "なし"
                                
                                # 日ごとの行データ
                                row = {
                                    "日付": weekday_labels[day],
                                    "予定": schedule[day] if day in schedule and schedule[day] else "予定なし",
                                    "訪問店舗": store_text
                                }
                                data.append(row)
                            
                            # DataFrameに変換
                            df = pd.DataFrame(data)
                            
                            # テーブル表示（インデックス列なし）
                            st.write(df.to_html(index=False), unsafe_allow_html=True)
                        else:
                            # 旧形式の場合はテキスト表示
                            for day in weekdays:
                                if day in schedule and schedule[day]:
                                    st.markdown(f"**{day}**:")
                                    st.markdown(schedule[day])
                                    
                                    # その日の訪問予定店舗
                                    visited_stores_key = f"{day}_visited_stores"
                                    if visited_stores_key in schedule and schedule[visited_stores_key]:
                                        stores = schedule[visited_stores_key]
                                        store_names = [store["name"] for store in stores if "name" in store]
                                        if store_names:
                                            st.markdown(f"**訪問店舗**: {', '.join(store_names)}")
                    except Exception as e:
                        # 日付変換エラーの場合は、通常表示を使用
                        st.error(f"日程表示エラー: {e}")
                        for day in weekdays:
                            if day in schedule and schedule[day]:
                                st.markdown(f"**{day}**:")
                                st.markdown(schedule[day])
                    
                    # コメント表示
                    comments_key = None
                    for key in ["コメント", "comments"]:
                        if key in schedule and schedule[key]:
                            comments_key = key
                            break
                            
                    if comments_key:
                        st.markdown("#### コメント")
                        for comment in schedule[comments_key]:
                            name_key = None
                            for key in ["投稿者", "name"]:
                                if key in comment:
                                    name_key = key
                                    break
                                    
                            time_key = None
                            for key in ["投稿日時", "time"]:
                                if key in comment:
                                    time_key = key
                                    break
                                    
                            content_key = None
                            for key in ["内容", "text"]:
                                if key in comment:
                                    content_key = key
                                    break
                            
                            if name_key and time_key and content_key:
                                st.markdown(f"""
                                <div class="comment-text">
                                <strong>{comment[name_key]}</strong> - {comment[time_key]}<br/>
                                {comment[content_key]}
                                </div>
                                ---
                                """, unsafe_allow_html=True)
                            
                    # コメント入力フォーム
                    with st.form(key=f"mypage_schedule_comment_{schedule.get('id', 'unknown')}"):
                        comment_text = st.text_area("コメントを入力", key=f"mypage_comment_text_{schedule.get('id', 'unknown')}")
                        submit_button = st.form_submit_button("コメントする")
                        
                        if submit_button and comment_text.strip():
                            comment = {
                                "投稿者": st.session_state["user"]["name"],
                                "内容": comment_text,
                            }
                            from db_utils import save_weekly_schedule_comment
                            if save_weekly_schedule_comment(schedule["id"], comment):
                                st.success("コメントを投稿しました！")
                                time.sleep(1)
                                st.rerun()
                            else:
                                st.error("コメントの投稿に失敗しました。")

                        

            # 週間予定がない場合の表示
            if not filtered_schedules:
                st.info("表示できる週間予定はありません。")
            elif len(filtered_schedules) == 0:
                st.info("表示できる週間予定はありません。")

def export_data():
    if "user" not in st.session_state or st.session_state["user"] is None:
        st.error("ログインしてください。")
        return

    # 管理者権限チェック
    if not st.session_state["user"].get("admin", False):
        st.error("データエクスポートには管理者権限が必要です。")
        return

    st.title("📊 データエクスポート")
    st.info("各種データをExcel形式でエクスポートできます。")

    tab1, tab2, tab3, tab4 = st.tabs(["日報データ", "週間予定データ", "投稿統計", "店舗訪問データ"])

    with tab1:
        st.markdown("### 日報データのエクスポート")
        
        # 日付操作用にdatetimeをインポート
        from datetime import date, timedelta
        
        # 期間指定
        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input("開始日", value=date.today() - timedelta(days=30), key="report_start_date")
        with col2:
            end_date = st.date_input("終了日", value=date.today(), key="report_end_date")
        
        # 営業部のデータのみ取得するように固定
        department = "営業部"
        
        if st.button("日報データをエクスポート", type="primary"):
            with st.spinner("データを取得しています..."):
                # 条件に合った日報データを取得
                from db_utils import load_reports_by_date
                
                # 営業部のみに固定
                dept = department
                
                # データ取得
                reports = load_reports(depart=dept)
                
                # 日付フィルタリング
                start_date_str = start_date.strftime("%Y-%m-%d")
                end_date_str = end_date.strftime("%Y-%m-%d")
                
                # 日付型と文字列型を正しく処理
                filtered_reports = []
                for r in reports:
                    if isinstance(r["日付"], str):
                        # 日付が文字列の場合
                        if start_date_str <= r["日付"] <= end_date_str:
                            filtered_reports.append(r)
                    else:
                        # 日付がdatetime.date型の場合
                        date_str = r["日付"].strftime("%Y-%m-%d")
                        if start_date_str <= date_str <= end_date_str:
                            filtered_reports.append(r)
                
                if filtered_reports:
                    # 日付範囲をファイル名に含める
                    excel_filename = f"日報データ_{start_date_str}_{end_date_str}.xlsx"
                    # 「内容」と「今後のアクション」列を含める
                    download_link = excel_utils.export_to_excel(filtered_reports, excel_filename, include_content=True)
                    st.markdown(download_link, unsafe_allow_html=True)
                else:
                    st.warning("指定された条件に一致する日報データがありません。")

    with tab2:
        st.markdown("### 週間予定データのエクスポート")
        
        # 日付操作用にdatetimeをインポート (tab1でインポート済みだが安全のため再度インポート)
        from datetime import date, timedelta
        
        # 期間指定
        col1, col2 = st.columns(2)
        with col1:
            start_month = st.date_input("開始月", value=date.today().replace(day=1) - timedelta(days=30), key="schedule_start_date")
        with col2:
            end_month = st.date_input("終了月", value=date.today().replace(day=28), key="schedule_end_date")
        
        # エクスポートボタン
        if st.button("週間予定データをエクスポート", type="primary"):
            with st.spinner("データを取得しています..."):
                # 週間予定データを取得
                schedules = load_weekly_schedules()
                
                # 期間でフィルタリング
                start_date_str = start_month.strftime("%Y-%m-%d")
                end_date_str = end_month.strftime("%Y-%m-%d")
                
                # 日付フィルタリング（文字列または日付型を考慮）
                filtered_schedules = []
                for s in schedules:
                    # 文字列型の場合
                    if isinstance(s["開始日"], str) and start_date_str <= s["開始日"] <= end_date_str:
                        filtered_schedules.append(s)
                    # 日付型の場合
                    elif hasattr(s["開始日"], "strftime"):
                        s_date_str = s["開始日"].strftime("%Y-%m-%d")
                        if start_date_str <= s_date_str <= end_date_str:
                            filtered_schedules.append(s)
                
                if filtered_schedules:
                    # 日付範囲をファイル名に含める
                    excel_filename = f"週間予定データ_{start_date_str}_{end_date_str}.xlsx"
                    # データをエクスポートしてダウンロードリンクを直接表示
                    download_link = excel_utils.export_weekly_schedules_to_excel(filtered_schedules, excel_filename)
                    st.markdown(download_link, unsafe_allow_html=True)
                else:
                    st.warning("指定された期間に一致する週間予定データがありません。")

    with tab3:
        st.markdown("### 投稿統計データ")
        
        # 日付操作用にdatetimeをインポート (安全のため再度インポート)
        from datetime import date, timedelta
        
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
                    
                    # 投稿数にリンクを追加
                    df_display = df.copy()
                    # 0値を1に変更
                    df_display["投稿数"] = df_display["投稿数"].apply(lambda x: f"{max(1, x)}件")
                    
                    # Streamlit専用のデータフレーム表示
                    st.dataframe(
                        df_display,
                        hide_index=True,
                        use_container_width=True
                    )
                    
                    # ユーザー選択して投稿詳細表示
                    if len(df) > 0:
                        selected_user = st.selectbox(
                            "ユーザーを選択して投稿詳細を表示",
                            options=df["名前"].tolist(),
                            key="monthly_user_select"
                        )
                        
                        if selected_user and st.button("投稿詳細を表示"):
                            # 選択したユーザーと月のデータを取得
                            year_month_parts = year_month.split("-")
                            year_val = int(year_month_parts[0])
                            month_val = int(year_month_parts[1])
                            
                            # 月の初日と末日
                            import calendar
                            start_date = f"{year_val}-{month_val:02d}-01"
                            last_day = calendar.monthrange(year_val, month_val)[1]
                            end_date = f"{year_val}-{month_val:02d}-{last_day}"
                            
                            # 期間内の報告を取得
                            from db_utils import load_reports_by_date
                            reports = load_reports_by_date(start_date, end_date)
                            
                            # 選択したユーザーのレポートだけをフィルタリング
                            user_reports = [r for r in reports if r["投稿者"] == selected_user]
                            
                            if user_reports:
                                st.markdown(f"#### {selected_user}の{year}年{month}月の投稿詳細 ({len(user_reports)}件)")
                                
                                # サマリーテーブル表示
                                summary_data = []
                                for report in user_reports:
                                    visited_stores = report.get('visited_stores', [])
                                    store_names = [s.get('name', '無名') for s in visited_stores]
                                    store_text = ", ".join(store_names) if store_names else "記録なし"
                                    
                                    summary_data.append({
                                        "日付": report['日付'],
                                        "場所": store_text[:20] + ('...' if len(store_text) > 20 else ''),
                                        "内容": report['実施内容'][:30] + ('...' if len(report['実施内容']) > 30 else ''),
                                        "今後のアクション": report['今後のアクション'][:30] + ('...' if len(report['今後のアクション']) > 30 else ''),
                                        "コメント数": len(report.get('comments', []))
                                    })
                                
                                # テーブル表示
                                if summary_data:
                                    # インデックスを非表示にしてデータフレーム表示
                                    summary_df = pd.DataFrame(summary_data)
                                    
                                    # Streamlit専用のデータフレーム表示
                                    st.dataframe(
                                        summary_df,
                                        hide_index=True,
                                        use_container_width=True
                                    )
                            else:
                                st.info(f"{selected_user}の{year}年{month}月の投稿はありません。")
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
                        # インデックスなしで表示（Streamlit専用の表示機能）
                        pivot_display = pivot_df[["名前"] + existing_cols]
                        
                        # Streamlit専用のデータフレーム表示
                        st.dataframe(
                            pivot_display,
                            hide_index=True,
                            use_container_width=True
                        )
                        
                        # 合計を計算して追加
                        pivot_df["合計"] = pivot_df[existing_cols].sum(axis=1)
                        st.markdown("#### 年間投稿数（降順）")
                        
                        # 降順でソート
                        sorted_df = pivot_df.sort_values("合計", ascending=False)
                        
                        # 表示用にデータフレームを整形 (「件」を追加)
                        sorted_df_display = sorted_df.copy()
                        # 0値を1に変更
                        sorted_df_display["合計"] = sorted_df_display["合計"].apply(lambda x: f"{max(1, x)}件")
                        for col in existing_cols:
                            sorted_df_display[col] = sorted_df_display[col].apply(lambda x: f"{max(1, x)}件" if not pd.isna(x) else "")
                        
                        # Streamlit専用のデータフレーム表示（インデックスなし）
                        st.dataframe(
                            sorted_df_display,
                            hide_index=True,
                            use_container_width=True
                        )
                        
                        # ユーザー選択して年間の投稿詳細表示
                        if len(sorted_df) > 0:
                            selected_user_year = st.selectbox(
                                f"ユーザーを選択して{year}年の投稿詳細を表示",
                                options=sorted_df["名前"].tolist(),
                                key="yearly_user_select"
                            )
                            
                            if selected_user_year and st.button("年間投稿詳細を表示"):
                                # 年の日付範囲
                                start_date = f"{year}-01-01"
                                end_date = f"{year}-12-31"
                                
                                # 期間内の報告を取得
                                from db_utils import load_reports_by_date
                                reports = load_reports_by_date(start_date, end_date)
                                
                                # 選択したユーザーのレポートだけをフィルタリング
                                user_reports = [r for r in reports if r["投稿者"] == selected_user_year]
                                
                                if user_reports:
                                    st.markdown(f"#### {selected_user_year}の{year}年の投稿詳細 ({len(user_reports)}件)")
                                    
                                    # 月ごとにグループ化
                                    reports_by_month = {}
                                    for report in user_reports:
                                        try:
                                            report_date = datetime.strptime(report["日付"], "%Y-%m-%d")
                                            month_key = f"{report_date.month}月"
                                            if month_key not in reports_by_month:
                                                reports_by_month[month_key] = []
                                            reports_by_month[month_key].append(report)
                                        except Exception as e:
                                            # 日付の解析エラーがあれば「その他」に分類
                                            if "その他" not in reports_by_month:
                                                reports_by_month["その他"] = []
                                            reports_by_month["その他"].append(report)
                                    
                                    # 月ごとにサマリーテーブルと詳細表示
                                    for month_key in sorted(reports_by_month.keys(), key=lambda x: int(x.replace("月", "")) if x != "その他" else 13):
                                        month_reports = reports_by_month[month_key]
                                        st.markdown(f"#### {month_key} ({len(month_reports)}件)")
                                        
                                        # サマリーテーブルを表示
                                        summary_data = []
                                        for report in month_reports:
                                            visited_stores = report.get('visited_stores', [])
                                            store_names = [s.get('name', '無名') for s in visited_stores]
                                            store_text = ", ".join(store_names) if store_names else "記録なし"
                                            
                                            summary_data.append({
                                                "日付": report['日付'],
                                                "場所": store_text[:20] + ('...' if len(store_text) > 20 else ''),
                                                "内容": report['実施内容'][:30] + ('...' if len(report['実施内容']) > 30 else ''),
                                                "今後のアクション": report['今後のアクション'][:30] + ('...' if len(report['今後のアクション']) > 30 else ''),
                                                "コメント数": len(report.get('comments', []))
                                            })
                                        
                                        # テーブル表示
                                        if summary_data:
                                            # インデックスを非表示にしてデータフレーム表示
                                            month_summary_df = pd.DataFrame(summary_data)
                                            st.dataframe(
                                                month_summary_df, 
                                                hide_index=True,
                                                use_container_width=True
                                            )
                                else:
                                    st.info(f"{selected_user_year}の{year}年の投稿はありません。")
                    else:
                        st.info(f"{year}年のデータはありません。")
                else:
                    st.info(f"{year}年のデータはありません。")
                
            # エクスポートボタン
            if st.button("投稿統計データをエクスポート", type="primary"):
                with st.spinner("データをエクスポート中..."):
                    # Excel形式でエクスポート（年を指定）
                    excel_filename = f"投稿統計_{year}年.xlsx"
                    download_link = excel_utils.export_monthly_stats_to_excel(stats, year, excel_filename)
                    st.markdown(download_link, unsafe_allow_html=True)
        else:
            st.info("投稿統計データがありません。")
    
    with tab4:
        st.markdown("### 店舗訪問データのエクスポート")
        
        # 日付操作用にdatetimeをインポート (安全のため再度インポート)
        from datetime import date, timedelta
        
        # 期間指定
        col1, col2 = st.columns(2)
        with col1:
            year = st.selectbox("年", options=range(date.today().year - 2, date.today().year + 1), index=2, key="visit_year")
        with col2:
            month = st.selectbox("月", options=[0] + list(range(1, 13)), 
                             format_func=lambda x: "すべての月" if x == 0 else f"{x}月", key="visit_month")
        
        # データを取得するボタン
        if st.button("店舗訪問データを集計", type="primary"):
            # 全ユーザーの店舗訪問データを取得
            from db_utils import get_all_users_store_visits
            
            # 月の値を適切に設定
            month_value = None if month == 0 else month
            
            # 処理開始のフラグを表示
            with st.spinner("店舗訪問データを取得中..."):
                try:
                    # データ取得
                    all_visits = get_all_users_store_visits(year=year, month=month_value)
                    
                    if all_visits and isinstance(all_visits, dict) and len(all_visits) > 0:
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
                        
                        # Streamlit専用のデータフレーム表示
                        st.dataframe(
                            summary_df,
                            hide_index=True,
                            use_container_width=True
                        )
                        
                        # 詳細データ（折りたたみ）
                        with st.expander("店舗訪問詳細データ（ユーザー別）", expanded=True):
                            for user_name, stores in all_visits.items():
                                st.markdown(f"##### {user_name}")
                                
                                user_data = []
                                for store in stores:
                                    # 日付ごとの訪問内容を整形
                                    visit_details = []
                                    for detail in store.get("details", []):
                                        date = detail["date"]
                                        content = detail.get("content", "")
                                        if content:
                                            visit_details.append(f"{date}: {content}")
                                        else:
                                            visit_details.append(date)
                                    
                                    # 訪問内容をまとめる
                                    visit_info = "\n\n".join(visit_details)
                                    
                                    user_data.append({
                                        "店舗コード": store["code"],
                                        "店舗名": store["name"],
                                        "訪問回数": max(1, store["count"]),
                                        "訪問日と内容": visit_info
                                    })
                                
                                user_df = pd.DataFrame(user_data)
                                if not user_df.empty:
                                    user_df = user_df.sort_values("訪問回数", ascending=False)
                                    
                                    # Streamlit専用のデータフレーム表示
                                    st.dataframe(
                                        user_df,
                                        hide_index=True,
                                        use_container_width=True
                                    )
                                else:
                                    st.info(f"{user_name}の訪問データはありません。")
                                
                                st.markdown("---")
                        
                        # エクスポートボタンを別エリアに配置
                        st.markdown("### データエクスポート")
                        
                        # 期間を含めたファイル名
                        period = f"{year}年"
                        if month_value:
                            period += f"{month_value}月"
                        else:
                            period += "全月"
                        
                        # Excel形式でエクスポート
                        excel_filename = f"店舗訪問データ_{period}.xlsx"
                        
                        # エクスポート処理を直接実行し、リンクを表示
                        try:
                            with st.spinner("Excel形式でエクスポート中..."):
                                download_link = excel_utils.export_store_visits_to_excel(all_visits, excel_filename)
                                st.markdown(download_link, unsafe_allow_html=True)
                        except Exception as e:
                            st.error(f"エクスポート中にエラーが発生しました: {str(e)}")
                            logging.error(f"店舗訪問エクスポートエラー: {e}")
                            import traceback
                            logging.error(traceback.format_exc())
                    else:
                        st.warning("指定された期間の店舗訪問データはありません。")
                        if isinstance(all_visits, dict) and len(all_visits) == 0:
                            st.info("データ構造は正しいですが、中身が空です。この期間にはデータがありません。")
                        elif all_visits is None:
                            st.error("データの取得中にエラーが発生しました。管理者に連絡してください。")
                except Exception as e:
                    st.error(f"データの取得中にエラーが発生しました: {str(e)}")
                    st.info("管理者に連絡してください。")

# 店舗データアップロード機能は削除しました

# お気に入りメンバー管理機能
def manage_favorite_members():
    if "user" not in st.session_state or st.session_state["user"] is None:
        st.error("ログインしてください。")
        return
    
    # 管理者以外はアクセス不可
    if not st.session_state["user"].get("admin", False):
        st.error("この機能は管理者のみ利用できます。")
        return
    
    st.title("⭐ お気に入りメンバー管理")
    st.info("お気に入りメンバーに登録すると、そのメンバーが日報を投稿した際に通知を受け取ることができます。")
    
    # ユーザーのリストを取得
    from db_utils import get_favorite_members, save_favorite_member, delete_favorite_member
    
    admin_code = st.session_state["user"]["code"]
    
    # お気に入りメンバーのリストを取得
    favorite_member_codes = get_favorite_members(admin_code)
    
    # 現在の選択状態をセッション状態で管理
    if "favorite_members" not in st.session_state:
        st.session_state.favorite_members = favorite_member_codes
    
    # ユーザー一覧を表示（編集可能なテーブル形式）
    st.subheader("メンバー一覧")
    
    # ユーザーデータファイルからすべてのユーザーを取得
    try:
        with open("data/users_data.json", "r", encoding="utf-8") as f:
            users_json = json.load(f)
            
        # ユーザーデータをDataFrameに変換
        user_data = []
        for user in users_json:
            # 自分自身は除外
            if user.get("code") == admin_code:
                continue
                
            user_code = user.get("code")
            user_name = user.get("name")
            # 所属部署を取得して、リストを文字列に変換
            departments = user.get("depart", [])
            department_str = ", ".join(departments) if departments else "なし"
            
            if user_code:
                is_favorite = user_code in st.session_state.favorite_members
                user_data.append({
                    "ユーザーコード": user_code,
                    "ユーザー名": user_name,
                    "所属部署": department_str,
                    "お気に入り": is_favorite
                })
        
        # ユーザーデータを表示
        df = pd.DataFrame(user_data)
        if not df.empty:
            edited_df = st.data_editor(
                df,
                column_config={
                    "ユーザーコード": st.column_config.TextColumn("ユーザーコード", disabled=True),
                    "ユーザー名": st.column_config.TextColumn("ユーザー名", disabled=True),
                    "所属部署": st.column_config.TextColumn("所属部署", disabled=True),
                    "お気に入り": st.column_config.CheckboxColumn("お気に入り", help="チェックを入れるとお気に入りに登録されます"),
                },
                hide_index=True,
                use_container_width=True,
                key="favorite_members_editor"
            )
    except Exception as e:
        st.error(f"ユーザーデータの読み込みに失敗しました: {e}")
        return
    
    # 変更があった場合は保存
    if not df.empty and st.button("変更を保存", key="save_favorites"):
        updated = False
        # edited_dfが定義されていることを確認する
        if 'edited_df' in locals() and not edited_df.empty:
            for _, row in edited_df.iterrows():
                user_code = row["ユーザーコード"]
                is_favorite = row["お気に入り"]
                was_favorite = user_code in st.session_state.favorite_members
                
                # お気に入り状態が変更された場合
                if is_favorite != was_favorite:
                    if is_favorite:
                        # お気に入りに追加
                        save_favorite_member(admin_code, user_code)
                        updated = True
                    else:
                        # お気に入りから削除
                        delete_favorite_member(admin_code, user_code)
                        updated = True
        
        if updated:
            # お気に入りリストを更新
            st.session_state.favorite_members = get_favorite_members(admin_code)
            st.success("お気に入りメンバーの設定を保存しました。")
            st.rerun()
        else:
            st.info("変更はありませんでした。")
    
    if df.empty:
        st.info("表示できるユーザーがいません。")
    
    # お気に入りメンバー一覧を表示
    st.subheader("現在のお気に入りメンバー")
    favorite_members = []
    
    # ユーザーデータを一度だけ読み込み
    try:
        with open("data/users_data.json", "r", encoding="utf-8") as f:
            users_json = json.load(f)
            
        # お気に入りメンバーの情報を取得
        for code in st.session_state.favorite_members:
            for u in users_json:
                if u.get("code") == code:
                    user_name = u.get("name")
                    departments = u.get("depart", [])
                    department_str = ", ".join(departments) if departments else "なし"
                    
                    favorite_members.append({
                        "ユーザーコード": code,
                        "ユーザー名": user_name,
                        "所属部署": department_str
                    })
                    break
        
        if favorite_members:
            favorite_df = pd.DataFrame(favorite_members)
            st.dataframe(
                favorite_df,
                hide_index=True,
                use_container_width=True
            )
        else:
            st.info("お気に入りメンバーはまだ登録されていません。")
    except Exception as e:
        st.error(f"お気に入りメンバー情報の取得に失敗しました: {e}")

# ✅ メインアプリ
def main():
    # アプリタイトル設定
    # st.set_page_config(page_title="OK-Nippou", layout="wide")  
    
    # カスタムCSS
    load_css("static/style.css")
    
    # セッション状態の初期化
    if "page" not in st.session_state:
        st.session_state["page"] = "ログイン"
    
    # サイドバー状態管理
    if "hide_sidebar" not in st.session_state:
        st.session_state["hide_sidebar"] = False
    
    # ユーザー状態初期化
    if "user" not in st.session_state:
        st.session_state["user"] = None
        
    # サイドバーの表示/非表示を切り替え
    if st.session_state.get("hide_sidebar", False):
        # サイドバーを隠す状態にする
        st.markdown("""
        <style>
            [data-testid="collapsedControl"] {
                display: none;
            }
            section[data-testid="stSidebar"] {
                display: none;
            }
            button[title="View fullscreen"] {
                display: none;
            }
        </style>
        """, unsafe_allow_html=True)
        
        # タイムラインの上部に「メニュー表示」ボタンを追加
        if st.session_state["user"] is not None:
            if st.button("≡ メニューを表示", key="show_sidebar_button"):
                st.session_state["hide_sidebar"] = False
                st.rerun()

    # ログイン状態に応じてページをレンダリング
    if st.session_state["user"] is None:
        login()
    else:
        # サイドバーナビゲーション（サイドバーが表示モードの場合のみ）
        if not st.session_state.get("hide_sidebar", False):
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
        elif page == "お気に入りメンバー管理":
            manage_favorite_members()
        else:
            st.error(f"不明なページ: {page}")

if __name__ == "__main__":
    main()
