import sys
import os
import time
import streamlit as st
import pandas as pd
import base64
from datetime import datetime, timedelta
import json
import psycopg2
from collections import defaultdict

# ヘルパー関数: 現在時刻に9時間を加算する
def get_current_time():
    return datetime.now() + timedelta(hours=9)  # JSTで現在時刻を取得

# サブコーディングから必要な関数をインポート
from db_utils import (
    init_db, authenticate_user, save_report, load_reports,
    load_notices, mark_notice_as_read, edit_report, delete_report,
    update_reaction, save_comment, load_commented_reports,
    save_weekly_schedule_comment, add_comments_column,
    save_weekly_schedule, load_weekly_schedules, # 追加
    update_weekly_schedule, get_weekly_schedule_for_all_users, get_daily_schedule # 追加
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
            st.markdown(f"│ ├─ {month}月")
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

                st.markdown('</div>', unsafe_allow_html=True)

def show_timeline():
    if "user" not in st.session_state or st.session_state["user"] is None:
        st.error("ログインしてください。")
        return
    
    st.title("タイムライン")
    
    try:
        # データベース接続の詳細なログを追加
        print("✅ データベース接続を試みます")
        conn = get_db_connection()
        if conn is None:
            print("❌ データベース接続エラー")
            st.error("データベース接続エラーが発生しました")
            return
        
        cur = conn.cursor()
        
        # データ取得の詳細なログを追加
        print("✅ データ取得クエリを実行します")
        cur.execute("SELECT * FROM reports ORDER BY 投稿日時 DESC")
        
        # クエリ実行の結果を確認
        print("✅ クエリ実行完了")
        
        # データ取得の結果を確認
        rows = cur.fetchall()
        print(f"✅ データ取得完了: {len(rows)}件のデータを取得しました")
        
        if not rows:
            print("⚠️ データが存在しません")
            st.info("タイムラインに表示する投稿はありません。")
            cur.close()
            conn.close()
            return
        
        # データの表示処理
        print("✅ タイムライン表示を開始します")
        for row in rows:
            with st.container():
                st.markdown(f"### {row[1]} さんの日報 ({row[2]})")
                st.write(f"**カテゴリ:** {row[3]}")
                st.write(f"**場所:** {row[4]}")
                st.write(f"**実施内容:** {row[5]}")
                st.write(f"**所感:** {row[6]}")
                
                # 画像表示の処理を改善
                if row[10]:  # 画像データがある場合
                    try:
                        print("✅ 画像データをデコードして表示を試みます")
                        image_data = base64.b64decode(row[10])
                        st.image(image_data, caption="添付画像", use_column_width=True)
                    except Exception as e:
                        print(f"❌ 画像表示エラー: {e}")
                        st.error("画像の表示に失敗しました")
                
                # リアクションボタンの表示
                col1, col2 = st.columns(2)
                if col1.button(f"いいね {row[7]}", key=f"like_{row[0]}"):
                    update_reaction(row[0], "いいね")
                    st.rerun()
                if col2.button(f"ナイスファイト {row[8]}", key=f"nice_{row[0]}"):
                    update_reaction(row[0], "ナイスファイト")
                    st.rerun()
                
                # コメント表示
                st.markdown("---")
                st.subheader("コメント")
                if row[9]:  # コメントデータがある場合
                    try:
                        comments = json.loads(row[9])
                        for comment in comments:
                            st.write(f"- {comment['投稿者']} ({comment['日時']}): {comment['コメント']}")
                    except Exception as e:
                        print(f"❌ コメント表示エラー: {e}")
                        st.error("コメントの表示に失敗しました")
                else:
                    st.write("まだコメントはありません。")
                
                # コメント入力
                comment_text = st.text_area(f"コメントを入力 (ID: {row[0]})", key=f"comment_{row[0]}")
                if st.button(f"コメントを投稿", key=f"submit_{row[0]}"):
                    if comment_text.strip():
                        try:
                            save_comment(row[0], st.session_state["user"]["name"], comment_text)
                            st.rerun()
                        except Exception as e:
                            print(f"❌ コメント保存エラー: {e}")
                            st.error("コメントの保存に失敗しました")
                    else:
                        st.warning("コメントを入力してください。")
        
        print("✅ タイムライン表示完了")
        cur.close()
        conn.close()
        
    except psycopg2.Error as e:
        print(f"❌ データベースエラー: {e}")
        st.error("データベースエラーが発生しました")
    except Exception as e:
        print(f"❌ 予期せぬエラー: {e}")
        st.error("タイムラインの表示に失敗しました")
        
def edit_report_page():
    if "user" not in st.session_state or st.session_state["user"] is None:
        st.error("ログインしてください。")
        return

    report_id = st.session_state.get("edit_report_id")
    if not report_id:
        st.error("編集する投稿が選択されていません。")
        return

    st.title("日報編集")

    # 編集対象の投稿を取得
    reports = load_reports()
    report = next((r for r in reports if r["id"] == report_id), None)
    if not report:
        st.error("投稿が見つかりませんでした。")
        return

    # 編集フォーム
    new_date = st.text_input("実行日", report["実行日"])
    new_location = st.text_input("場所", report["場所"])
    new_content = st.text_area("実施内容", report["実施内容"])
    new_remarks = st.text_area("所感", report["所感"])

    if st.button("更新"):
        edit_report(report_id, new_date, new_location, new_content, new_remarks)
        st.success("投稿を更新しました！")
        st.session_state["page"] = "タイムライン"
        st.rerun()

def post_report():
    if "user" not in st.session_state or st.session_state["user"] is None:
        st.error("ログインしてください。")
        return

    st.title("日報作成")

    # 入力フォーム
    report_date = st.date_input("実行日", datetime.now())
    category = st.selectbox("カテゴリ", ["業務", "会議", "研修", "その他"])
    location = st.text_input("場所")
    content = st.text_area("実施内容")
    remarks = st.text_area("所感")
    uploaded_file = st.file_uploader("画像アップロード", type=["png", "jpg", "jpeg"])

    if st.button("投稿"):
        # 画像をbase64エンコード
        image_base64 = None
        if uploaded_file is not None:
            image_base64 = base64.b64encode(uploaded_file.getvalue()).decode("utf-8")

        # 日報データを保存
        report = {
            "投稿者": st.session_state["user"]["name"],
            "実行日": report_date.strftime("%Y-%m-%d"),
            "カテゴリ": category,
            "場所": location,
            "実施内容": content,
            "所感": remarks,
            "image": image_base64,
        }
        save_report(report)
        st.success("日報を投稿しました！")
        st.session_state["page"] = "タイムライン"
        st.rerun()

def show_notices():
    if "user" not in st.session_state or st.session_state["user"] is None:
        st.error("ログインしてください。")
        return

    st.title("お知らせ")

    notices = load_notices(st.session_state["user"]["name"])
    if not notices:
        st.info("お知らせはありません。")
        return

    for notice in notices:
        if notice["既読"] == 0:
            if st.checkbox(notice["タイトル"], value=True, key=f"notice_{notice['id']}"):
                st.markdown(notice["内容"])
                mark_notice_as_read(notice["id"])
                st.rerun()
        else:
            st.markdown(f"<span style='color:gray;'>{notice['タイトル']} (既読)</span>", unsafe_allow_html=True)
            if st.checkbox("詳細を表示", key=f"details_{notice['id']}"):
                st.markdown(notice["内容"])

def show_mypage():
    if "user" not in st.session_state or st.session_state["user"] is None:
        st.error("ログインしてください。")
        return

    st.title("マイページ")
    user = st.session_state["user"]
    st.write(f"**名前:** {user['name']}")
    st.write(f"**社員コード:** {user['code']}")
    st.write(f"**部署:** {', '.join(user['depart'])}")

    # コメントした投稿を表示
    st.subheader("コメントした投稿")
    commented_reports = load_commented_reports(user["name"])
    if commented_reports:
        for report in commented_reports:
            st.write(f"- {report['実行日']} の投稿にコメントしました ({report['コメント日時']})")
            if st.checkbox("投稿内容を表示", key=f"report_{report['id']}"):
                st.write(f"  - **投稿者:** {report['投稿者']}")
                st.write(f"  - **場所:** {report['場所']}")
                st.write(f"  - **実施内容:** {report['実施内容']}")
                st.write(f"  - **コメント:** {report['コメント'][-1]['コメント']}")
    else:
        st.write("コメントした投稿はありません。")

# ページの表示
if st.session_state["user"] is None:
    login()
else:
    sidebar_navigation()
    if st.session_state["page"] == "タイムライン":
        show_timeline()
    elif st.session_state["page"] == "日報投稿":
        post_report()
    elif st.session_state["page"] == "お知らせ":
        show_notices()
    elif st.session_state["page"] == "マイページ":
        show_mypage()
    elif st.session_state["page"] == "日報編集":
        edit_report_page()
    elif st.session_state["page"] == "週間予定投稿":
        post_weekly_schedule()
    elif st.session_state["page"] == "週間予定":
        show_weekly_schedules()
