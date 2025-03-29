# main.py
import os
import time
import streamlit as st
import base64
from datetime import datetime, timedelta
import json
from collections import defaultdict

# サブコードから関数をインポート
from db_utils import (
    authenticate_user, save_report, load_reports,
    load_notices, mark_notice_as_read, edit_report, delete_report,
    update_reaction, save_comment, load_commented_reports,
    save_weekly_schedule, load_weekly_schedules, save_weekly_schedule_comment
)

# 絶対パスでCSSファイルを読み込む関数
def load_css(file_name):
    with open(file_name) as f:
        st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

# CSS読み込み
css_file_path = "style.css"
if os.path.exists(css_file_path):
    load_css(css_file_path)

# セッション状態の初期化
if "user" not in st.session_state:
    st.session_state["user"] = None
if "page" not in st.session_state:
    st.session_state["page"] = "ログイン"

# ページ切り替え関数
def switch_page(page_name):
    st.session_state["page"] = page_name

# サイドバーナビゲーション
def sidebar_navigation():
    with st.sidebar:
        st.image("OK-Nippou5.png", use_container_width=True)
        
        menu_items = {
            "⏳ タイムライン": "タイムライン",
            "📅 週間予定": "週間予定",
            "🔔 お知らせ": "お知らせ",
            "✈️ 週間予定投稿": "週間予定投稿",
            "📝 日報作成": "日報投稿",
            "👤 マイページ": "マイページ"
        }
        
        for btn_text, page in menu_items.items():
            if st.button(btn_text, key=f"sidebar_{page}"):
                switch_page(page)

# ログイン画面
def login():
    col1, col2, col3 = st.columns([1, 3, 1])
    with col2:
        st.image("OK-Nippou4.png", use_container_width=True)

    st.title(" ログイン")
    employee_code = st.text_input("社員コード")
    password = st.text_input("パスワード", type="password")
    
    if st.button("ログイン"):
        user = authenticate_user(employee_code, password)
        if user:
            st.session_state["user"] = user
            st.success(f"ようこそ、{user['name']} さん！（{', '.join(user['depart'])}）")
            time.sleep(1)
            switch_page("タイムライン")
            st.rerun()
        else:
            st.error("社員コードまたはパスワードが間違っています。")

# 日報投稿
def post_report():
    if not st.session_state.get("user"):
        st.error("ログインしてください。")
        return

    st.title("日報投稿")
    today = datetime.today().date()
    
    # 日付選択（過去1週間＋未来1日）
    date_options = [today + timedelta(days=i) for i in range(-7, 2)]
    selected_date = st.selectbox(
        "実施日",
        options=date_options,
        format_func=lambda d: d.strftime("%Y年%m月%d日 (%a)")
    )
    
    location = st.text_input("場所")
    category = st.text_input("カテゴリ（商談やイベント提案など）")
    content = st.text_area("実施内容")
    remarks = st.text_area("所感")
    uploaded_file = st.file_uploader("写真を選択", type=["png", "jpg", "jpeg"])
    
    image_base64 = None
    if uploaded_file is not None:
        image_bytes = uploaded_file.getvalue()
        image_base64 = base64.b64encode(image_bytes).decode('utf-8')

    if st.button("投稿する"):
        report_data = {
            "投稿者": st.session_state["user"]["name"],
            "実行日": selected_date.strftime("%Y-%m-%d"),
            "場所": location,
            "カテゴリ": category,
            "実施内容": content,
            "所感": remarks,
            "image": image_base64
        }
        
        try:
            save_report(report_data)
            st.success("✅ 日報を投稿しました！")
            time.sleep(1)
            switch_page("タイムライン")
        except Exception as e:
            st.error(f"⚠️ 投稿に失敗しました: {str(e)}")

# タイムライン表示
def timeline():
    if not st.session_state.get("user"):
        st.error("ログインしてください。")
        return

    st.title(" タイムライン")
    
    # フィルタリング設定
    st.sidebar.subheader("表示設定")
    period_option = st.sidebar.radio(
        "表示期間",
        ["24時間以内", "1週間以内", "カスタム期間"],
        index=0
    )
    
    start_date = end_date = None
    if period_option == "カスタム期間":
        col1, col2 = st.sidebar.columns(2)
        with col1:
            start_date = st.date_input("開始日")
        with col2:
            end_date = st.date_input("終了日")
    
    # 部署フィルター
    show_all = st.sidebar.checkbox("全部署の投稿を表示", value=True)
    
    # 検索機能
    search_query = st.text_input("キーワード検索")
    
    # データ取得
    try:
        reports = load_reports()
    except Exception as e:
        st.error(f"⚠️ データの取得に失敗しました: {str(e)}")
        return
    
    # フィルタリング処理
    filtered_reports = []
    for report in reports:
        report_date = datetime.strptime(report["実行日"], "%Y-%m-%d").date()
        
        # 期間フィルター
        if period_option == "24時間以内":
            if (datetime.now().date() - report_date).days > 1:
                continue
        elif period_option == "1週間以内":
            if (datetime.now().date() - report_date).days > 7:
                continue
        elif period_option == "カスタム期間" and start_date and end_date:
            if not (start_date <= report_date <= end_date):
                continue
                
        # 部署フィルター
        if not show_all:
            user_departments = st.session_state["user"]["depart"]
            if report["投稿者"] not in get_department_members(user_departments):
                continue
                
        # キーワード検索
        if search_query:
            search_text = f"{report['実施内容']} {report['所感']} {report['カテゴリ']}".lower()
            if search_query.lower() not in search_text:
                continue
                
        filtered_reports.append(report)
    
    # 投稿表示
    for report in filtered_reports:
        with st.container():
            st.subheader(f"{report['投稿者']} さんの日報 ({report['実行日']})")
            st.write(f"**場所:** {report['場所']}")
            st.write(f"**カテゴリ:** {report['カテゴリ']}")
            st.write(f"**実施内容:** {report['実施内容']}")
            st.write(f"**所感:** {report['所感']}")
            
            if report.get("image"):
                try:
                    image_data = base64.b64decode(report["image"])
                    st.image(image_data, caption="投稿画像", use_container_width=True)
                except Exception as e:
                    st.error("⚠️ 画像の表示に失敗しました")
            
            # リアクションボタン
            col1, col2 = st.columns(2)
            with col1:
                if st.button(f"❤️ {report['いいね']} いいね！", key=f"like_{report['id']}"):
                    update_reaction(report["id"], "いいね")
                    st.rerun()
            with col2:
                if st.button(f"💪 {report['ナイスファイト']} ナイスファイト！", key=f"nice_{report['id']}"):
                    update_reaction(report["id"], "ナイスファイト")
                    st.rerun()
            
            # コメントセクション
            with st.expander(f"コメント ({len(report['コメント'])})"):
                for comment in report["コメント"]:
                    st.write(f"**{comment['投稿者']}** ({comment['日時']}): {comment['コメント']}")
                
                new_comment = st.text_input(
                    "新しいコメントを入力",
                    key=f"comment_input_{report['id']}"
                )
                
                if st.button("コメントを投稿", key=f"comment_btn_{report['id']}"):
                    if new_comment.strip():
                        save_comment(report["id"], st.session_state["user"]["name"], new_comment)
                        st.rerun()
                    else:
                        st.warning("コメントを入力してください")
            
            st.markdown("---")

# 週間予定表示
def show_weekly_schedules():
    if not st.session_state.get("user"):
        st.error("ログインしてください。")
        return

    st.title("週間予定")
    
    try:
        schedules = load_weekly_schedules()
    except Exception as e:
        st.error(f"⚠️ データの取得に失敗しました: {str(e)}")
        return
    
    # 週ごとにグループ化
    grouped = defaultdict(list)
    for s in schedules:
        key = (s['開始日'], s['終了日'])
        grouped[key].append(s)
    
    # 表示処理
    for (start_date, end_date), group in grouped.items():
        with st.expander(f"{start_date} ～ {end_date}"):
            for schedule in group:
                st.subheader(f"{schedule['投稿者']} さんの週間予定")
                
                days = ["月曜日", "火曜日", "水曜日", "木曜日", "金曜日", "土曜日", "日曜日"]
                for day in days:
                    st.write(f"**{day}:** {schedule[day]}")
                
                # コメントセクション
                with st.expander("コメント"):
                    for comment in schedule["コメント"]:
                        st.write(f"**{comment['投稿者']}** ({comment['日時']}): {comment['コメント']}")
                    
                    new_comment = st.text_input(
                        "新しいコメントを入力",
                        key=f"schedule_comment_{schedule['id']}"
                    )
                    
                    if st.button("コメントを投稿", key=f"schedule_comment_btn_{schedule['id']}"):
                        if new_comment.strip():
                            save_weekly_schedule_comment(schedule["id"], st.session_state["user"]["name"], new_comment)
                            st.rerun()
                        else:
                            st.warning("コメントを入力してください")
                
                st.markdown("---")

# マイページ
def my_page():
    if not st.session_state.get("user"):
        st.error("ログインしてください。")
        return

    user_name = st.session_state["user"]["name"]
    st.title(f"{user_name} さんのマイページ")
    
    try:
        # ユーザー関連データ取得
        my_reports = [r for r in load_reports() if r["投稿者"] == user_name]
        commented_reports = load_commented_reports(user_name)
        my_schedules = [s for s in load_weekly_schedules() if s["投稿者"] == user_name]
        
    except Exception as e:
        st.error(f"⚠️ データの取得に失敗しました: {str(e)}")
        return
    
    # 今週の投稿
    with st.expander("📅 今週の活動", expanded=True):
        if not my_reports:
            st.info("今週の投稿はありません")
        else:
            for report in my_reports:
                show_report_details(report)
    
    # 過去の投稿
    with st.expander("🗂 過去の投稿"):
        if not my_reports:
            st.info("過去の投稿はありません")
        else:
            for report in my_reports:
                show_report_details(report)
    
    # コメントした投稿
    with st.expander("💬 コメントした投稿"):
        if not commented_reports:
            st.info("コメントした投稿はありません")
        else:
            for report in commented_reports:
                show_report_details(report)
    
    # 週間予定
    with st.expander("📆 週間予定"):
        if not my_schedules:
            st.info("投稿した週間予定はありません")
        else:
            for schedule in my_schedules:
                st.subheader(f"{schedule['開始日']} ～ {schedule['終了日']}")
                days = ["月曜日", "火曜日", "水曜日", "木曜日", "金曜日", "土曜日", "日曜日"]
                for day in days:
                    st.write(f"**{day}:** {schedule[day]}")
                st.markdown("---")

# 投稿詳細表示
def show_report_details(report):
    with st.container():
        st.subheader(f"{report['実行日']} - {report['場所']}")
        st.write(f"**カテゴリ:** {report['カテゴリ']}")
        st.write(f"**実施内容:** {report['実施内容']}")
        st.write(f"**所感:** {report['所感']}")
        
        if report.get("image"):
            try:
                image_data = base64.b64decode(report["image"])
                st.image(image_data, caption="投稿画像", use_container_width=True)
            except:
                st.error("⚠️ 画像の表示に失敗しました")
        
        # 編集・削除ボタン（自分の投稿のみ）
        if report["投稿者"] == st.session_state["user"]["name"]:
            col1, col2 = st.columns([1, 3])
            with col1:
                edit_mode = st.button("✏️ 編集", key=f"edit_{report['id']}")
            with col2:
                if st.button("🗑️ 削除", key=f"delete_{report['id']}"):
                    if delete_report(report["id"]):
                        st.success("削除しました")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error("削除に失敗しました")
            
            # 編集フォーム
            if edit_mode:
                edit_report_form(report)

# 投稿編集フォーム
def edit_report_form(report):
    with st.form(key=f"edit_form_{report['id']}"):
        new_date = st.date_input(
            "実施日",
            value=datetime.strptime(report["実行日"], "%Y-%m-%d").date()
        )
        new_location = st.text_input("場所", value=report["場所"])
        new_category = st.text_input("カテゴリ", value=report["カテゴリ"])
        new_content = st.text_area("実施内容", value=report["実施内容"])
        new_remarks = st.text_area("所感", value=report["所感"])
        
        submitted = st.form_submit_button("保存")
        if submitted:
            try:
                edit_report(
                    report["id"],
                    new_date.strftime("%Y-%m-%d"),
                    new_location,
                    new_category,
                    new_content,
                    new_remarks
                )
                st.success("変更を保存しました")
                time.sleep(1)
                st.rerun()
            except Exception as e:
                st.error(f"保存に失敗しました: {str(e)}")

# お知らせ表示
def show_notices():
    if not st.session_state.get("user"):
        st.error("ログインしてください。")
        return

    user_name = st.session_state["user"]["name"]
    st.title("🔔 お知らせ")
    
    try:
        notices = load_notices(user_name)
    except Exception as e:
        st.error(f"⚠️ お知らせの取得に失敗しました: {str(e)}")
        return
    
    # 未読通知
    unread = [n for n in notices if not n["既読"]]
    if unread:
        st.subheader("新しいお知らせ")
        for notice in unread:
            with st.container():
                st.markdown(f"### {notice['タイトル']}")
                st.write(notice["内容"])
                if st.button("既読にする", key=f"read_{notice['id']}"):
                    mark_notice_as_read(notice["id"])
                    st.rerun()
                st.markdown("---")
    
    # 既読通知
    read = [n for n in notices if n["既読"]]
    if read:
        with st.expander("過去のお知らせ"):
            for notice in read:
                st.markdown(f"**{notice['タイトル']}**")
                st.write(notice["内容"])
                st.markdown("---")

# 部署メンバー取得（ユーザーデータから）
def get_department_members(departments):
    try:
        with open("data/users_data.json", "r", encoding="utf-8-sig") as f:
            users = json.load(f)
        return [u["name"] for u in users if any(d in u["depart"] for d in departments)]
    except:
        return []

# メイン処理
if __name__ == "__main__":
    if st.session_state["page"] == "ログイン":
        login()
    else:
        if not st.session_state.get("user"):
            st.error("ログインしてください。")
            st.stop()
        
        sidebar_navigation()
        
        page_handlers = {
            "タイムライン": timeline,
            "日報投稿": post_report,
            "お知らせ": show_notices,
            "マイページ": my_page,
            "週間予定投稿": post_weekly_schedule,
            "週間予定": show_weekly_schedules
        }
        
        # ページハンドラから現在のページに対応する関数を呼び出す
        if st.session_state["page"] in page_handlers:
            page_handlers[st.session_state["page"]]()
        else:
            st.error("ページが見つかりません。")
