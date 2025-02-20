
import streamlit as st
from db_utils import load_reports, update_reaction, save_comment
from datetime import datetime

def timeline():
    if "user" not in st.session_state or st.session_state["user"] is None:
        st.error("ログインしてください。")
        return

    st.title("📜 タイムライン")

    reports = load_reports()

    if not reports:
        st.info("📭 表示する投稿がありません。")
        return

    for report in reports:
        st.subheader(f"{report['投稿者']} さんの日報 ({report['実行日']})")
        st.write(f"🏷 **カテゴリ:** {report['カテゴリ']}")
        st.write(f"📍 **場所:** {report['場所']}")
        st.write(f"📝 **実施内容:** {report['実施内容']}")
        st.write(f"💬 **所感:** {report['所感']}")

        col1, col2 = st.columns(2)
        with col1:
            if st.button(f"❤️ {report['いいね']} いいね！", key=f"like_{report['id']}"):
                update_reaction(report["id"], "いいね")
                st.experimental_rerun()
        with col2:
            if st.button(f"👍 {report['ナイスファイト']} ナイスファイト！", key=f"nice_{report['id']}"):
                update_reaction(report["id"], "ナイスファイト")
                st.experimental_rerun()

        with st.expander("💬 コメントを見る・追加する"):
            if report["コメント"]:
                for c in report["コメント"]:
                    st.write(f"👤 {c['投稿者']} ({c['日時']}): {c['コメント']}")

            commenter_name = st.session_state["user"]["name"] if st.session_state["user"] else "匿名"
            new_comment = st.text_area(f"✏️ {commenter_name} さんのコメント", key=f"comment_{report['id']}")

            if st.button("📤 コメントを投稿", key=f"submit_comment_{report['id']}"):
                if new_comment and new_comment.strip():
                    save_comment(report["id"], commenter_name, new_comment)
                    st.success("✅ コメントを投稿しました！")
                    st.experimental_rerun()
                else:
                    st.warning("⚠️ 空白のコメントは投稿できません！")
