import streamlit as st
import base64
from datetime import datetime, timedelta
from db_utils import (
    init_db, authenticate_user, handle_comment, get_comments,
    load_reports, load_weekly_schedules, update_reaction,
    load_notices, mark_notice_read, save_report, save_weekly_schedule,
    update_item, delete_item
)

# 初期設定
DB_PATH = "/mount/src/ok-nippou-kun/Ok-nippou-kun/data/reports.db"
init_db(keep_existing=True)

# セッション状態の初期化
if "user" not in st.session_state:
    st.session_state.user = None
if "page" not in st.session_state:
    st.session_state.page = "ログイン"

# 共通コンポーネント -------------------------------------------------

def top_navigation():
    """共通ナビゲーションバー"""
    cols = st.columns(4)
    pages = {
        "⏳ タイムライン": "タイムライン",
        "📅 週間予定": "週間予定",
        "🔔 お知らせ": "お知らせ",
        "✏️ 新規投稿": "新規投稿選択"
    }
    for col, (label, page) in zip(cols, pages.items()):
        with col:
            if st.button(label):
                st.session_state.page = page
                st.rerun()

def comment_section(item_type, item_id):
    """共通コメントコンポーネント"""
    comments = get_comments(item_type, item_id)
    
    with st.expander(f"💬 コメント ({len(comments)}件)"):
        # コメント表示
        for comment in comments:
            st.markdown(f"""
                **{comment['投稿者']}**  
                `{comment['日時']}`  
                {comment['コメント']}
            """)
        
        # コメント入力
        new_comment = st.text_input(
            "コメントを入力...",
            key=f"comment_{item_type}_{item_id}",
            label_visibility="collapsed"
        )
        
        if st.button("📤 投稿", key=f"send_{item_type}_{item_id}"):
            if new_comment.strip():
                if handle_comment(
                    item_type,
                    item_id,
                    st.session_state.user["name"],
                    new_comment
                ):
                    st.rerun()
            else:
                st.warning("コメントを入力してください")

# ページコンポーネント -------------------------------------------------

def login_page():
    """ログイン画面"""
    st.title("ログイン")
    with st.form("login_form"):
        code = st.text_input("社員コード")
        password = st.text_input("パスワード", type="password")
        if st.form_submit_button("ログイン"):
            user = authenticate_user(code, password)
            if user:
                st.session_state.user = user
                st.session_state.page = "タイムライン"
                st.rerun()
            else:
                st.error("認証に失敗しました")

def timeline_page():
    """タイムライン画面"""
    top_navigation()
    st.title("タイムライン")
    
    # フィルタリング設定
    filtered_reports = apply_filters(load_reports())
    
    # 投稿表示
    for report in filtered_reports:
        with st.container():
            display_report(report)
            comment_section("report", report["id"])

def weekly_schedules_page():
    """週間予定画面"""
    top_navigation()
    st.title("週間予定")
    
    for schedule in load_weekly_schedules():
        with st.expander(f"{schedule['投稿者']} さんの予定"):
            display_schedule(schedule)
            comment_section("weekly", schedule["id"])

def new_post_page():
    """新規投稿選択画面"""
    top_navigation()
    st.title("新規投稿")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("📝 日報を書く"):
            st.session_state.page = "日報投稿"
            st.rerun()
    with col2:
        if st.button("🗓 週間予定を作成"):
            st.session_state.page = "週間予定投稿"
            st.rerun()

def report_form_page():
    """日報投稿画面"""
    top_navigation()
    st.title("日報投稿")
    
    with st.form("report_form"):
        # フォーム項目
        report_data = collect_report_data()
        
        if st.form_submit_button("投稿"):
            save_report(report_data)
            st.session_state.page = "タイムライン"
            st.rerun()

def schedule_form_page():
    """週間予定投稿画面"""
    top_navigation()
    st.title("週間予定投稿")
    
    with st.form("schedule_form"):
        # フォーム項目
        schedule_data = collect_schedule_data()
        
        if st.form_submit_button("投稿"):
            save_weekly_schedule(schedule_data)
            st.session_state.page = "タイムライン"
            st.rerun()

def mypage_page():
    """マイページ"""
    top_navigation()
    st.title("マイページ")
    
    # 投稿管理
    with st.expander("自分の投稿"):
        manage_posts("report", load_reports())
    
    # 週間予定管理
    with st.expander("週間予定"):
        manage_posts("weekly", load_weekly_schedules())
    
    # コメント履歴
    with st.expander("コメントした投稿"):
        display_commented_posts()

# ヘルパー関数 --------------------------------------------------------

def apply_filters(reports):
    """投稿フィルタリング処理"""
    # 期間フィルタ
    filtered = filter_by_period(reports)
    
    # 部署フィルタ
    if st.session_state.get("filter_dept", False):
        filtered = filter_by_department(filtered)
    
    # 検索フィルタ
    if search_query := st.sidebar.text_input("検索"):
        filtered = filter_by_search(filtered, search_query)
    
    return filtered

def display_report(report):
    """日報表示"""
    st.subheader(f"{report['投稿者']} さんの日報")
    st.write(f"**実施日:** {report['実行日']}")
    st.write(f"**場所:** {report['場所']}")
    st.write(f"**内容:** {report['実施内容']}")
    st.write(f"**所感:** {report['所感']}")
    
    # 画像表示
    if report.get("image"):
        try:
            st.image(base64.b64decode(report["image"]))
        except Exception as e:
            st.error("画像の表示に失敗しました")
    
    # リアクションボタン
    col1, col2 = st.columns(2)
    with col1:
        if st.button(f"❤️ {report['いいね']}", key=f"like_{report['id']}"):
            update_reaction("report", report["id"], "like")
    with col2:
        if st.button(f"💪 {report['ナイスファイト']}", key=f"nice_{report['id']}"):
            update_reaction("report", report["id"], "nice")

def display_schedule(schedule):
    """週間予定表示"""
    st.write(f"**期間:** {schedule['開始日']} ～ {schedule['終了日']}")
    days = ["月", "火", "水", "木", "金", "土", "日"]
    for i, day in enumerate(days):
        st.write(f"**{day}曜日:** {schedule[f'{day}曜日']}")

def manage_posts(item_type, items):
    """投稿管理コンポーネント"""
    user_posts = [i for i in items if i["投稿者"] == st.session_state.user["name"]]
    
    for post in user_posts:
        with st.container():
            st.write(f"**{post.get('実行日', post.get('開始日'))}**")
            if item_type == "report":
                st.write(post["実施内容"][:50] + "...")
            else:
                st.write(post["月曜日"][:50] + "...")
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("✏️ 編集", key=f"edit_{item_type}_{post['id']}"):
                    pass  # 編集処理実装
            with col2:
                if st.button("🗑️ 削除", key=f"del_{item_type}_{post['id']}"):
                    delete_item(item_type, post["id"])
                    st.rerun()

# ページルーティング -------------------------------------------------

PAGES = {
    "ログイン": login_page,
    "タイムライン": timeline_page,
    "週間予定": weekly_schedules_page,
    "新規投稿選択": new_post_page,
    "日報投稿": report_form_page,
    "週間予定投稿": schedule_form_page,
    "マイページ": mypage_page
}

if __name__ == "__main__":
    page = PAGES.get(st.session_state.page, login_page)
    page()
