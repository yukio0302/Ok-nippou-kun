import streamlit as st
import json
from datetime import datetime

# ファイルパス
USER_DATA_FILE = "users_data.json"
REPORTS_FILE = "reports.json"
NOTICE_FILE = "notices.json"

# ファイル読み込み関数
def load_data(file_path, default_data):
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return default_data

# ファイル保存関数
def save_data(file_path, data):
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# データ読み込み
users = load_data(USER_DATA_FILE, [])
reports = load_data(REPORTS_FILE, [])
notices = load_data(NOTICE_FILE, [])

# Streamlit 初期設定
st.set_page_config(page_title="日報管理システム", layout="wide")

# ログイン機能
def login():
    st.title("ログイン")
    user_code = st.text_input("社員コード")
    password = st.text_input("パスワード", type="password", help="パスワードを入力してください")
    login_button = st.button("ログイン")
    
    if login_button:
        user = next((u for u in users if u["code"] == user_code and u["password"] == password), None)
        if user:
            st.session_state["user"] = user
            st.success(f"ログイン成功！ようこそ、{user['name']}さん！")
            st.rerun()
        else:
            st.error("社員コードまたはパスワードが間違っています。")

# 日報投稿
def post_report():
    st.title("日報投稿")
    with st.form("report_form"):
        category = st.selectbox("カテゴリ", ["営業活動", "社内作業", "その他"])
        tags = st.text_input("タグ", placeholder="#案件, #改善提案 など")
        content = st.text_area("実施内容", placeholder="実施した内容を記入してください")
        notes = st.text_area("所感・備考", placeholder="所感や備考を記入してください（任意）")
        submit = st.form_submit_button("投稿")
        
        if submit and content:
            new_report = {
                "投稿者": st.session_state["user"]["name"],
                "カテゴリ": category,
                "タグ": tags,
                "実施内容": content,
                "所感・備考": notes,
                "投稿日時": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "いいね": 0,
                "ナイスファイト": 0,
                "コメント": []
            }
            reports.append(new_report)
            save_data(REPORTS_FILE, reports)
            st.success("日報を投稿しました！")
            st.rerun()

# タイムライン
def timeline():
    st.title("📜 タイムライン")

    search_keyword = st.text_input("🔎 投稿検索（タグ & 本文）", placeholder="キーワードを入力")

    # 🔥 お知らせから指定された投稿があれば、それを先頭にする
    jump_to_report = st.session_state.get("jump_to_report", None)
    if jump_to_report is not None:
        filtered_reports = [reports[jump_to_report]] + [r for i, r in enumerate(reports) if i != jump_to_report]
        st.session_state["jump_to_report"] = None
    else:
        filtered_reports = reports if not search_keyword else [
            r for r in reports if search_keyword in r["タグ"] or search_keyword in r["実施内容"]
        ]

    if not filtered_reports:
        st.info("🔍 該当する投稿がありません。")
        return

    for idx, report in enumerate(filtered_reports):
        with st.container():
            if jump_to_report is not None and idx == 0:
                st.markdown("### 🎯 該当の投稿")
                st.markdown("---")

            st.subheader(f"{report['投稿者']} - {report['カテゴリ']} - {report['投稿日時']}")

            if report["タグ"]:
                st.markdown(f"**🏷 タグ:** {report['タグ']}")

            st.write(f"📝 {report['実施内容']}")

            st.text(f"👍 いいね！ {report['いいね']} / 🎉 ナイスファイト！ {report['ナイスファイト']}")

            col1, col2 = st.columns(2)
            with col1:
                if st.button("👍 いいね！", key=f"like_{idx}"):
                    report["いいね"] += 1
                    save_data(REPORTS_FILE, reports)
                    st.rerun()

            with col2:
                if st.button("🎉 ナイスファイト！", key=f"nice_fight_{idx}"):
                    report["ナイスファイト"] += 1
                    save_data(REPORTS_FILE, reports)
                    st.rerun()

            if "コメント" not in report:
                report["コメント"] = []

            st.subheader("💬 コメント一覧")
            for comment_idx, comment in enumerate(report["コメント"]):
                st.text(f"📌 {comment['投稿者']}: {comment['内容']} ({comment['投稿日時']})")
                if comment["投稿者"] == st.session_state["user"]["name"]:
                    if st.button("🗑 削除", key=f"delete_comment_{idx}_{comment_idx}"):
                        report["コメント"].pop(comment_idx)
                        save_data(REPORTS_FILE, reports)
                        st.rerun()

            new_comment = st.text_input(f"✏ コメントを入力（{report['投稿者']} さんの日報）", key=f"comment_{idx}")
            if st.button("💬 コメント投稿", key=f"post_comment_{idx}"):
                if new_comment.strip():
                    new_comment_data = {
                        "投稿者": st.session_state["user"]["name"],
                        "内容": new_comment,
                        "投稿日時": datetime.now().strftime("%Y-%m-%d %H:%M")
                    }
                    report["コメント"].append(new_comment_data)
                    save_data(REPORTS_FILE, reports)

                    new_notice = {
                        "タイトル": "あなたの投稿にコメントがつきました！",
                        "日付": datetime.now().strftime("%Y-%m-%d %H:%M"),
                        "内容": f"{st.session_state['user']['name']} さんがコメントしました！",
                        "リンク": reports.index(report),
                        "既読": False
                    }
                    notices.append(new_notice)
                    save_data(NOTICE_FILE, notices)

                    st.success("コメントを投稿しました！")
                    st.rerun()

# お知らせ
def notice():
    st.title("🔔 お知らせ")

    # 未読と既読のタブを作る
    tab_selected = st.radio("📌 お知らせ", ["未読", "既読"])

    # 未読・既読リストのフィルタリング
    unread_notices = [n for n in notices if not n["既読"]]
    read_notices = [n for n in notices if n["既読"]]

    # 確認する投稿のインデックス（Noneなら表示しない）
    selected_report_index = st.session_state.get("selected_report_index", None)

    # 🔴 未読タブ
    if tab_selected == "未読":
        if selected_report_index is None:
            if not unread_notices:
                st.info("未読のお知らせはありません。")
                return
            
            for idx, notice in enumerate(unread_notices):
                with st.container():
                    st.subheader(f"{notice['タイトル']} - {notice['日付']}")
                    st.write(notice["内容"])

                    if "リンク" in notice:
                        if st.button("📌 投稿を確認する", key=f"notice_{idx}"):
                            st.session_state["selected_report_index"] = notice["リンク"]
                            notice["既読"] = True
                            save_data(NOTICE_FILE, notices)
                            st.rerun()

        else:
            # 📌 投稿を表示
            report = reports[selected_report_index]
            st.markdown("### 🎯 該当の投稿")
            st.subheader(f"{report['投稿者']} - {report['カテゴリ']} - {report['投稿日時']}")
            
            if report["タグ"]:
                st.markdown(f"**🏷 タグ:** {report['タグ']}")

            st.write(f"📝 {report['実施内容']}")

            st.text(f"👍 いいね！ {report['いいね']} / 🎉 ナイスファイト！ {report['ナイスファイト']}")

            # 🔙 閉じるボタン
            if st.button("❌ 閉じる"):
                st.session_state["selected_report_index"] = None
                st.rerun()

    # ✅ 既読タブ
    elif tab_selected == "既読":
        if not read_notices:
            st.info("既読のお知らせはありません。")
            return
        
        for notice in read_notices:
            with st.container():
                st.subheader(f"{notice['タイトル']} - {notice['日付']}")
                st.write(notice["内容"])


if "user" not in st.session_state:
    st.session_state["user"] = None

if st.session_state["user"] is None:
    login()
else:
    menu = st.sidebar.radio("メニュー", ["タイムライン", "日報投稿", "お知らせ"])
    if menu == "タイムライン":
        timeline()
    elif menu == "日報投稿":
        post_report()
    elif menu == "お知らせ":
        notice()
