import streamlit as st
import base64
from datetime import datetime, timedelta
import json
import time
from db_utils import (
    init_db, authenticate_user, save_report, load_reports, update_reaction,
    save_comment, load_notices, mark_notice_as_read, save_weekly_schedule,
    load_weekly_schedules, load_commented_reports, edit_report, delete_report,
    save_weekly_schedule_comment
)

# データベース初期化
init_db(keep_existing=True)
# パスワードハッシュ化
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# 管理者権限デコレーター
def admin_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if st.session_state.user.get("role") != "admin":
            st.error("管理者権限が必要です")
            return
        return func(*args, **kwargs)
    return wrapper

# 管理画面
@admin_required
def admin_page():
    st.title("管理者画面")
    # ユーザー管理、データエクスポートなどの機能...

# 監査ログ
def log_action(action):
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO audit_log 
            (user_id, action, timestamp) 
            VALUES (%s, %s, %s)
        """, (st.session_state.user["id"], action, datetime.now()))
        conn.commit()
    except psycopg2.Error as e:
        conn.rollback()
    finally:
        conn.close()

# セッション状態の初期化
def initialize_session():
    if "user" not in st.session_state:
        st.session_state.user = None
    if "page" not in st.session_state:
        st.session_state.page = "ログイン"
    if "edit_target" not in st.session_state:
        st.session_state.edit_target = None
initialize_session()

# CSSの読み込み
def load_css():
    st.markdown("""
    <style>
    .main { background-color: #f0f2f6; }
    .sidebar .sidebar-content { background-color: #2c3e50; }
    h1 { color: #2c3e50; }
    .stButton button { width: 100%; }
    .report-card {
        background: white;
        padding: 20px;
        border-radius: 10px;
        margin: 10px 0;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    </style>
    """, unsafe_allow_html=True)
load_css()

# 共通コンポーネント
def sidebar_navigation():
    with st.sidebar:
        st.image("OK-Nippou5.png", use_container_width=True)
        nav_options = {
            "⏳ タイムライン": "タイムライン",
            "📅 週間予定": "週間予定",
            "🔔 お知らせ": "お知らせ",
            "✈️ 週間予定投稿": "週間予定投稿",
            "📝 日報作成": "日報投稿",
            "👤 マイページ": "マイページ"
        }
        for label, page in nav_options.items():
            if st.button(label, key=f"nav_{page}"):
                st.session_state.page = page
                st.rerun()


# ログインページ
def login_page():
    st.title("日報管理システム")
    col1, col2, col3 = st.columns([1, 3, 1])
    with col2:
        st.image("OK-Nippou4.png", use_container_width=True)
    with st.form("login_form"):
        emp_code = st.text_input("社員コード")
        password = st.text_input("パスワード", type="password")
        if st.form_submit_button("ログイン"):
            user = authenticate_user(emp_code, password)
            if user:
                st.session_state.user = user
                st.session_state.page = "タイムライン"
                st.rerun()
            else:
                st.error("認証に失敗しました")

# 日報投稿ページ
def report_post_page():
    st.title("日報投稿")
    with st.form("report_form"):
        exec_date = st.date_input("実施日", datetime.now() + timedelta(hours=9))
        location = st.text_input("場所")
        category = st.text_input("カテゴリ")
        content = st.text_area("実施内容")
        remarks = st.text_area("所感")
        image = st.file_uploader("画像添付", type=["png", "jpg", "jpeg"])
        if st.form_submit_button("投稿"):
            report_data = {
                "投稿者": st.session_state.user["name"],
                "実行日": exec_date.strftime("%Y-%m-%d"),
                "場所": location,
                "カテゴリ": category,
                "実施内容": content,
                "所感": remarks,
                "image": base64.b64encode(image.read()).decode() if image else None
            }
            save_report(report_data)
            st.success("日報を投稿しました")
            time.sleep(1)
            st.session_state.page = "タイムライン"
            st.rerun()

# タイムラインページ
def timeline_page():
    st.title("タイムライン")
    reports = load_reports()
    
    with st.expander("フィルター設定", expanded=True):
        col1, col2 = st.columns(2)
        with col1:
            period = st.selectbox("表示期間", ["直近24時間", "過去1週間", "全期間"])
        with col2:
            search_term = st.text_input("キーワード検索")
    
    filtered_reports = filter_reports(reports, period, search_term)
    
    for report in filtered_reports:
        with st.container():
            st.markdown(f"### {report['投稿者']} - {report['実行日']}")
            display_report(report)

def filter_reports(reports, period, search_term):
    now = datetime.now() + timedelta(hours=9)
    if period == "直近24時間":
        cutoff = now - timedelta(hours=24)
    elif period == "過去1週間":
        cutoff = now - timedelta(weeks=1)
    else:
        cutoff = datetime.min
    filtered = [r for r in reports if datetime.strptime(r["投稿日時"], "%Y-%m-%d %H:%M:%S") >= cutoff]
    if search_term:
        filtered = [r for r in filtered if search_term.lower() in r["実施内容"].lower() or search_term.lower() in r["所感"].lower()]
    return filtered

def display_report(report):
    with st.expander(f"{report['カテゴリ']} - {report['場所']}"):
        st.write(f"**実施内容:**\n{report['実施内容']}")
        st.write(f"**所感:**\n{report['所感']}")
        if report.get("image"):
            try:
                st.image(base64.b64decode(report["image"]))
            except Exception as e:
                st.error("画像の表示に失敗しました")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button(f"❤️ {report['いいね']}", key=f"like_{report['id']}"):
                update_reaction(report["id"], "いいね")
                st.rerun()
        with col2:
            if st.button(f"💪 {report['ナイスファイト']}", key=f"nice_{report['id']}"):
                update_reaction(report["id"], "ナイスファイト")
                st.rerun()
        
        with st.form(f"comment_form_{report['id']}"):
            comment = st.text_area("コメントを入力")
            if st.form_submit_button("投稿"):
                if comment.strip():
                    save_comment(report["id"], st.session_state.user["name"], comment)
                    st.rerun()
        
        if report["コメント"]:
            st.subheader("コメント")
            for comment in report["コメント"]:
                st.markdown(f"**{comment['投稿者']}** ({comment['日時']}): {comment['コメント']}")

def export_to_excel(data, filename):
    """データをExcelファイルにエクスポート"""
    df = pd.DataFrame(data)
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False)
    return output.getvalue()
    
# 週間予定ページ
def weekly_schedule_page():
    st.title("週間予定管理")
    
    with st.expander("新規作成", expanded=True):
        with st.form("weekly_form"):
            start_date = st.date_input("開始日")
            end_date = st.date_input("終了日")
            days = ["月曜日", "火曜日", "水曜日", "木曜日", "金曜日", "土曜日", "日曜日"]
            schedule = {}
            for day in days:
                schedule[day] = st.text_input(day)
            if st.form_submit_button("保存"):
                schedule_data = {
                    "投稿者": st.session_state.user["name"],
                    "開始日": start_date.strftime("%Y-%m-%d"),
                    "終了日": end_date.strftime("%Y-%m-%d"),
                    **schedule
                }
                save_weekly_schedule(schedule_data)
                st.success("週間予定を保存しました")
    
    st.subheader("既存の予定")
    schedules = load_weekly_schedules()
    for schedule in schedules:
        with st.expander(f"{schedule['開始日']} - {schedule['終了日']}"):
            cols = st.columns(3)
            days = ["月曜日", "火曜日", "水曜日", "木曜日", "金曜日", "土曜日", "日曜日"]
            for i, day in enumerate(days):
                cols[i%3].write(f"**{day}**\n{schedule[day]}")
            
            with st.form(f"comment_weekly_{schedule['id']}"):
                comment = st.text_area("コメント入力")
                if st.form_submit_button("投稿"):
                    if comment.strip():
                        save_weekly_schedule_comment(schedule["id"], st.session_state.user["name"], comment)
                        st.rerun()
            
            if schedule["コメント"]:
                st.subheader("コメント")
                for comment in schedule["コメント"]:
                    st.write(f"**{comment['投稿者']}**: {comment['コメント']}")

if st.button("Excelでエクスポート"):
        schedules = load_weekly_schedules()
        excel_data = export_to_excel([
            {
                "開始日": s["開始日"],
                "終了日": s["終了日"],
                "月曜日": s["月曜日"],
                # ...他の曜日...
                "投稿者": s["投稿者"]
            }
            for s in schedules
        ], "weekly_schedules.xlsx")
        st.download_button(
            label="ダウンロード",
            data=excel_data,
            file_name="週間予定.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    
# お知らせページ
def notice_page():
    st.title("お知らせ")
    notices = load_notices(st.session_state.user["name"])
    
    unread = [n for n in notices if not n["既読"]]
    if unread:
        st.subheader("新着通知")
        for notice in unread:
            with st.container():
                st.markdown(f"### {notice['タイトル']}")
                st.write(notice["内容"])
                if st.button("既読にする", key=f"read_{notice['id']}"):
                    mark_notice_as_read(notice["id"])
                    st.rerun()
    
    read = [n for n in notices if n["既読"]]
    if read:
        with st.expander("過去のお知らせ"):
            for notice in read:
                st.markdown(f"**{notice['タイトル']}**")
                st.caption(notice["日付"])
                st.write(notice["内容"])

# マイページ
def mypage():
    st.title("マイページ")
    
    st.subheader("自分の日報")
    reports = [r for r in load_reports() if r["投稿者"] == st.session_state.user["name"]]
    for report in reports:
        with st.expander(f"{report['実行日']} - {report['カテゴリ']}"):
            display_report(report)
            if st.button("削除", key=f"del_{report['id']}"):
                delete_report(report["id"])
                st.rerun()
    
    st.subheader("コメントした投稿")
    commented = load_commented_reports(st.session_state.user["name"])
    for report in commented:
        with st.expander(f"{report['投稿者']} - {report['実行日']}"):
            display_report(report)

# ページルーティング
def main():
    if st.session_state.user is None:
        login_page()
    else:
        sidebar_navigation()
        {
            "ログイン": login_page,
            "タイムライン": timeline_page,
            "日報投稿": report_post_page,
            "週間予定": weekly_schedule_page,
            "お知らせ": notice_page,
            "マイページ": mypage
        }[st.session_state.page]()

if __name__ == "__main__":
    main()

def advanced_search():
    st.sidebar.subheader("高度な検索")
    with st.sidebar.expander("検索オプション"):
        # 日付範囲
        start_date = st.date_input("開始日", datetime.now() - timedelta(days=30))
        end_date = st.date_input("終了日", datetime.now())
        
        # 投稿者フィルタ
        authors = list(set(r["投稿者"] for r in load_reports()))
        selected_authors = st.multiselect("投稿者", authors)
        
        # いいね数
        min_likes = st.number_input("最低いいね数", min_value=0, value=0)
    
    # 検索実行
    if st.button("検索"):
        conn = get_db_connection()
        try:
            query = """
            SELECT * FROM reports 
            WHERE 投稿日時 BETWEEN %s AND %s
            AND いいね >= %s
            """
            params = [start_date, end_date, min_likes]
            
            if selected_authors:
                query += " AND 投稿者 = ANY(%s)"
                params.append(selected_authors)
            
            cur = conn.cursor()
            cur.execute(query, params)
            results = cur.fetchall()
            
            # 結果表示...
            
        except psycopg2.Error as e:
            st.error(f"検索エラー: {e}")
        finally:
            conn.close()

# インデックス作成
def create_indexes():
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("CREATE INDEX IF NOT EXISTS idx_post_date ON reports (投稿日時)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_author ON reports (投稿者)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_notice_user ON notices (対象ユーザー)")
        conn.commit()
    except psycopg2.Error as e:
        st.error(f"インデックス作成エラー: {e}")
    finally:
        conn.close()

# アプリ起動時に実行
create_indexes()

# キャッシュの活用
@st.cache_data(ttl=300)
def cached_load_reports():
    return load_reports()

@st.cache_data(ttl=300)
def cached_load_schedules():
    return load_weekly_schedules()
    
