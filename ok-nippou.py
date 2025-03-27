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

# ヘルパー関数: 現在時刻に9時間を加算する
def get_current_time():
    return datetime.now() + timedelta(hours=9)  # JSTで現在時刻を取得

# サブコーディングから必要な関数をインポート
from db_utils import (
    init_db, authenticate_user, save_report, load_reports, 
    load_notices, mark_notice_as_read, edit_report, delete_report, 
    update_reaction, save_comment, load_commented_reports,
    save_weekly_schedule_comment, add_comments_column  # 追加
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

# ✅ データベースのパス
DB_PATH = "data/reports.db"

# ✅ SQLite 初期化（データを消さない）
init_db(keep_existing=True)
# メインコードの最初の方（データベース初期化後）に追加
add_comments_column()  # 週間予定テーブルにコメントカラムが存在することを保証

# ✅ ログイン状態を管理
if "user" not in st.session_state:
    st.session_state["user"] = None
if "page" not in st.session_state:
    st.session_state["page"] = "ログイン"

# ✅ ページ遷移関数（修正済み）
def switch_page(page_name):
    """ページを切り替える（即時リロードはなし！）"""
    st.session_state["page"] = page_name

# ✅ ナビゲーションバー（CSSを削除）
# ...（以下、元のコードと同じ。その他の関数やメインロジックは変更なし）...
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
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()

        # ✅ 投稿日時を JST で保存
        schedule["投稿日時"] = (datetime.now() + timedelta(hours=9)).strftime("%Y-%m-%d %H:%M:%S")

        cur.execute("""
        INSERT INTO weekly_schedules (投稿者, 開始日, 終了日, 月曜日, 火曜日, 水曜日, 木曜日, 金曜日, 土曜日, 日曜日, 投稿日時)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            schedule["投稿者"], schedule["開始日"], schedule["終了日"], 
            schedule["月曜日"], schedule["火曜日"], schedule["水曜日"], 
            schedule["木曜日"], schedule["金曜日"], schedule["土曜日"], 
            schedule["日曜日"], schedule["投稿日時"]
        ))

        conn.commit()
        conn.close()
        print("✅ 週間予定を保存しました！")  # デバッグログ
    except Exception as e:
        print(f"⚠️ 週間予定の保存エラー: {e}")  # エラー内容を表示

def load_weekly_schedules():
    """週間予定データを取得（最新の投稿順にソート）"""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("SELECT *, コメント FROM weekly_schedules ORDER BY 投稿日時 DESC") # コメントカラムも取得
    rows = cur.fetchall()
    conn.close()

    # ✅ データを辞書リストに変換
    schedules = []
    for row in rows:
        schedules.append({
            "id": row[0], "投稿者": row[1], "開始日": row[2], "終了日": row[3], 
            "月曜日": row[4], "火曜日": row[5], "水曜日": row[6], 
            "木曜日": row[7], "金曜日": row[8], "土曜日": row[9], 
            "日曜日": row[10], "投稿日時": row[11],
            "コメント": json.loads(row[12]) if row[12] else [] # コメントをJSONデコード
        })
    return schedules

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

    st.title("週間予定")

    # カスタムCSSでネスト表現を実現
    st.markdown("""
    <style>
    .nested-expander {
        border-left: 3px solid #f0f2f6;
        margin-left: 1rem;
        padding-left: 1rem;
    }
    .week-header {
        cursor: pointer;
        padding: 0.5rem;
        background-color: #f0f2f6;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
        transition: background-color 0.3s ease, max-height 0.3s ease; /* アニメーションを追加 */
        overflow: hidden; /* コンテンツを非表示 */
    }
    .week-header:hover {
        background-color: #e0e0e0; /* ホバー時の色を変更 */
    }
    .week-header.expanded {
        max-height: none; /* 展開時は高さを自動調整 */
    }
    .week-content {
        overflow: hidden; /* アニメーションのために追加 */
        transition: max-height 0.3s ease; /* アニメーションを追加 */
    }
</style>
    """, unsafe_allow_html=True)

    schedules = load_weekly_schedules()

    if not schedules:
        st.info("週間予定はありません。")
        return

    # 週ごとにグループ化
    grouped = defaultdict(list)
    for s in schedules:
        key = (s['開始日'], s['終了日'])
        grouped[key].append(s)

    # 開始日で降順ソート
    sorted_groups = sorted(grouped.items(),
                           key=lambda x: datetime.strptime(x[0][0], "%Y-%m-%d"),
                           reverse=True)

    # 現在の日付から6週間前の日付を計算
    six_weeks_ago = datetime.now() - timedelta(weeks=6)

    # 最新の投稿（5週分）と過去の投稿（6週前以前）に分割
    recent_schedules = []
    past_schedules = []
    for start_end, group_schedules in sorted_groups:
        start_date = datetime.strptime(start_end[0], "%Y-%m-%d")
        if start_date >= six_weeks_ago:
            recent_schedules.append((start_end, group_schedules))
        else:
            past_schedules.append((start_end, group_schedules))

    # 最新の投稿を表示
    st.subheader("直近5週分の予定")
    display_schedules(recent_schedules)

    # 過去の投稿を表示
    if past_schedules:
        st.subheader("過去の予定を見る（6週間以前）")
        display_past_schedules(past_schedules)

    # ダウンロードボタン（ループの外に移動）
    if schedules:
        if st.button("週間予定をExcelでダウンロード"):
            start_date = schedules[0]["開始日"]
            end_date = schedules[0]["終了日"]
            excel_file = excel_utils.download_weekly_schedule_excel(start_date, end_date)
            st.download_button(
                label="ダウンロード",
                data=excel_file,
                file_name="週間予定.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

def display_schedules(schedules_to_display):
    for idx, ((start_str, end_str), group_schedules) in enumerate(schedules_to_display):
        start_date = datetime.strptime(start_str, "%Y-%m-%d")
        end_date = datetime.strptime(end_str, "%Y-%m-%d")
        weekday_ja = ["月", "火", "水", "木", "金", "土", "日"]

        # 週のヘッダー（擬似折りたたみボタン）
        group_title = (
            f"{start_date.month}月{start_date.day}日（{weekday_ja[start_date.weekday()]}）"
            f" ～ {end_date.month}月{end_date.day}日（{weekday_ja[end_date.weekday()]}）"
        )

        # セッションステートで開閉状態を管理
        if f'week_{idx}_expanded' not in st.session_state:
            st.session_state[f'week_{idx}_expanded'] = False

        # ヘッダークリックで状態切り替え
        clicked = st.button(
            f" {group_title} {'▼' if st.session_state[f'week_{idx}_expanded'] else '▶'}",
            key=f'week_header_{idx}',
            use_container_width=True
        )

        if clicked:
            st.session_state[f'week_{idx}_expanded'] = not st.session_state[f'week_{idx}_expanded']

        # コンテンツ表示
        if st.session_state[f'week_{idx}_expanded']:
            with st.container():
                st.markdown('<div class="nested-expander">', unsafe_allow_html=True)

                for schedule in group_schedules:
                    with st.expander(f"{schedule['投稿者']} さんの週間予定 ▽"):
                        # 各曜日の日付を計算
                        days = []
                        current_date = start_date
                        for i in range(7):
                            days.append(current_date)
                            current_date += timedelta(days=1)

                        # 予定表示
                        for i, weekday in enumerate(["月曜日", "火曜日", "水曜日", "木曜日", "金曜日", "土曜日", "日曜日"]):
                            target_date = days[i]
                            date_str = f"{target_date.month}月{target_date.day}日（{weekday_ja[target_date.weekday()]}）"
                            st.write(f"**{date_str}**: {schedule[weekday]}")

                        st.write(f"**投稿日時:** {schedule['投稿日時']}")

                        # コメント表示
                        st.markdown("---")
                        st.subheader("コメント")
                        if schedule["コメント"]:
                            for comment in schedule["コメント"]:
                                st.write(f"- {comment['投稿者']} ({comment['日時']}): {comment['コメント']}")
                        else:
                            st.write("まだコメントはありません。")

                        # コメント入力
                        comment_text = st.text_area(
                            f"コメントを入力 (ID: {schedule['id']})",
                            key=f"comment_{schedule['id']}"
                        )
                        if st.button(f"コメントを投稿", key=f"submit_{schedule['id']}"):
                            if comment_text.strip():
                                save_weekly_schedule_comment(schedule["id"], st.session_state["user"]["name"], comment_text)
                                st.rerun()
                            else:
                                st.warning("コメントを入力してください。")

                st.markdown('</div>', unsafe_allow_html=True)  # ここでdivを閉じる

def display_past_schedules(past_schedules):
    # 月ごとにグループ化
    monthly_grouped = defaultdict(lambda: defaultdict(list))
    for (start_str, end_str), group_schedules in past_schedules:
        start_date = datetime.strptime(start_str, "%Y-%m-%d")
        monthly_grouped[start_date.year][start_date.month].append(((start_str, end_str), group_schedules))

    # 年と月でソートして表示
    for year in sorted(monthly_grouped.keys(), reverse=True):
        st.markdown(f"├─ {year}年{'' if len(monthly_grouped[year]) > 1 else ' '}{list(monthly_grouped[year].keys())[0] if len(monthly_grouped[year]) == 1 else ''}")
        for month in sorted(monthly_grouped[year].keys(), reverse=True):
            st.markdown(f"│  ├─ {month}月")
            for (start_str, end_str), group_schedules in sorted(monthly_grouped[year][month], key=lambda x: x[0][0], reverse=True):
                start_date = datetime.strptime(start_str, "%Y-%m-%d")
                end_date = datetime.strptime(end_str, "%Y-%m-%d")
                weekday_ja = ["月", "火", "水", "木", "金", "土", "日"]
                st.markdown(f"│ │ ├─ {start_date.month}/{start_date.day} ({weekday_ja[start_date.weekday()]})～{end_date.month}/{end_date.day} ({weekday_ja[end_date.weekday()]})")
                st.markdown('│ │ │ <div class="nested-expander">', unsafe_allow_html=True)
                for schedule in group_schedules:
                    with st.expander(f"{schedule['投稿者']} さんの週間予定 ▽"):
                        # 各曜日の日付を計算
                        days = []
                        current_date = start_date
                        for i in range(7):
                            days.append(current_date)
                            current_date += timedelta(days=1)

                        # 予定表示
                        for i, weekday in enumerate(["月曜日", "火曜日", "水曜日", "木曜日", "金曜日", "土曜日", "日曜日"]):
                            target_date = days[i]
                            date_str = f"{target_date.month}月{target_date.day}日（{weekday_ja[target_date.weekday()]}）"
                            st.write(f"**{date_str}**: {schedule[weekday]}")

                        st.write(f"**投稿日時:** {schedule['投稿日時']}")

                        # コメント表示
                        st.markdown("---")
                        st.subheader("コメント")
                        if schedule["コメント"]:
                            for comment in schedule["コメント"]:
                                st.write(f"- {comment['投稿者']} ({comment['日時']}): {comment['コメント']}")
                        else:
                            st.write("まだコメントはありません。")

                        # コメント入力
                        comment_text = st.text_area(
                            f"コメントを入力 (ID: {schedule['id']})",
                            key=f"comment_{schedule['id']}"
                        )
                        if st.button(f"コメントを投稿", key=f"submit_{schedule['id']}"):
                            if comment_text.strip():
                                save_weekly_schedule_comment(schedule["id"], st.session_state["user"]["name"], comment_text)
                                st.rerun()
                            else:
                                st.warning("コメントを入力してください。")
                st.markdown('│  │  </div>', unsafe_allow_html=True)
                
def add_comments_column():
    """weekly_schedules テーブルにコメントカラムを追加"""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("ALTER TABLE weekly_schedules ADD COLUMN コメント TEXT DEFAULT '[]'")
    conn.commit()
    conn.close()
    print("✅ コメントカラムを追加しました！")

# ✅ 日報投稿
def post_report():
    if "user" not in st.session_state or st.session_state["user"] is None:
        st.error("ログインしてください。")
        return

    st.title("日報投稿")
    # top_navigation()

     # 選択可能な日付リスト（1週間前～本日）
    today = datetime.today().date()
    date_options = [(today + timedelta(days=1) - timedelta(days=i)) for i in range(9)]
    date_options_formatted = [f"{d.strftime('%Y年%m月%d日 (%a)')}" for d in date_options]

    # 実施日の選択（リストから選ぶ）
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
            "実行日": formatted_date,  # YYYY-MM-DD 形式で保存
            "カテゴリ": category,
            "場所": location,
            "実施内容": content,
            "所感": remarks,
            "image": image_base64
        })
        st.success("✅ 日報を投稿しました！")
        time.sleep(1)
        switch_page("タイムライン")


# ✅ タイムライン（コメント機能修正）
def timeline():
    if "user" not in st.session_state or st.session_state["user"] is None:
        st.error("ログインしてください。")
        return
    st.title(" タイムライン")
    reports = load_reports()

    # ✅ 期間選択（キーを追加）
    st.sidebar.subheader("表示期間を選択")
    
     # カスタムCSSを適用
    st.markdown(
        """
        <style>
            div[data-baseweb="radio"] label {
                color: white !important;
            }
            .stSidebar .stSubheader {
                color: white !important;
            }
        </style>
        """,
        unsafe_allow_html=True
    )
    
    period_option = st.sidebar.radio(
        "表示する期間を選択",
        ["24時間以内の投稿", "1週間以内の投稿", "過去の投稿"],
        index=0,
        key="timeline_period_selector"
    )

    
    # ✅ デフォルトで24時間以内の投稿を表示
    if period_option == "24時間以内の投稿":
        start_datetime = datetime.now() + timedelta(hours=9) - timedelta(hours=24)  # 過去24時間（JST）
        end_datetime = datetime.now() + timedelta(hours=9)  # 現在時刻（JST）
    elif period_option == "1週間以内の投稿":
        start_datetime = datetime.now() + timedelta(hours=9) - timedelta(days=7)  # 過去7日間（JST）
        end_datetime = datetime.now() + timedelta(hours=9)  # 現在時刻（JST）
    else:
        # ✅ 過去の投稿を選択した場合、カレンダーで期間を指定
        st.sidebar.subheader("過去の投稿を表示")
        col1, col2 = st.sidebar.columns(2)
        with col1:
            start_date = st.date_input("開始日", datetime.now().date() - timedelta(days=365), max_value=datetime.now().date() - timedelta(days=1))
        with col2:
            end_date = st.date_input("終了日", datetime.now().date() - timedelta(days=1), min_value=start_date, max_value=datetime.now().date() - timedelta(days=1))
        start_datetime = datetime(start_date.year, start_date.month, start_date.day)
        end_datetime = datetime(end_date.year, end_date.month, end_date.day) + timedelta(days=1)
    
    # ✅ 選択された期間に該当する投稿をフィルタリング
    filtered_reports = []
    for report in reports:
        report_datetime = datetime.strptime(report["投稿日時"], "%Y-%m-%d %H:%M:%S")
        if start_datetime <= report_datetime <= end_datetime:
            filtered_reports.append(report)

    # ✅ 現在のユーザーの所属部署を取得
    user_departments = st.session_state["user"]["depart"]  # 配列で取得

    # ✅ フィルタリング用のセッション管理（デフォルトは「すべて表示」）
    if "filter_department" not in st.session_state:
        st.session_state["filter_department"] = "すべて"

    # ✅ 部署フィルタボタン
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🌍 すべての投稿を見る"):
            st.session_state["filter_department"] = "すべて"
            st.rerun()
    
    with col2:
        if st.button("🏢 自分の部署のメンバーの投稿を見る"):
            st.session_state["filter_department"] = "自分の部署"
            st.rerun()

    # ✅ フィルタを適用（自分の部署のメンバーの投稿のみ表示）
    if st.session_state["filter_department"] == "自分の部署":
        try:
            USER_FILE = "data/users_data.json"
            with open(USER_FILE, "r", encoding="utf-8-sig") as file:
                users = json.load(file)

            # ✅ 自分の部署にいるメンバーの名前を取得
            department_members = {
                user["name"] for user in users if any(dept in user_departments for dept in user["depart"])
            }

            # ✅ メンバーの投稿のみフィルタリング
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
            or search_query.lower() in report["投稿者"].lower()  # 投稿主の名前でも検索
        ]

    if not filtered_reports:
        st.warning(" 該当する投稿が見つかりませんでした。")
        return

    # ✅ 投稿を表示
    for report in filtered_reports:
        st.subheader(f"{report['投稿者']} さんの日報 ({report['実行日']})")
        st.write(f" **実施日:** {report['実行日']}")
        st.write(f" **場所:** {report['場所']}")
        st.write(f" **実施内容:** {report['実施内容']}")
        st.write(f" **所感:** {report['所感']}")

        # ✅ 画像が存在する場合、表示する
        if report.get("image"):
            try:
                # Base64データをデコードして画像を表示
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
            if st.button(f"💪 {report['ナイスファイト']} ナイスファイト！", key=f"nice_{report['id']}"):
                update_reaction(report["id"], "ナイスファイト")
                st.rerun()

        # コメント欄
        comment_count = len(report["コメント"]) if report["コメント"] else 0  # コメント件数を取得
        with st.expander(f" ({comment_count}件)のコメントを見る・追加する "):  # 件数を表示
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

# ✅ お知らせを表示（未読を強調し、既読を折りたたむ）
def show_notices():
    if "user" not in st.session_state or st.session_state["user"] is None:
        st.error("ログインしてください。")
        return

    st.title(" お知らせ")
    # top_navigation()

    # ✅ 現在のユーザー名を取得
    user_name = st.session_state["user"]["name"]

    # ✅ 対象ユーザーに紐づくお知らせを取得
    notices = load_notices(user_name)

    if not notices:
        st.info(" お知らせはありません。")
        return

    # ✅ notice_to_read を初期化
    if "notice_to_read" not in st.session_state:
        st.session_state["notice_to_read"] = None

    # ✅ 未読・既読を分類
    new_notices = [n for n in notices if n["既読"] == 0]
    old_notices = [n for n in notices if n["既読"] == 1]

    # ✅ 未読のお知らせを上部に表示
    if new_notices:
        st.subheader(" 新着お知らせ")
        for notice in new_notices:
            with st.container():
                st.markdown(f"### {notice['タイトル']} ✅")
                st.write(f" {notice['日付']}")
                st.write(notice["内容"])

                # ✅ クリックで既読処理を実行
                if st.button(f"✔️ 既読にする", key=f"read_{notice['id']}"):
                    st.session_state["notice_to_read"] = notice["id"]

    # ✅ 既読処理を実行
    if st.session_state["notice_to_read"] is not None:
        mark_notice_as_read(st.session_state["notice_to_read"])
        st.session_state["notice_to_read"] = None  # 既読処理後にリセット
        st.rerun()  # ✅ 即リロードして画面を更新！

    # ✅ 既読のお知らせを折りたたみ表示
    if old_notices:
        with st.expander(" 過去のお知らせを見る"):
            for notice in old_notices:
                with st.container():
                    st.markdown(f"**{notice['タイトル']}**")
                    st.write(f" {notice['日付']}")
                    st.write(notice["内容"])

# ✅ マイページ
def my_page():
    if "user" not in st.session_state or st.session_state["user"] is None:
        st.error("ログインしてください。")
        return

    st.title("マイページ")
    # top_navigation()

    reports = load_reports()
    my_reports = [r for r in reports if r["投稿者"] == st.session_state["user"]["name"]]

    #  今週の投稿
    with st.expander("今週の投稿", expanded=False):  # 初期状態は折りたたまれている
        now = datetime.utcnow()
        start_of_week = now - timedelta(days=now.weekday())
        end_of_week = start_of_week + timedelta(days=4)

        weekly_reports = [
            r for r in my_reports
            if start_of_week.date() <= datetime.strptime(r["実行日"], "%Y-%m-%d").date() <= end_of_week.date()
        ]

        if weekly_reports:
            for index, report in enumerate(weekly_reports): # indexを追加
                st.markdown(f"**{report['実行日']} / {report['場所']}**")
                show_report_details(report, index)  # indexを渡す
        else:
            st.info("今週の投稿はありません。")

    #  過去の投稿
    with st.expander("過去の投稿", expanded=False):  # 初期状態は折りたたまれている
        past_reports = [r for r in my_reports if r not in weekly_reports]

        if past_reports:
            for index, report in enumerate(past_reports): # indexを追加
                st.markdown(f"**{report['実行日']} / {report['場所']}**")
                show_report_details(report, index)  # indexを渡す
        else:
            st.info("過去の投稿はありません。")

    #  コメントした投稿
    with st.expander("コメントした投稿", expanded=False):  # 初期状態は折りたたまれている
        commented_reports = load_commented_reports(st.session_state["user"]["name"])

        if commented_reports:
            for index, report in enumerate(commented_reports): # indexを追加
                st.markdown(f"**{report['投稿者']} さんの日報 ({report['実行日']})**")
                show_report_details(report, index)  # indexを渡す
        else:
            st.info("コメントした投稿はありません。")

    #  週間予定の表示機能（編集機能削除）
    with st.expander("週間予定", expanded=False):
        st.subheader("週間予定")
        schedules = load_weekly_schedules()
        user_schedules = [s for s in schedules if s["投稿者"] == st.session_state["user"]["name"]]

        if user_schedules:
            for schedule in user_schedules:
                with st.container():
                    st.markdown(f"** 期間: {schedule['開始日']} ～ {schedule['終了日']}**")
                    st.caption(f"最終更新日時: {schedule['投稿日時']}")

                    # 各曜日の予定を表示
                    days = ["月曜日", "火曜日", "水曜日", "木曜日", "金曜日", "土曜日", "日曜日"]
                    for day in days:
                        st.write(f"**{day}**: {schedule[day]}")

                     # コメント表示を追加
                    st.markdown("---")
                    st.subheader("コメント")
                    if schedule["コメント"]:
                        for comment in schedule["コメント"]:
                            st.write(f"- {comment['投稿者']} ({comment['日時']}): {comment['コメント']}")
                    else:
                        st.write("まだコメントはありません。")

                    st.markdown("---")
        else:
            st.info("投稿した週間予定はありません。")
            
# ✅ 投稿詳細（編集・削除機能付き）
def show_report_details(report, report_index):
    """投稿の詳細を表示し、編集・削除機能を提供"""
    st.write(f"**実施日:** {report['実行日']}")
    st.write(f"**場所:** {report['場所']}")
    st.write(f"**実施内容:** {report['実施内容']}")
    st.write(f"**所感:** {report['所感']}")

    # コメント一覧表示
    if report.get("コメント"):
        st.subheader("️ コメント一覧")
        for c_idx, comment in enumerate(report["コメント"]):
            st.write(
                f"{comment['投稿者']} ({comment['日時']}): {comment['コメント']}",
                key=f"comment_{report['id']}_{report_index}_{c_idx}"  # キーにreport_indexを追加
            )

    # 編集 & 削除ボタン（完全に一意なキーを生成）
    if report["投稿者"] == st.session_state["user"]["name"]:
        # ユニークキー生成用の要素
        user_info = st.session_state["user"]
        unique_key_suffix = f"{report['id']}_{report_index}_{user_info.get('employee_code', 'unknown')}_{user_info.get('name', 'unknown')}"  # キーにユーザー情報も追加

        col1, col2 = st.columns(2)
        with col1:
            if st.button(
                "✏️ 編集する",
                key=f"daily_edit_{unique_key_suffix}",  # キーを修正
                help="この日報を編集します"
            ):
                st.session_state[f"edit_mode_{unique_key_suffix}"] = True

        with col2:
            if st.button(
                "️ 削除する",
                key=f"daily_delete_{unique_key_suffix}",  # キーを修正
                help="この日報を完全に削除します"
            ):
                st.session_state[f"confirm_delete_{unique_key_suffix}"] = True

        # 削除確認ダイアログ
        if st.session_state.get(f"confirm_delete_{unique_key_suffix}", False):
            st.warning("⚠️ 本当に削除しますか？")

            col_confirm, col_cancel = st.columns(2)
            with col_confirm:
                if st.button(
                    "✅ はい、削除する",
                    key=f"confirm_delete_{unique_key_suffix}" # キーを修正
                ):
                    delete_report(report["id"])
                    st.success("✅ 削除しました")
                    time.sleep(1)
                    st.rerun()
            with col_cancel:
                if st.button(
                    "❌ キャンセル",
                    key=f"cancel_delete_{unique_key_suffix}" # キーを修正
                ):
                    st.session_state[f"confirm_delete_{unique_key_suffix}"] = False
                    st.rerun()

        # 編集フォーム表示
        if st.session_state.get(f"edit_mode_{unique_key_suffix}", False):
            edit_report_form(report, unique_key_suffix)

# ✅ 編集フォームの修正版
def edit_report_form(report, unique_key_suffix):
    """投稿の編集フォーム（キーを完全に一意化）"""
    new_date = st.text_input(
        "実施日",
        report["実行日"],
        key=f"date_{unique_key_suffix}"
    )
    new_location = st.text_input(
        "場所",
        report["場所"],
        key=f"location_{unique_key_suffix}"
    )
    new_content = st.text_area(
        "実施内容",
        report["実施内容"],
        key=f"content_{unique_key_suffix}"
    )
    new_remarks = st.text_area(
        "所感",
        report["所感"],
        key=f"remarks_{unique_key_suffix}"
    )

    col_save, col_cancel = st.columns([1, 3])
    with col_save:
        if st.button(
            "💾 保存",
            key=f"save_{unique_key_suffix}",
            type="primary"
        ):
            edit_report(
                report["id"],
                new_date,
                new_location,
                new_content,
                new_remarks
            )
            st.session_state[f"edit_mode_{unique_key_suffix}"] = False
            st.success("✅ 編集を保存しました")
            time.sleep(1)
            st.rerun()

    with col_cancel:
        if st.button(
            "キャンセル",
            key=f"cancel_{unique_key_suffix}"
        ):
            st.session_state[f"edit_mode_{unique_key_suffix}"] = False
            st.rerun()
# ✅ メニュー管理
if st.session_state["user"] is None:
    login()
else:
    sidebar_navigation()  # サイドバーナビゲーションを追加
    
    
    # 既存のページ表示ロジックは変更なし
    
    if st.session_state["page"] == "タイムライン":
        timeline()
    elif st.session_state["page"] == "日報投稿":
        post_report()
    elif st.session_state["page"] == "お知らせ":
        show_notices()
    elif st.session_state["page"] == "マイページ":
        my_page()
    elif st.session_state["page"] == "週間予定投稿":  # 週間予定投稿ページを追加
        post_weekly_schedule()
    elif st.session_state["page"] == "週間予定":  # 週間予定表示ページを追加
        show_weekly_schedules()
