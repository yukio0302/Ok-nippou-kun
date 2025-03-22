# weekly_plan.py
import streamlit as st
import json
from datetime import datetime, timedelta
from db_utils import save_weekly_plan, load_weekly_plans, update_reaction, save_comment

# ✅ 週間予定投稿
def post_weekly_plan():
    if "user" not in st.session_state or st.session_state["user"] is None:
        st.error("ログインしてください。")
        return

    st.title("週間予定投稿")

    start_date = st.date_input("週の開始日")
    end_date = start_date + timedelta(days=6)  # 週の終了日を計算

    st.write(f"該当週: {start_date.strftime('%Y年%m月%d日')} ~ {end_date.strftime('%Y年%m月%d日')}")

    plans = {}
    for i in range(7):
        current_date = start_date + timedelta(days=i)
        day_name = current_date.strftime("%A")  # 曜日名を取得
        plans[current_date.strftime("%Y-%m-%d")] = st.text_area(f"{current_date.strftime('%m月%d日')} ({day_name}) の予定")

    if st.button("週間予定を投稿"):
        save_weekly_plan(st.session_state["user"]["name"], start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d"), json.dumps(plans))
        st.success("✅ 週間予定を投稿しました！")
        time.sleep(1)
        switch_page("タイムライン")

# ✅ 週間予定を表示
def show_weekly_plans():
    if "user" not in st.session_state or st.session_state["user"] is None:
        st.error("ログインしてください。")
        return

    st.title("週間予定")

    weekly_plans = load_weekly_plans()

    if not weekly_plans:
        st.info("週間予定はありません。")
        return

    for plan in weekly_plans:
        st.subheader(f"{plan['投稿者']} さんの週間予定 ({plan['週開始日']} ~ {plan['週終了日']})")
        plans = json.loads(plan["予定"])
        for date, content in plans.items():
            st.write(f"**{date}**: {content}")

        #  いいね！、コメント機能
        col1, col2 = st.columns(2)
        with col1:
            if st.button(f"❤️ {plan['いいね']} いいね！", key=f"like_plan_{plan['id']}"):
                update_reaction(plan["id"], "いいね")
                st.rerun()
        with col2:
            if st.button(f" {plan['ナイスファイト']} ナイスファイト！", key=f"nice_plan_{plan['id']}"):
                update_reaction(plan["id"], "ナイスファイト")
                st.rerun()

        # コメント欄
        comment_count = len(plan["コメント"]) if plan["コメント"] else 0  # コメント件数を取得
        with st.expander(f" ({comment_count}件)のコメントを見る・追加する "):  # 件数を表示
            if plan["コメント"]:
                for c in plan["コメント"]:
                    st.write(f" {c['投稿者']} ({c['日時']}): {c['コメント']}")

            if plan.get("id") is None:
                st.error("⚠️ 投稿の ID が見つかりません。")
                continue

            commenter_name = st.session_state["user"]["name"] if st.session_state["user"] else "匿名"
            new_comment = st.text_area(f"✏️ {commenter_name} さんのコメント", key=f"comment_plan_{plan['id']}")

            if st.button(" コメントを投稿", key=f"submit_comment_plan_{plan['id']}"):
                if new_comment and new_comment.strip():
                    print(f"️ コメント投稿デバッグ: report_id={plan['id']}, commenter={commenter_name}, comment={new_comment}")
                    save_comment(plan["id"], commenter_name, new_comment)
                    st.success("✅ コメントを投稿しました！")
                    st.rerun()
                else:
                    st.warning("⚠️ 空白のコメントは投稿できません！")

        st.write("----")

# ✅ 週間予定編集フォーム
def edit_weekly_plan(plan):
    """週間予定の編集フォーム"""
    plans = json.loads(plan["予定"])
    new_plans = {}
    for date, content in plans.items():
        new_plans[date] = st.text_area(f"{date} の予定", content)

    if st.button("保存", key=f"save_plan_{plan['id']}"):
        save_weekly_plan(plan["投稿者"], plan["週開始日"], plan["週終了日"], json.dumps(new_plans))
        st.success("✅ 編集を保存しました")
        st.rerun()

    if st.button("キャンセル", key=f"cancel_plan_{plan['id']}"):
        st.rerun()

# ✅ 週間予定削除
def delete_weekly_plan(plan_id):
    """週間予定を削除する"""
    if st.button("削除", key=f"delete_plan_{plan_id}"):
        delete_weekly_plan(plan_id)
        st.success("✅ 削除しました")
        st.rerun()
