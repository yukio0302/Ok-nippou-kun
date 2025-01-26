import streamlit as st
from datetime import datetime
import json
import os

# ファイルパス
USERS_FILE = "users_data.json"
REPORTS_FILE = "reports_data.json"

# 初期設定
st.set_page_config(page_title="日報管理システム", layout="wide")

# ユーザーデータをロード
def load_users():
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

# 投稿データをロード
def load_reports():
    if os.path.exists(REPORTS_FILE):
        with open(REPORTS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

# 投稿データを保存
def save_reports(reports):
    with open(REPORTS_FILE, "w", encoding="utf-8") as f:
        json.dump(reports, f, ensure_ascii=False, indent=4)

# セッション初期化
if "user" not in st.session_state:
    st.session_state["user"] = None
if "reports" not in st.session_state:
    st.session_state["reports"] = load_reports()

# ログイン画面
def login():
    st.title("ログイン")
    user_code = st.text_input("社員コード", key="user_code_input")
    password = st.text_input("パスワード", type="password", key="password_input")
    login_button = st.button("ログイン", key="login_button")

    if login_button:
        users = load_users()
        for user in users:
            if user["code"] == user_code and user["password"] == password:
                st.session_state["user"] = user
                st.success(f"ログイン成功！ようこそ、{user['name']}さん！")
                st.experimental_rerun()
                return
        st.error("社員コードまたはパスワードが間違っています。")

# タイムライン表示
def timeline():
    st.title("タイムライン")
    if len(st.session_state["reports"]) == 0:
        st.info("まだ投稿がありません。")
        return

    for idx, report in enumerate(reversed(st.session_state["reports"])):
        # カードデザイン
        with st.container():
            st.markdown(
                """
                <style>
                .card {
                    background-color: white;
                    padding: 15px;
                    border-radius: 10px;
                    box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
                    margin-bottom: 20px;
                }
                </style>
                """,
                unsafe_allow_html=True,
            )
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.subheader(f"投稿者: {report['投稿者']} / 投稿日: {report['投稿日時']}")
            st.write(f"カテゴリ: {report['カテゴリ']}")
            st.write(f"実施内容: {report['実施内容']}")
            if report["タグ"]:
                st.write(f"タグ: {report['タグ']}")
            if report["所感・備考"]:
                st.write(f"所感・備考: {report['所感・備考']}")

            # リアクション表示
            st.text(f"いいね！ {len(report['いいね'])} / ナイスファイト！ {len(report['ナイスファイト'])}")
            
            # リアクションボタンとコメント
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                if st.button("コメントする", key=f"comment_{idx}"):
                    with st.form(f"comment_form_{idx}"):
                        comment = st.text_area("コメントを入力してください", key=f"comment_input_{idx}")
                        submit = st.form_submit_button("投稿")
                        if submit:
                            if "コメント" not in report:
                                report["コメント"] = []
                            report["コメント"].append({"ユーザー": st.session_state["user"]["name"], "コメント": comment})
                            save_reports(st.session_state["reports"])
                            st.experimental_rerun()
            with col2:
                if st.button("いいね！", key=f"like_{idx}"):
                    if st.session_state["user"]["name"] not in report["いいね"]:
                        report["いいね"].append(st.session_state["user"]["name"])
                    else:
                        report["いいね"].remove(st.session_state["user"]["name"])
                    save_reports(st.session_state["reports"])
                    st.experimental_rerun()
            with col3:
                if st.button("ナイスファイト！", key=f"nice_fight_{idx}"):
                    if st.session_state["user"]["name"] not in report["ナイスファイト"]:
                        report["ナイスファイト"].append(st.session_state["user"]["name"])
                    else:
                        report["ナイスファイト"].remove(st.session_state["user"]["name"])
                    save_reports(st.session_state["reports"])
                    st.experimental_rerun()
            with col4:
                if st.button("お気に入り", key=f"favorite_{idx}"):
                    if report not in st.session_state["user"].get("favorites", []):
                        st.session_state["user"].setdefault("favorites", []).append(report)
                        save_reports(st.session_state["reports"])
                        st.success("お気に入りに追加しました！")
            
            # コメント一覧表示
            if "コメント" in report and len(report["コメント"]) > 0:
                st.write("コメント:")
                for comment in report["コメント"]:
                    st.write(f"- {comment['ユーザー']}: {comment['コメント']}")

            st.markdown('</div>', unsafe_allow_html=True)

# 日報投稿フォーム
def post_report():
    st.title("日報投稿")
    with st.form("report_form"):
        category = st.selectbox("カテゴリ", ["営業活動", "社内作業", "その他"], key="category")
        tags = st.text_input("タグ", placeholder="#案件, #改善提案 など", key="tags")
        content = st.text_area("実施内容", placeholder="実施した内容を記入してください", key="content")
        notes = st.text_area("所感・備考", placeholder="所感や備考を記入してください（任意）", key="notes")
        submit = st.form_submit_button("投稿")
        if submit:
            if not content:
                st.error("実施内容は必須項目です。")
            else:
                new_report = {
                    "投稿者": st.session_state["user"]["name"],
                    "カテゴリ": category,
                    "タグ": tags,
                    "実施内容": content,
                    "所感・備考": notes,
                    "投稿日時": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "いいね": [],
                    "ナイスファイト": []
                }
                st.session_state["reports"].append(new_report)
                save_reports(st.session_state["reports"])
                st.success("日報を投稿しました！")

# マイページ
def my_page():
    st.title("マイページ")
    st.write(f"ログインユーザー: {st.session_state['user']['name']}")
    st.write("お気に入り投稿:")
    if "favorites" in st.session_state["user"] and st.session_state["user"]["favorites"]:
        for favorite in st.session_state["user"]["favorites"]:
            st.write(f"- {favorite['実施内容']} (投稿日時: {favorite['投稿日時']})")
    else:
        st.write("お気に入り登録がありません。")

# お知らせ
def notifications():
    st.title("お知らせ")
    st.write("お知らせ機能は未実装です。")

# メイン処理
if st.session_state["user"] is None:
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
