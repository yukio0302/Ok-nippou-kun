import streamlit as st
from datetime import datetime, timedelta
import os

# 初期設定
st.set_page_config(page_title="日報管理システム", layout="wide")
st.session_state.setdefault("user", None)  # ユーザー情報
st.session_state.setdefault("reports", [])  # 日報投稿データ

# ログイン画面
def login():
    st.title("ログイン")
    # 各入力要素に一意のキーを付与
    employee_code = st.text_input("社員コード", key="employee_code_input")
    password = st.text_input("パスワード", type="password", key="password_input")
    login_button = st.button("ログイン", key="login_button")

    if login_button:
        # ユーザー認証（簡易版、外部ユーザー情報データを使用予定）
        if employee_code == "901179" and password == "okanaga":
            st.session_state.user = {"code": employee_code, "name": "野村　幸男"}
            st.success("ログイン成功！")
        else:
            st.error("社員コードまたはパスワードが間違っています。")

# タイムライン表示
def timeline():
    st.title("タイムライン")

    if "reports" not in st.session_state or len(st.session_state["reports"]) == 0:
        st.info("まだ投稿がありません。")
        return

    # 投稿を最新順に表示
    for report in reversed(st.session_state["reports"]):
        st.subheader(f"カテゴリ: {report['カテゴリ']} - {report['投稿日時']}")
        if report["得意先"]:
            st.write(f"得意先: {report['得意先']}")
        if report["タグ"]:
            st.write(f"タグ: {report['タグ']}")
        st.write(f"実施内容: {report['実施内容']}")
        if report["所感・備考"]:
            st.write(f"所感・備考: {report['所感・備考']}")
        if report["画像"]:
            try:
                st.image(report["画像"].read(), caption=report["画像"].name, use_column_width=True)
            except Exception as e:
                st.warning("画像の読み込み中にエラーが発生しました。")

# 日報投稿フォーム
def post_report():
    st.title("日報投稿")

    with st.form("report_form"):
        # カテゴリ選択
        category = st.selectbox("カテゴリ", ["営業活動", "社内作業", "その他"], key="category")

        # 得意先（営業活動時のみ表示）
        client = st.text_input("得意先", placeholder="営業活動の場合に記入してください", key="client") if category == "営業活動" else ""

        # タグ
        tags = st.text_input("タグ", placeholder="#案件, #改善提案 など", key="tags")

        # 実施内容（必須）
        content = st.text_area("実施内容", placeholder="実施した内容を記入してください", key="content")

        # 所感・備考
        notes = st.text_area("所感・備考", placeholder="所感や備考を記入してください（任意）", key="notes")

        # 画像アップロード
        image = st.file_uploader("画像をアップロード（任意）", type=["jpg", "png", "jpeg"], key="image")

        # 投稿ボタン
        submit = st.form_submit_button("投稿")

        if submit:
            # 入力バリデーション
            if not content:
                st.error("実施内容は必須項目です。")
            else:
                # 投稿内容をセッションに保存
                post = {
                    "カテゴリ": category,
                    "得意先": client,
                    "タグ": tags,
                    "実施内容": content,
                    "所感・備考": notes,
                    "画像": image if image else None,
                    "投稿日時": datetime.now().strftime("%Y-%m-%d %H:%M")
                }
                st.session_state["reports"].append(post)

                st.success("日報を投稿しました！")

# メイン処理
if st.session_state.user is None:
    login()
else:
    # 下部ナビゲーション
    menu = st.sidebar.radio("メニュー", ["タイムライン", "日報投稿", "マイページ", "お知らせ"])

    if menu == "タイムライン":
        timeline()
    elif menu == "日報投稿":
        post_report()
    elif menu == "マイページ":
        st.write("マイページ機能は未実装です。")
    elif menu == "お知らせ":
        st.write("お知らせ機能は未実装です。")
