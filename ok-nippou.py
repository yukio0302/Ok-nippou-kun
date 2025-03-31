import streamlit as st
import pandas as pd
import base64
from datetime import datetime, timedelta
import json
import sqlite3
from collections import defaultdict
import logging
import db_utils
import excel_utils

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

DB_PATH = "/mount/src/ok-nippou-kun/data/reports.db"

def load_css(file_name):
    with open(file_name) as f:
        st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

load_css("style.css")

if "user" not in st.session_state:
    st.session_state["user"] = None
if "page" not in st.session_state:
    st.session_state["page"] = "ログイン"

def switch_page(page_name):
    st.session_state["page"] = page_name

def sidebar_navigation():
    with st.sidebar:
        st.image("OK-Nippou5.png", use_container_width=True)
        st.markdown("""<style> .stImage { margin-bottom: 30px !important; } .sidebar-menu { color: white !important; margin-bottom: 30px; } </style>""", unsafe_allow_html=True)
        if st.button("⏳ タイムライン", key="sidebar_timeline"): switch_page("タイムライン")
        if st.button(" 週間予定", key="sidebar_weekly"): switch_page("週間予定")
        if st.button(" お知らせ", key="sidebar_notice"): switch_page("お知らせ")
        if st.button("✈️ 週間予定投稿", key="sidebar_post_schedule"): switch_page("週間予定投稿")
        if st.button(" 日報作成", key="sidebar_post_report"): switch_page("日報投稿")
        if st.button(" マイページ", key="sidebar_mypage"): switch_page("マイページ")

def login():
    col1, col2, col3 = st.columns([1, 3, 1])
    with col2: st.image("OK-Nippou4.png", use_container_width=True)
    st.title(" ログイン")
    employee_code = st.text_input("社員コード")
    password = st.text_input("パスワード", type="password")
    if st.button("ログイン"):
        user = db_utils.authenticate_user(employee_code, password)
        if user:
            st.session_state["user"] = user
            st.success(f"ようこそ、{user['name']} さん！（{', '.join(user['depart'])}）")
            st.session_state["page"] = "タイムライン"
            st.rerun()
        else:
            st.error("社員コードまたはパスワードが間違っています。")

def save_weekly_schedule(schedule):
    schedule["投稿日時"] = (datetime.now() + timedelta(hours=9)).strftime("%Y-%m-%d %H:%M:%S")
    db_utils.save_weekly_schedule(schedule)
    st.success("✅ 週間予定を投稿しました！")
    st.session_state["page"] = "タイムライン"

def post_weekly_schedule():
    if not st.session_state["user"]: st.error("ログインしてください。"); return
    st.title("週間予定投稿")
    def generate_week_options():
        today = datetime.today().date(); options = []
        for i in range(-4, 5):
            start = today - timedelta(days=today.weekday()) + timedelta(weeks=i); end = start + timedelta(days=6)
            options.append((start, end, f"{start.month}/{start.day}（月）～{end.month}/{end.day}（日）"))
        return options
    week_options = generate_week_options(); start_date, end_date, _ = st.selectbox("該当週を選択", options=week_options, format_func=lambda x: x[2], index=4)
    weekly_plan = { (start_date + timedelta(days=i)).strftime("%Y-%m-%d"): st.text_input(f"{start_date.month}月{start_date.day + i}日（{['月', '火', '水', '木', '金', '土', '日'][i]}） の予定", key=f"plan_{start_date + timedelta(days=i)}") for i in range(7) }
    if st.button("投稿する"):
        schedule = { "投稿者": st.session_state["user"]["name"], "開始日": start_date.strftime("%Y-%m-%d"), "終了日": end_date.strftime("%Y-%m-%d"), **{ ["月曜日", "火曜日", "水曜日", "木曜日", "金曜日", "土曜日", "日曜日"][i]: weekly_plan[(start_date + timedelta(days=i)).strftime("%Y-%m-%d")] for i in range(7) } }
        save_weekly_schedule(schedule)

def show_weekly_schedules():
    if not st.session_state["user"]: st.error("ログインしてください。"); return
    st.title("週間予定")
    st.markdown("""<style> .nested-expander { border-left: 3px solid #f0f2f6; margin-left: 1rem; padding-left: 1rem; } .week-header { cursor: pointer; padding: 0.5rem; background-color: #f0f2f6; border-radius: 0.5rem; margin: 0.5rem 0; transition: background-color 0.3s ease, max-height 0.3s ease; overflow: hidden; } .week-header:hover { background-color: #e0e0e0; } .week-header.expanded { max-height: none; } .week-content { overflow: hidden; transition: max-height 0.3s ease; } </style>""", unsafe_allow_html=True)
    schedules = db_utils.load_weekly_schedules()
    if not schedules: st.info("週間予定はありません。"); return
    grouped = defaultdict(list); [grouped[(s['開始日'], s['終了日'])].append(s) for s in schedules]
    sorted_groups = sorted(grouped.items(), key=lambda x: datetime.strptime(x[0][0], "%Y-%m-%d"), reverse=True)
    six_weeks_ago = datetime.now() - timedelta(weeks=6)
    recent_schedules = [(start_end, group_schedules) for start_end, group_schedules in sorted_groups if datetime.strptime(start_end[0], "%Y-%m-%d") >= six_weeks_ago]
    past_schedules = [(start_end, group_schedules) for start_end, group_schedules in sorted_groups if datetime.strptime(start_end[0], "%Y-%m-%d") < six_weeks_ago]
    st.subheader("直近5週分の予定"); display_schedules(recent_schedules)
    if past_schedules: st.subheader("過去の予定を見る（6週間以前）"); display_past_schedules(past_schedules)
    if schedules and st.button("週間予定をExcelでダウンロード"):
        excel_file = excel_utils.download_weekly_schedule_excel(schedules[0]["開始日"], schedules[0]["終了日"])
        st.download_button(label="ダウンロード", data=excel_file, file_name="週間予定.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

def display_schedules(schedules_to_display):
    for idx, ((start_str, end_str), group_schedules) in enumerate(schedules_to_display):
        start_date, end_date = datetime.strptime(start_str, "%Y-%m-%d"), datetime.strptime(end_str, "%Y-%m-%d")
        group_title = f"{start_date.month}月{start_date.day}日（{['月', '火', '水', '木', '金', '土', '日'][start_date.weekday()]}） ～ {end_date.month}月{end_date.day}日（{['月', '火', '水', '木', '金', '土', '日'][end_date.weekday()]}）"
        if f'week_{idx}_expanded' not in st.session_state: st.session_state[f'week_{idx}_expanded'] = False
        if st.button(f" {group_title} {'▼' if st.session_state[f'week_{idx}_expanded'] else '▶'}", key=f'week_header_{idx}', use_container_width=True):
            st.session_state[f'week_{idx}_expanded'] = not st.session_state[f'week_{idx}_expanded']
        if st.session_state[f'week_{idx}_expanded']:
            with st.container():
                st.markdown('<div class="nested-expander">', unsafe_allow_html=True)
                for schedule in group_schedules:
                    with st.expander(f"{schedule['投稿者']} さんの週間予定 ▽"):
                        days = [start_date + timedelta(days=i) for i in range(7)]
                        [st.write(f"**{days[i].month}月{days[i].day}日（{['月', '火', '水', '木', '金', '土', '日'][i]}）**: {schedule[['月曜日', '火曜日', '水曜日', '木曜日', '金曜日', '土曜日', '日曜日'][i]]}") for i in range(7)]
                        st.write(f"**投稿日時:** {schedule['投稿日時']}"); st.markdown("---"); st.subheader("コメント")
                        if schedule["コメント"]: [st.write(f"- {comment['投稿者']} ({comment['日時']}): {comment['コメント']}") for comment in schedule["コメント"]]
                        else: st.write("まだコメントはありません。")
                        comment_text = st.text_area(f"コメントを入力 (ID: {schedule['id']})", key=f"comment_{schedule['id']}");
                        if st.button(f"コメントを投稿", key=f"submit_{schedule['id']}"):
                            if comment_text.strip(): db_utils.save_weekly_schedule_comment(schedule["id"], st.session_state["user"]["name"], comment_text); st.rerun()
                            else: st.warning("コメントを入力してください。")
                st.markdown('</div>', unsafe_allow_html=True)

def display_past_schedules(past_schedules):
    monthly_grouped = defaultdict(lambda: defaultdict(list))
    [monthly_grouped[datetime.strptime(start_str, "%Y-%m-%d").year][datetime.strptime(start_str, "%Y-%m-%d").month].append(((start_str, end_str), group_schedules)) for (start_str, end_str), group_schedules in past_schedules]
    for year in sorted(monthly_grouped.keys(), reverse=True):
        st.markdown(f"├─ {year}年{'' if len(monthly_grouped[year]) > 1 else ' '}{list(monthly_grouped[year].keys())[0] if len(monthly_grouped[year]) == 1 else ''}")
        for month in sorted(monthly_grouped[year].keys(), reverse=True):
            st.markdown(f"│ ├─ {month}月")
            for (start_str, end_str), group_schedules in sorted(monthly_grouped[year][month], key=lambda x: x[0][0], reverse=True):
                start_date, end_date = datetime.strptime(start_str, "%Y-%m-%d"), datetime.strptime(end_str, "%Y-%m-%d")
                st.markdown(f"│ │ ├─ {start_date.month}/{start_date.day} ({['月', '火', '水', '木', '金', '土', '日'][start_date.weekday()]})～{end_date.month}/{end_date.day} ({['月', '火', '水', '木', '金', '土', '日'][end_date.weekday()]})")
                st.markdown('│ │ │ <div class="nested-expander">', unsafe_allow_html=True)
                for schedule in group_schedules:
                    with st.expander(f"{schedule['投稿者']} さんの週間予定 ▽"):
                        days = [start_date + timedelta(days=i) for i in range(7)]
                        [st.write(f"**{days[i].month}月{days[i].day}日（{['月', '火', '水', '木', '金', '土', '日'][i]}）**: {schedule[['月曜日', '火曜日', '水曜日', '木曜日', '金曜日', '土曜日', '日曜日'][i]]}") for i in range(7)]
                        st.write(f"**投稿日時:** {schedule['投稿日時']}"); st.markdown("---"); st.subheader("コメント")
                        if schedule["コメント"]: [st.write(f"- {comment['投稿者']} ({comment['日時']}): {comment['コメント']}") for comment in schedule["コメント"]]
                        else: st.write("まだコメントはありません。")
                        comment_text = st.text_area(f"コメントを入力 (ID: {schedule['id']})", key=f"comment_{schedule['id']}");
                        if st.button(f"コメントを投稿", key=f"submit_{schedule['id']}"):
                            if comment_text.strip(): db_utils.save_weekly_schedule_comment(schedule["id"], st.session_state["user"]["name"], comment_text); st.rerun()
                            else: st.warning("コメントを入力してください。")
                st.markdown('</div>', unsafe_allow_html=True)

def show_timeline():
    if not st.session_state["user"]: st.error("ログインしてください。"); return
    st.title("タイムライン")
    st.sidebar.subheader("表示期間を選択")
    st.markdown("""<style> div[data-baseweb="radio"] label { color: white !important; } .stSidebar .stSubheader { color: white !important; } </style>""", unsafe_allow_html=True)
    period_option = st.sidebar.radio("表示する期間を選択", ["24時間以内の投稿", "1週間以内の投稿", "過去の投稿"], index=0, key="timeline_period_selector")
    now_jst = datetime.now() + timedelta(hours=9)
    if period_option == "24時間以内の投稿": start_datetime, end_datetime = now_jst - timedelta(hours=24), now_jst
    elif period_option == "1週間以内の投稿": start_datetime, end_datetime = now_jst - timedelta(days=7), now_jst
    else:
        st.sidebar.subheader("過去の投稿を表示"); col1, col2 = st.sidebar.columns(2)
        with col1: start_date = st.date_input("開始日", now_jst.date() - timedelta(days=365), max_value=now_jst.date() - timedelta(days=1))
        with col2: end_date = st.date_input("終了日", now_jst.date() - timedelta(days=1), min_value=start_date, max_value=now_jst.date() - timedelta(days=1))
        start_datetime, end_datetime = datetime(start_date.year, start_date.month, start_date.day), datetime(end_date.year, end_date.month, end_date.day) + timedelta(days=1)
    filtered_reports = [report for report in db_utils.load_reports() if start_datetime <= datetime.strptime(report["投稿日時"], "%Y-%m-%d %H:%M:%S") <= end_datetime]
    user_departments = st.session_state["user"]["depart"]
    if "filter_department" not in st.session_state: st.session_state["filter_department"] = "すべて"
    col1, col2 = st.columns(2);
    if col1.button(" すべての投稿を見る"): st.session_state["filter_department"] = "すべて"; st.rerun()
    if col2.button(" 自分の部署のメンバーの投稿を見る"): st.session_state["filter_department"] = "自分の部署"; st.rerun()
    if st.session_state["filter_department"] == "自分の部署":
        try:
            with open("data/users_data.json", "r", encoding="utf-8-sig") as file: users = json.load(file)
            department_members = {user["name"] for user in users if any(dept in user_departments for dept in user["depart"])}
            filtered_reports = [report for report in filtered_reports if report["投稿者"] in department_members]
        except Exception as e: st.error(f"⚠️ 部署情報の読み込みエラー: {e}"); return
    search_query = st.text_input("投稿を検索", "");
    if search_query: filtered_reports = [report for report in filtered_reports if search_query.lower() in report["実施内容"].lower() or search_query.lower() in report["所感"].lower() or search_query.lower() in report["カテゴリ"].lower() or search_query.lower() in report["投稿者"].lower()]
    if not filtered_reports: st.warning("該当する投稿が見つかりませんでした。"); return
    for report in filtered_reports:
        st.subheader(f"{report['投稿者']} さんの日報 ({report['実行日']})");
        st.write(f"**実施日:** {report['実行日']}"); st.write(f"**場所:** {report['場所']}"); st.write(f"**実施内容:** {report['実施内容']}"); st.write(f"**所感:** {report['所感']}");
        if report.get("image"):
            try: st.image(base64.b64decode(report["image"]), caption="投稿画像", use_container_width=True)
            except Exception as e: st.error(f"⚠️ 画像の表示中にエラーが発生しました: {e}")
        col1, col2 = st.columns(2);
        if col1.button(f"❤️ {report['いいね']} いいね！", key=f"like_{report['id']}"): db_utils.update_reaction(report["id"], "いいね"); st.rerun()
        if col2.button(f" {report['ナイスファイト']} ナイスファイト！", key=f"nice_{report['id']}"): db_utils.update_reaction(report["id"], "ナイスファイト"); st.rerun()
        with st.expander(f"({len(report['コメント']) if report['コメント'] else 0}件)のコメントを見る・追加する"):
            if report["コメント"]: [st.write(f"{c['投稿者']} ({c['日時']}): {c['コメント']}") for c in report["コメント"]]
            if report.get("id") is None: st.error("⚠️ 投稿のIDが見つかりません。"); continue
            commenter_name = st.session_state["user"]["name"] if st.session_state["user"] else "匿名"
            new_comment = st.text_area(f"✏️ {commenter_name} さんのコメント", key=f"comment_{report['id']}");
            if st.button("コメントを投稿", key=f"submit_comment_{report['id']}"):
                if new_comment and new_comment.strip(): db_utils.save_comment(report["id"], commenter_name, new_comment); st.success("✅ コメントを投稿しました！"); st.rerun()
                else: st.warning("⚠️ 空白のコメントは投稿できません！")
        st.write("----")

def post_report():
    if not st.session_state["user"]: st.error("ログインしてください。"); return
    st.title("日報作成")
    report_date = st.date_input("実行日", datetime.now() + timedelta(hours=9))
    location = st.text_input("場所"); category = st.text_input("カテゴリ"); content = st.text_area("実施内容"); remarks = st.text_area("所感")
    uploaded_file = st.file_uploader("画像をアップロード", type=["png", "jpg", "jpeg"]); image_data = base64.b64encode(uploaded_file.getvalue()).decode("utf-8") if uploaded_file else None
    if st.button("投稿"): db_utils.save_report({ "投稿者": st.session_state["user"]["name"], "実行日": report_date.strftime("%Y-%m-%d"), "場所": location, "カテゴリ": category, "実施内容": content, "所感": remarks, "image": image_data }); st.success("✅ 日報を投稿しました！"); st.session_state["page"] = "タイムライン"

def show_notices():
    if not st.session_state["user"]: st.error("ログインしてください。"); return
    st.title("お知らせ")
    notices = db_utils.load_notices(st.session_state["user"]["name"])
    if not notices: st.info("現在お知らせはありません。"); return
    for notice in notices:
        col1, col2 = st.columns([0.8, 0.2]);
        with col1: st.subheader(notice["タイトル"]); st.write(notice["内容"]); st.write(f"投稿日時: {notice['日付']}")
        with col2:
            if not notice["既読"] and st.button("既読にする", key=f"read_{notice['id']}"): db_utils.mark_notice_as_read(notice["id"]); st.rerun()
        st.write("---")

def show_mypage():
    if not st.session_state["user"]: st.error("ログインしてください。"); return
    st.title("マイページ")
    user = st.session_state["user"]; st.write(f"**名前:** {user['name']}"); st.write(f"**社員コード:** {user['code']}"); st.write(f"**部署:** {', '.join(user['depart'])}")
    my_reports = [r for r in db_utils.load_reports() if r["投稿者"] == user["name"]]; st.subheader("あなたの投稿した日報")
    if my_reports: [st.write(f"- {report['実行日']}: {report['実施内容']}") for report in my_reports]
    else: st.info("投稿した日報はありません。")
    commented_reports = db_utils.load_commented_reports(user["name"]); st.subheader("あなたがコメントした投稿")
    if commented_reports: [st.write(f"- {report['実行日']}: {report['実施内容']}") for report in commented_reports]
    else: st.info("コメントした投稿はありません。")

def main():
    db_utils.init_db(keep_existing=True); db_utils.add_comments_column()
    if st.session_state["user"] is None: login()
    else:
        sidebar_navigation()
        { "タイムライン": show_timeline, "日報投稿": post_report, "お知らせ": show_notices, "マイページ": show_mypage, "週間予定投稿": post_weekly_schedule, "週間予定": show_weekly_schedules }[st.session_state["page"]]()

if __name__ == "__main__": main()
