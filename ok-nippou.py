# タイムライン
def timeline():
    st.title("📜 タイムライン")

    # 🔍 タグ & キーワード検索
    search_keyword = st.text_input("🔎 投稿検索（タグ & 本文）", placeholder="キーワードを入力")
    
    # 検索ロジック（投稿のタグ or 本文にキーワードが含まれるか）
    filtered_reports = reports if not search_keyword else [
        r for r in reports if search_keyword in r["タグ"] or search_keyword in r["実施内容"]
    ]

    if not filtered_reports:
        st.info("🔍 該当する投稿がありません。")
        return

    for idx, report in enumerate(filtered_reports):
        with st.container():
            # 📝 タイトル（投稿者 & カテゴリ）
            st.subheader(f"{report['投稿者']} - {report['カテゴリ']} - {report['投稿日時']}")

            # 🏷 タグ
            if report["タグ"]:
                st.markdown(f"**🏷 タグ:** {report['タグ']}")

            # 📄 投稿内容（全文表示）
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

            # 🔴 コメント機能
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

            # 💬 コメント投稿
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
                        "リンク": idx,
                        "既読": False
                    }
                    notices.append(new_notice)
                    save_data(NOTICE_FILE, notices)

                    st.success("コメントを投稿しました！")
                    st.rerun()
