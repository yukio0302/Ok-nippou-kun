import sys
import os
import time
import streamlit as st
import pandas as pd
import base64
from datetime import datetime, timedelta

# ヘルパー関数: 現在時刻に9時間を加算する
def get_current_time():
    return datetime.now() + timedelta(hours=9)  # JSTで現在時刻を取得

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
        if st.button(" お知らせ"):
            st.session_state.page = "お知らせ"
            st.rerun()
    with col2:
        if st.button("✏️ 日報投稿"):
            st.session_state.page = "日報投稿"
            st.rerun()
        if st.button(" マイページ"):
            st.session_state.page = "マイページ"
            st.rerun()

    if "page" not in st.session_state:
        st.session_state.page = "タイムライン"

# ✅ ログイン機能（修正済み）
def login():
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

# ✅ 日報投稿
def post_report():
    if "user" not in st.session_state or st.session_state["user"] is None:
        st.error("ログインしてください。")
        return

    st.title("日報投稿")
    top_navigation()

    category = st.text_input("実施日")
    location = st.text_input("場所")
    content = st.text_area("実施内容")
    remarks = st.text_area("所感")

    uploaded_file = st.file_uploader("写真を選択", type=["png", "jpg", "jpeg"])
    image_base64 = None
    if uploaded_file is not None:
        image_bytes = uploaded_file.getvalue()
        image_base64 = base64.b64encode(image_bytes).decode('utf-8')

    submit_button = st.button("投稿する")
    if submit_button:
        save_report({
            "投稿者": st.session_state["user"]["name"],
            "実行日": datetime.now().strftime("%Y-%m-%d"),
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
    top_navigation()

    reports = load_reports()

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
            reports = [report for report in reports if report["投稿者"] in department_members]
        
        except Exception as e:
            st.error(f"⚠️ 部署情報の読み込みエラー: {e}")
            return
    search_query = st.text_input(" 投稿を検索", "")

    if search_query:
        reports = [
            report for report in reports
            if search_query.lower() in report["実施内容"].lower()
            or search_query.lower() in report["所感"].lower()
            or search_query.lower() in report["カテゴリ"].lower()
        ]

    if not reports:
        st.warning(" 該当する投稿が見つかりませんでした。")
        return

    for report in reports:
        st.subheader(f"{report['投稿者']} さんの日報 ({report['実行日']})")
        st.write(f" **実施日:** {report['カテゴリ']}")
        st.write(f" **場所:** {report['場所']}")
        st.write(f" **実施内容:** {report['実施内容']}")
        st.write(f" **所感:** {report['所感']}")

        col1, col2 = st.columns(2)
        with col1:
            if st.button(f"❤️ {report['いいね']} いいね！", key=f"like_{report['id']}"):
                update_reaction(report["id"], "いいね")
                st.rerun()
        with col2:
            if st.button(f" {report['ナイスファイト']} ナイスファイト！", key=f"nice_{report['id']}"):
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
    top_navigation()

    notices = load_notices()

    if not notices:
        st.info(" お知らせはありません。")
        return

    # ✅ 未読・既読を分類
    new_notices = [n for n in notices if n["既読"] == 0]
    old_notices = [n for n in notices if n["既読"] == 1]

    # ✅ 既読処理をセッションで管理
    if "notice_to_read" not in st.session_state:
        st.session_state["notice_to_read"] = None

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
    top_navigation()

    reports = load_reports()
    my_reports = [r for r in reports if r["投稿者"] == st.session_state["user"]["name"]]

    st.subheader("今週の投稿")
    now = datetime.utcnow()
    start_of_week = now - timedelta(days=now.weekday())
    end_of_week = start_of_week + timedelta(days=4)
    
    weekly_reports = [
        r for r in my_reports
        if start_of_week.date() <= datetime.strptime(r["実行日"], "%Y-%m-%d").date() <= end_of_week.date()
    ]

    # 🔹 今週の投稿を表示
    if weekly_reports:
        for report in weekly_reports:
            with st.expander(f"{report['実行日']}: {report['カテゴリ']} / {report['場所']}"):
                show_report_details(report)

    past_reports = [r for r in my_reports if r not in weekly_reports]

    # 🔹 過去の投稿を折りたたみ表示
    if past_reports:
        with st.expander("過去の投稿"):
            for report in past_reports:
                with st.expander(f"{report['実行日']}: {report['カテゴリ']} / {report['場所']}"):
                    show_report_details(report)
    else:
        st.info("過去の投稿はありません。")


# ✅ 投稿詳細（編集・削除機能付き）
def show_report_details(report):
    """投稿の詳細を表示し、編集・削除機能を提供"""
    st.write(f"**実施日:** {report['実行日']}")
    st.write(f"**場所:** {report['場所']}")
    st.write(f"**実施内容:** {report['実施内容']}")
    st.write(f"**所感:** {report['所感']}")

    # 🔹 コメント一覧
    if report.get("コメント"):
        st.subheader("🗨️ コメント一覧")
        for c in report["コメント"]:
            st.write(f"{c['投稿者']} ({c['日時']}): {c['コメント']}")

    # 🔹 編集 & 削除ボタン
    col1, col2 = st.columns(2)
    with col1:
        if st.button("✏️ 編集する", key=f"edit_btn_{report['id']}"):
            st.session_state[f"edit_mode_{report['id']}"] = True  # 編集モードをON

    with col2:
        if st.button("🗑️ 削除する", key=f"delete_btn_{report['id']}"):
            st.session_state[f"confirm_delete_{report['id']}"] = True  # 削除確認モードをON

    # 🔹 削除確認
    if st.session_state.get(f"confirm_delete_{report['id']}", False):
        st.warning("⚠️ 本当に削除しますか？")

        col_confirm, col_cancel = st.columns(2)
        with col_confirm:
            if st.button("✅ はい、削除する", key=f"confirm_delete_btn_{report['id']}"):
                delete_report(report["id"])
                st.success("✅ 削除しました")
                st.rerun()  # 画面を更新

        with col_cancel:
            if st.button("❌ キャンセル", key=f"cancel_delete_btn_{report['id']}"):
                st.session_state[f"confirm_delete_{report['id']}"] = False  # 削除確認モードをOFF

    # 🔹 編集モード
    if st.session_state.get(f"edit_mode_{report['id']}", False):
        edit_report_form(report)



# ✅ 編集フォーム
def edit_report_form(report):
    """投稿の編集フォーム"""
    new_date = st.text_input("実施日", report["実行日"])
    new_location = st.text_input("場所", report["場所"])
    new_content = st.text_area("実施内容", report["実施内容"])
    new_remarks = st.text_area("所感", report["所感"])

    if st.button("💾 保存", key=f"save_{report['id']}"):
        edit_report(report["id"], new_date, new_location, new_content, new_remarks)
        st.session_state[f"edit_mode_{report['id']}"] = False  # 編集モード終了
        st.success("✅ 編集を保存しました")
        st.rerun()
    
    if st.button("キャンセル", key=f"cancel_{report['id']}"):
        st.session_state[f"edit_mode_{report['id']}"] = False  # 編集モード終了
        st.rerun()

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
