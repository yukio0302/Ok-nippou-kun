import streamlit as st
from datetime import datetime, timedelta
import os
import json

# 初期設定
st.set_page_config(page_title="日報管理システム", layout="wide")

# JSONファイルのパス
data_file = "reports_data.json"  # 投稿データ
user_file = "users_data.json"    # ユーザーデータ

# セッション永続化の保持時間（1週間）
SESSION_DURATION = timedelta(days=7)

# データの永続化関数
def load_data(file_path):
    """ファイルからデータを読み込む"""
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def save_data(file_path, data):
    """データをファイルに保存する"""
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


# セッションデータの初期化
if "user" not in st.session_state:
    st.session_state["user"] = None

if "reports" not in st.session_state:
    st.session_state["reports"] = load_data(data_file)  # 投稿データを読み込む

if "users" not in st.session_state:
    st.session_state["users"] = load_data(user_file)    # ユーザーデータを読み込む

if "last_login" not in st.session_state:
    st.session_state["last_login"] = None

if "notifications" not in st.session_state:
    st.session_state["notifications"] = []


# ログイン画面
def login():
    st.title("ログイン")
    employee_code = st.text_input("社員コード", key="employee_code_input")
    password = st.text_input("パスワード", type="password", key="password_input")
    login_button = st.button("ログイン", key="login_button")

    if login_button:
        # ユーザーデータから検索
        user = next(
            (u for u in st.session_state["users"] if u["code"] == employee_code and u["password"] == password),
            None,
        )

        if user:
            st.session_state.user = user
            st.session_state.last_login = datetime.now()
            st.success(f"ログイン成功！ようこそ、{user['name']}さん！")
        else:
            st.error("社員コードまたはパスワードが間違っています。")


# 名前アイコン作成
def create_name_icon(name):
    """名前から丸いアイコンを生成する"""
    initials = "".join([part[0] for part in name.split()]).upper()  # 頭文字を取得
    st.markdown(
        f"""
        <div style="
            display: inline-block;
            width: 50px;
            height: 50px;
            background-color: #007bff;
            border-radius: 50%;
            color: white;
            text-align: center;
            line-height: 50px;
            font-weight: bold;
            font-size: 20px;
        ">
            {initials}
        </div>
        """,
        unsafe_allow_html=True,
    )


# タイムライン
def timeline():
    st.title("タイムライン")

    # 検索機能
    search_query = st.text_input("検索", placeholder="タグやカテゴリ、内容で検索", key="search_query")

    # 表示期間フィルター
    now = datetime.now()
    filter_option = st.radio(
        "表示期間",
        ["24時間以内", "3日以内", "5日以内"],
        horizontal=True,
        key="filter_option",
    )

    days_filter = {"24時間以内": 1, "3日以内": 3, "5日以内": 5}.get(filter_option, 5)
    cutoff_date = now - timedelta(days=days_filter)

    # フィルター適用
    reports = [
        report
        for report in st.session_state["reports"]
        if datetime.strptime(report["投稿日時"], "%Y-%m-%d %H:%M") >= cutoff_date
        and (not search_query or search_query in report["タグ"] or search_query in report["カテゴリ"] or search_query in report["実施内容"])
    ]

    if not reports:
        st.info("該当する投稿がありません。")
        return

    for report_index, report in enumerate(reversed(reports)):
        with st.container():
            st.markdown("---")
            # 名前アイコンを表示
            create_name_icon(report["投稿者"])

            # 投稿内容を表示
            st.subheader(f"{report['投稿者']} さんの投稿")
            st.write(f"カテゴリ: **{report['カテゴリ']}**")
            st.write(f"投稿日時: {report['投稿日時']}")
            if report["得意先"]:
                st.write(f"得意先: {report['得意先']}")
            if report["タグ"]:
                st.write(f"タグ: {report['タグ']}")
            st.write(f"実施内容: {report['実施内容']}")
            if report["所感・備考"]:
                st.write(f"所感・備考: {report['所感・備考']}")

            # スタンプ機能
            col1, col2 = st.columns(2)
            with col1:
                if st.button(f"👍 いいね！ ({len(report.get('いいね', []))})", key=f"like_{report_index}"):
                    if st.session_state.user["name"] not in report.get("いいね", []):
                        report.setdefault("いいね", []).append(st.session_state.user["name"])
                        save_data(data_file, st.session_state["reports"])
            with col2:
                if st.button(f"🔥 ナイスファイト！ ({len(report.get('ナイスファイト', []))})", key=f"fight_{report_index}"):
                    if st.session_state.user["name"] not in report.get("ナイスファイト", []):
                        report.setdefault("ナイスファイト", []).append(st.session_state.user["name"])
                        save_data(data_file, st.session_state["reports"])

            # リアクション詳細（投稿者のみ）
            if st.session_state.user["name"] == report["投稿者"]:
                with st.expander("リアクション詳細"):
                    st.write("👍 いいね！:")
                    st.write(", ".join(report.get("いいね", [])) or "なし")
                    st.write("🔥 ナイスファイト！:")
                    st.write(", ".join(report.get("ナイスファイト", [])) or "なし")


# 日報投稿フォーム
def post_report():
    st.title("日報投稿")

    with st.form("report_form"):
        category = st.selectbox("カテゴリ", ["営業活動", "社内作業", "その他"], key="category")
        client = st.text_input("得意先", key="client") if category == "営業活動" else ""
        tags = st.text_input("タグ", placeholder="#案件, #改善提案 など", key="tags")
        content = st.text_area("実施内容", placeholder="実施した内容を記入してください", key="content")
        notes = st.text_area("所感・備考", placeholder="所感や備考を記入してください（任意）", key="notes")

        submit = st.form_submit_button("投稿")

        if submit:
            if not content:
                st.error("実施内容は必須項目です。")
            else:
                post = {
                    "投稿者": st.session_state.user["name"],
                    "カテゴリ": category,
                    "得意先": client,
                    "タグ": tags,
                    "実施内容": content,
                    "所感・備考": notes,
                    "投稿日時": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "いいね": [],
                    "ナイスファイト": []
                }
                st.session_state["reports"].append(post)
                save_data(data_file, st.session_state["reports"])  # 投稿データをファイルに保存
                st.success("日報を投稿しました！")


# マイページ
def my_page():
    st.title("マイページ")
    st.subheader("投稿の管理")

    user_reports = [r for r in st.session_state["reports"] if r["投稿者"] == st.session_state.user["name"]]

    if not user_reports:
        st.info("まだ投稿がありません。")
        return

    for report in reversed(user_reports):
        with st.container():
            st.markdown("---")
            st.subheader(f"カテゴリ: {report['カテゴリ']} - {report['投稿日時']}")
            if report["得意先"]:
                st.write(f"得意先: {report['得意先']}")
            if report["タグ"]:
                st.write(f"タグ: {report['タグ']}")
            st.write(f"実施内容: {report['実施内容']}")
            if report["所感・備考"]:
                st.write(f"所感・備考: {report['所感・備考']}")

            # 編集・削除ボタン
            col1, col2 = st.columns(2)
            with col1:
                if st.button("編集", key=f"edit_{report['投稿日時']}"):
                    edited_content = st.text_area("編集内容", report["実施内容"], key=f"edit_content_{report['投稿日時']}")
                    edited_notes = st.text_area("編集所感・備考", report["所感・備考"], key=f"edit_notes_{report['投稿日時']}")
                    if st.button("保存", key=f"save_{report['投稿日時']}"):
                        report["実施内容"] = edited_content
                        report["所感・備考"] = edited_notes
                        save_data(data_file, st.session_state["reports"])
                        st.success("投稿を編集しました！")
                        st.experimental_rerun()
            with col2:
                if st.button("削除", key=f"delete_{report['投稿日時']}"):
                    st.session_state["reports"].remove(report)
                    save_data(data_file, st.session_state["reports"])
                    st.success("投稿を削除しました！")
                    st.experimental_rerun()


# お知らせ
def notifications():
    st.title("お知らせ")
    if not st.session_state["notifications"]:
        st.info("お知らせはありません。")
        return

    for notification in reversed(st.session_state["notifications"]):
        with st.container():
            st.write(notification)
            st.markdown("---")


# メイン処理
if st.session_state.user is None:
    if st.session_state.last_login and datetime.now() - st.session_state.last_login < SESSION_DURATION:
        st.session_state.user = {"code": "901179", "name": "野村幸男"}
    else:
        login()
else:
    menu = st.sidebar.radio("メニュー", ["タイムライン", "日報投稿", "マイページ", "お知らせ"])
    if menu == "タイムライン":
        timeline()
    elif menu == "日報投稿":
        post_report()
    elif menu == "マイページ":
        my_page()
    elif menu == "お知らせ":
        notifications()
