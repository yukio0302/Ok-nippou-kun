import sys
import os
import time
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

# サブコーディングから必要な関数をインポート
from db_utils import init_db, authenticate_user, save_report, load_reports, load_notices, mark_notice_as_read, edit_report, delete_report, update_reaction, save_comment

# ✅ SQLite 初期化（データを消さない）
init_db(keep_existing=True)

# ✅ ログイン状態を管理
if "user" not in st.session_state:
    st.session_state["user"] = None
if "page" not in st.session_state:
    st.session_state["page"] = "ログイン"

# ✅ ページ遷移関数（修正済み）
def switch_page(page_name):
    """ページを切り替える（即時リロードはなし！）"""
    st.session_state["page"] = page_name
# ✅ ナビゲーションバー（修正済み）
def top_navigation():
    st.markdown("""
    <style>
        .nav-bar {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            background-color: #ffffff;
            display: grid;
            grid-template-columns: repeat(2, 1fr); /* 2列 */
            gap: 10px;
            padding: 10px;
            border-bottom: 1px solid #ccc;
            box-shadow: 0 2px 5px rgba(0, 0, 0, 0.1);
            z-index: 9999;
        }
        .nav-item {
            text-align: center;
            font-size: 14px;
            padding: 10px;
            cursor: pointer;
            color: #666;
            background-color: #f8f8f8;
            border-radius: 5px;
        }
        .nav-item.active {
            color: black;
            font-weight: bold;
            background-color: #ddd;
        }
        @media (max-width: 600px) {
            .nav-bar {
                grid-template-columns: repeat(2, 1fr); /* スマホでも2列を維持 */
            }
        }
    </style>
    """, unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("⏳ タイムライン"):
            st.session_state.page = "タイムライン"
            st.rerun()
        if st.button("🔔 お知らせ"):
            st.session_state.page = "お知らせ"
            st.rerun()
    with col2:
        if st.button("✏️ 日報投稿"):
            st.session_state.page = "日報投稿"
            st.rerun()
        if st.button("👤 マイページ"):
            st.session_state.page = "マイページ"
            st.rerun()
    
    if "page" not in st.session_state:
        st.session_state.page = "タイムライン"

# ✅ ログイン機能（修正済み）
def login():
    st.title("🔑 ログイン")
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


# ✅ 日報投稿
def post_report():
    if "user" not in st.session_state or st.session_state["user"] is None:
        st.error("ログインしてください。")
        return

    st.title("📝 日報投稿")
    top_navigation()

    category = st.text_input("📋 カテゴリ")
    location = st.text_input("📍 場所")
    content = st.text_area("📝 実施内容")
    remarks = st.text_area("💬 所感")

    submit_button = st.button("📤 投稿する")
    if submit_button:
        save_report({
            "投稿者": st.session_state["user"]["name"],
            "実行日": datetime.utcnow().strftime("%Y-%m-%d"),
            "カテゴリ": category,
            "場所": location,
            "実施内容": content,
            "所感": remarks,
            "コメント": []
        })
        st.success("✅ 日報を投稿しました！")
        time.sleep(1)
        switch_page("タイムライン")

# ✅ タイムライン（コメント機能修正）
def timeline():
    if "user" not in st.session_state or st.session_state["user"] is None:
        st.error("ログインしてください。")
        return

    st.title("📜 タイムライン")
    top_navigation()

    reports = load_reports()
    
 # ✅ 検索ボックス
    search_query = st.text_input("🔍 投稿を検索", "")

    # ✅ 全部署リスト（固定）
    all_departments = ["業務部", "営業部", "企画部", "国際流通", "総務部", "情報統括", "マーケティング室"]

  # ✅ ユーザーの所属部署を取得（エラー防止）
    user_departments = st.session_state["user"].get("depart", [])  # `depart` がなければ空リスト

    # ✅ `depart` が `str` の場合はリスト化
    if isinstance(user_departments, str):
        user_departments = [user_departments]

    print(f"🛠️ デバッグ: user_departments = {user_departments}")  # ← 確認用（デプロイ後は削除）

    # ✅ フィルタ状態をセッションで管理（デフォルトは「全体表示」）
    if "filter_mode" not in st.session_state:
        st.session_state["filter_mode"] = "全体表示"
        st.session_state["selected_department"] = None

    # ✅ フィルタ切り替えボタン
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("🌎 全体表示"):
            st.session_state["filter_mode"] = "全体表示"
            st.session_state["selected_department"] = None
            st.rerun()
    with col2:
        if st.button("🏢 所属部署の投稿を見る"):
            st.session_state["filter_mode"] = "所属部署"
            st.session_state["selected_department"] = None
            st.rerun()
    with col3:
        if st.button("🔍 他の部署の投稿を見る"):
            st.session_state["filter_mode"] = "他の部署"

    # ✅ 他の部署を選ぶセレクトボックス（選択時のみ表示）
    if st.session_state["filter_mode"] == "他の部署":
        selected_department = st.selectbox("📌 表示する部署を選択", all_departments, index=0)
        st.session_state["selected_department"] = selected_department

  # ✅ 投稿の「部署」をリスト化（万が一 `str` や `None` だった場合に対応）
    for report in reports:
        report["部署"] = report.get("部署", [])  # 🔥 `部署` がない場合は空リストをセット
        if not isinstance(report["部署"], list):  # 🔥 `str` だった場合はリスト化
            report["部署"] = [report["部署"]]

   # ✅ フィルタ処理
    if st.session_state["filter_mode"] == "所属部署":
        reports = [report for report in reports if set(report["部署"]) & set(user_departments)]  # 🔥 ここ修正済み
    elif st.session_state["filter_mode"] == "他の部署" and st.session_state["selected_department"]:
        reports = [report for report in reports if st.session_state["selected_department"] in report["部署"]]

    # ✅ 検索フィルタ（フィルタ後のデータに適用）
    if search_query:
        reports = [
            report for report in reports
            if search_query.lower() in report["実施内容"].lower()
            or search_query.lower() in report["所感"].lower()
            or search_query.lower() in report["カテゴリ"].lower()
        ]

    if not reports:
        st.warning("🔎 該当する投稿が見つかりませんでした。")
        return

        
    for report in reports:
        st.subheader(f"{report['投稿者']} さんの日報 ({report['実行日']})")
        st.write(f"🏷 **カテゴリ:** {report['カテゴリ']}")
        st.write(f"📍 **場所:** {report['場所']}")
        st.write(f"📝 **実施内容:** {report['実施内容']}")
        st.write(f"💬 **所感:** {report['所感']}")

        # ✅ いいね！＆ナイスファイト！ボタン
        col1, col2 = st.columns(2)
        with col1:
            if st.button(f"❤️ {report['いいね']} いいね！", key=f"like_{report['id']}"):
                update_reaction(report["id"], "いいね")
                st.rerun()
        with col2:
            if st.button(f"👍 {report['ナイスファイト']} ナイスファイト！", key=f"nice_{report['id']}"):
                update_reaction(report["id"], "ナイスファイト")
                st.rerun()

                  # コメント欄
        comment_count = len(report["コメント"]) if report["コメント"] else 0  # コメント件数を取得
        with st.expander(f"💬 ({comment_count}件)のコメントを見る・追加する "):  # 件数を表示
            if report["コメント"]:
                for c in report["コメント"]:
                    st.write(f"👤 {c['投稿者']} ({c['日時']}): {c['コメント']}")

            if report.get("id") is None:
                st.error("⚠️ 投稿の ID が見つかりません。")
                continue

            commenter_name = st.session_state["user"]["name"] if st.session_state["user"] else "匿名"
            new_comment = st.text_area(f"✏️ {commenter_name} さんのコメント", key=f"comment_{report['id']}")

            if st.button("📤 コメントを投稿", key=f"submit_comment_{report['id']}"):
                if new_comment and new_comment.strip():
                    current_time = datetime.now() + timedelta(hours=9, minutes=1)
                    # 時間を適切なフォーマットに変換
            formatted_time = current_time.strftime("%Y-%m-%d %H:%M:%S")

            # デバッグ用の出力
            print(f"🛠️ コメント投稿デバッグ: report_id={report['id']}, commenter={commenter_name}, comment={new_comment}, time={formatted_time}")
                    save_comment(report["id"], commenter_name, new_comment)
                    st.success("✅ コメントを投稿しました！")
                    st.rerun()
                else:
                    st.warning("⚠️ 空白のコメントは投稿できません！")

st.write("----")

# ✅ お知らせ
def show_notices():
    if "user" not in st.session_state or st.session_state["user"] is None:
        st.error("ログインしてください。")
        return

    st.title("🔔 お知らせ")
    top_navigation()

    notices = load_notices()

    for notice in notices:
        status = "未読" if notice["既読"] == 0 else "既読"
        st.subheader(f"{notice['タイトル']} - {status}")
        st.write(f"📅 {notice['日付']}")
        st.write(f"{notice['内容']}")
        if notice["既読"] == 0:
            if st.button(f"既読にする ({notice['id']})"):
                mark_notice_as_read(notice["id"])
                st.experimental_rerun()

# ✅ マイページ
def my_page():
    if "user" not in st.session_state or st.session_state["user"] is None:
        st.error("ログインしてください。")
        return

    st.title("👤 マイページ")
    top_navigation()

    reports = load_reports()
    my_reports = [r for r in reports if r["投稿者"] == st.session_state["user"]["name"]]

    st.subheader("📅 今週の投稿")
    now = datetime.utcnow()
    start_of_week = now - timedelta(days=now.weekday())
    end_of_week = start_of_week + timedelta(days=4)
    weekly_reports = [r for r in my_reports if start_of_week.date() <= datetime.strptime(r["実行日"], "%Y-%m-%d").date() <= end_of_week.date()]

    for report in weekly_reports:
        st.write(f"- {report['実行日']}: {report['カテゴリ']} / {report['場所']}")

# ✅ メニュー管理
if st.session_state["user"] is None:
    login()
else:
    if st.session_state["page"] == "タイムライン":
        timeline()
    elif st.session_state["page"] == "日報投稿":
        post_report()
    elif st.session_state["page"] == "お知らせ":
        show_notices()
    elif st.session_state["page"] == "マイページ":
        my_page()
