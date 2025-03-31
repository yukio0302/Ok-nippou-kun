import json
import os
from datetime import datetime, timedelta
import streamlit as st
from neon_db_utils import execute_query

# ✅ ユーザー認証（先に定義！）
def authenticate_user(employee_code, password):
    """ユーザー認証（users_data.jsonを使用）"""
    USER_FILE = "data/users_data.json"

    if not os.path.exists(USER_FILE):
        return None

    try:
        with open(USER_FILE, "r", encoding="utf-8-sig") as file:
            users = json.load(file)

        for user in users:
            if user["code"] == employee_code and user["password"] == password:
                return user
    except (FileNotFoundError, json.JSONDecodeError):
        pass

    return None

def init_db(keep_existing=True):
    """データベースの初期化（テーブル作成）"""
    if not keep_existing:
        execute_query("DROP TABLE IF EXISTS reports")
        execute_query("DROP TABLE IF EXISTS notices")
        execute_query("DROP TABLE IF EXISTS weekly_schedules")

    # ✅ 日報データのテーブル作成（存在しない場合のみ）
    execute_query("""
        CREATE TABLE IF NOT EXISTS reports (
            id SERIAL PRIMARY KEY,
            投稿者 TEXT,
            実行日 TEXT,
            カテゴリ TEXT,
            場所 TEXT,
            実施内容 TEXT,
            所感 TEXT,
            いいね INTEGER DEFAULT 0,
            ナイスファイト INTEGER DEFAULT 0,
            コメント TEXT DEFAULT '[]',
            画像 TEXT,
            投稿日時 TEXT
        )
    """)

    # ✅ お知らせデータのテーブル作成（存在しない場合のみ）
    execute_query("""
        CREATE TABLE IF NOT EXISTS notices (
            id SERIAL PRIMARY KEY,
            タイトル TEXT,
            内容 TEXT,
            日付 TEXT,
            既読 INTEGER DEFAULT 0,
            対象ユーザー TEXT
        )
    """)

    # ✅ 週間予定データのテーブル作成（存在しない場合のみ）
    execute_query("""
        CREATE TABLE IF NOT EXISTS weekly_schedules (
            id SERIAL PRIMARY KEY,
            投稿者 TEXT,
            開始日 TEXT,
            終了日 TEXT,
            月曜日 TEXT,
            火曜日 TEXT,
            水曜日 TEXT,
            木曜日 TEXT,
            金曜日 TEXT,
            土曜日 TEXT,
            日曜日 TEXT,
            投稿日時 TEXT,
        コメント TEXT DEFAULT '[]'
        )
    """)

def update_db_schema():
    """既存のデータベーススキーマを安全に更新する"""
    # カラム存在チェック
    columns = execute_query("PRAGMA table_info(notices)", fetch=True)
    column_names = [col[1] for col in columns]

    if "対象ユーザー" not in column_names:
        try:
            execute_query("ALTER TABLE notices ADD COLUMN 対象ユーザー TEXT")
            print("✅ 対象ユーザーカラムを追加しました！")
        except Exception as e:
            print(f"⚠️ スキーマ更新エラー: {e}")
    else:
        print("✅ 対象ユーザーカラムは既に存在します")

def save_report(report):
    """日報をデータベースに保存（表示形式は変更しない安定版）"""
    try:
        report["投稿日時"] = (datetime.now() + timedelta(hours=9)).strftime("%Y-%m-%d %H:%M:%S")

        if '実行日' not in report or not report['実行日']:
            report['実行日'] = (datetime.now() + timedelta(hours=9)).strftime("%Y-%m-%d")

        execute_query("""
            INSERT INTO reports (投稿者, 実行日, カテゴリ, 場所, 実施内容, 所感, いいね, ナイスファイト, コメント, 画像, 投稿日時)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            report["投稿者"], report["実行日"], report["カテゴリ"], report["場所"],
            report["実施内容"], report["所感"], 0, 0, json.dumps([]), report.get("image", None), report["投稿日時"]
        ))
        print(f"✅ 日報を保存しました（投稿者: {report['投稿者']}, 実行日: {report['実行日']}）")
    except Exception as e:
        print(f"⚠️ 日報保存エラー: {e}")

def load_reports():
    """日報データを取得（最新の投稿順にソート）"""
    rows = execute_query("SELECT * FROM reports ORDER BY 投稿日時 DESC", fetch=True)
    reports = []
    for row in rows:
        reports.append({
            "id": row[0], "投稿者": row[1], "実行日": row[2], "カテゴリ": row[3],
            "場所": row[4], "実施内容": row[5], "所感": row[6], "いいね": row[7],
            "ナイスファイト": row[8], "コメント": json.loads(row[9]), "image": row[10],
            "投稿日時": row[11]
        })
    return reports

def update_reaction(report_id, reaction_type):
    """リアクション（いいね・ナイスファイト）を更新"""
    if reaction_type == "いいね":
        execute_query("UPDATE reports SET いいね = いいね + 1 WHERE id = %s", (report_id,))
    elif reaction_type == "ナイスファイト":
        execute_query("UPDATE reports SET ナイスファイト = ナイスファイト + 1 WHERE id = %s", (report_id,))

def save_comment(report_id, commenter, comment):
    """コメントを保存＆通知を追加"""
    row = execute_query("SELECT 投稿者, 実行日, 場所, 実施内容, コメント FROM reports WHERE id = %s", (report_id,), fetch=True)
    if row:
        投稿者, 実行日, 場所, 実施内容, comments = row[0]
        comments = json.loads(comments) if comments else []

        new_comment = {
            "投稿者": commenter,
            "日時": (datetime.now() + timedelta(hours=9)).strftime("%Y-%m-%d %H:%M:%S"),
            "コメント": comment
        }
        comments.append(new_comment)
        execute_query("UPDATE reports SET コメント = %s WHERE id = %s", (json.dumps(comments), report_id))

        if 投稿者 != commenter:
            notification_content = f"""【お知らせ】
{new_comment["日時"]}

実施日: {実行日}
場所: {場所}
実施内容: {実施内容}

の投稿に {commenter} さんがコメントしました。
コメント内容: {comment}
"""
            execute_query("""
                INSERT INTO notices (タイトル, 内容, 日付, 既読, 対象ユーザー)
                VALUES (%s, %s, %s, %s, %s)
            """, (
                "新しいコメントが届きました！", notification_content, new_comment["日時"], 0, 投稿者
            ))

def load_commented_reports(commenter_name):
    """指定したユーザーがコメントした投稿を取得（コメント日時の降順でソート）"""
    rows = execute_query("SELECT * FROM reports", fetch=True)
    commented_reports = []
    for row in rows:
        comments = json.loads(row[9]) if row[9] else []
        for comment in comments:
            if comment["投稿者"] == commenter_name:
                commented_reports.append({
                    "id": row[0], "投稿者": row[1], "実行日": row[2], "カテゴリ": row[3],
                    "場所": row[4], "実施内容": row[5], "所感": row[6], "いいね": row[7],
                    "ナイスファイト": row[8], "コメント": comments, "image": row[10],
                    "投稿日時": row[11], "コメント日時": comment["日時"]
                })
                break
    return sorted(commented_reports, key=lambda x: x["コメント日時"], reverse=True)

def load_notices(user_name):
    """お知らせデータを取得（対象ユーザーのみ）"""
    rows = execute_query("SELECT * FROM notices WHERE 対象ユーザー = %s ORDER BY 日付 DESC", (user_name,), fetch=True)
    notices = []
    for row in rows:
        notices.append({
            "id": row[0], "タイトル": row[1], "内容": row[2], "日付": row[3], "既読": row[4]
        })
    return notices

def mark_notice_as_read(notice_id):
    """お知らせを既読にする"""
    execute_query("UPDATE notices SET 既読 = 1 WHERE id = %s", (notice_id,))

def edit_report(report_id, new_date, new_location, new_content, new_remarks):
    """投稿を編集する"""
    execute_query("""
        UPDATE reports
        SET 実行日 = %s, 場所 = %s, 実施内容 = %s, 所感 = %s
        WHERE id = %s
    """, (new_date, new_location, new_content, new_remarks, report_id))
    print(f"✅ 投稿 (ID: {report_id}) を編集しました！")

def delete_report(report_id):
    """投稿を削除する（エラーハンドリング付き）"""
    deleted = execute_query("DELETE FROM reports WHERE id = %s", (report_id,))
    if deleted:
        print("✅ 削除成功！")
        return True
    else:
        print(f"⚠️ 削除対象の投稿（ID: {report_id}）が見つかりませんでした。")
        return False

def save_weekly_schedule(schedule):
    """週間予定をデータベースに保存"""
    schedule["投稿日時"] = (datetime.now() + timedelta(hours=9)).strftime("%Y-%m-%d %H:%M:%S")
    execute_query("""
        INSERT INTO weekly_schedules (投稿者, 開始日, 終了日, 月曜日, 火曜日, 水曜日, 木曜日, 金曜日, 土曜日, 日曜日, 投稿日時)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """, (
        schedule["投稿者"], schedule["開始日"], schedule["終了日"],schedule["月曜日"], schedule["火曜日"], schedule["水曜日"], schedule["木曜日"],
        schedule["金曜日"], schedule["土曜日"], schedule["日曜日"], schedule["投稿日時"]
    ))
    print("✅ 週間予定を保存しました！")

def load_weekly_schedules():
    """週間予定データを取得（最新の投稿順にソート）"""
    rows = execute_query("SELECT * FROM weekly_schedules ORDER BY 投稿日時 DESC", fetch=True)
    schedules = []
    for row in rows:
        schedules.append({
            "id": row[0], "投稿者": row[1], "開始日": row[2], "終了日": row[3],
            "月曜日": row[4], "火曜日": row[5], "水曜日": row[6],
            "木曜日": row[7], "金曜日": row[8], "土曜日": row[9],
            "日曜日": row[10], "投稿日時": row[11],
            "コメント": json.loads(row[12]) if row[12] else []
        })
    return schedules

def update_weekly_schedule(schedule_id, monday, tuesday, wednesday, thursday, friday, saturday, sunday):
    """週間予定を更新する"""
    execute_query("""
        UPDATE weekly_schedules
        SET 月曜日 = %s, 火曜日 = %s, 水曜日 = %s, 木曜日 = %s, 金曜日 = %s, 土曜日 = %s, 日曜日 = %s
        WHERE id = %s
    """, (monday, tuesday, wednesday, thursday, friday, saturday, sunday, schedule_id))
    print(f"✅ 週間予定 (ID: {schedule_id}) を編集しました！")

def add_comments_column():
    """weekly_schedules テーブルにコメントカラムを追加（存在しない場合のみ）"""
    try:
        execute_query("SELECT コメント FROM weekly_schedules LIMIT 1", fetch=True)
    except Exception:
        execute_query("ALTER TABLE weekly_schedules ADD COLUMN コメント TEXT DEFAULT '[]'")
        print("✅ コメントカラムを追加しました！")

def save_weekly_schedule_comment(schedule_id, commenter, comment):
    """週間予定へのコメントを保存＆通知を追加"""
    row = execute_query("SELECT 投稿者, 開始日, 終了日, コメント FROM weekly_schedules WHERE id = %s", (schedule_id,), fetch=True)
    if row:
        投稿者, 開始日, 終了日, comments = row[0]
        comments = json.loads(comments) if comments else []

        new_comment = {
            "投稿者": commenter,
            "日時": (datetime.now() + timedelta(hours=9)).strftime("%Y-%m-%d %H:%M:%S"),
            "コメント": comment
        }
        comments.append(new_comment)
        execute_query("UPDATE weekly_schedules SET コメント = %s WHERE id = %s", (json.dumps(comments, ensure_ascii=False), schedule_id))

        if 投稿者 != commenter:
            notification_content = f"""【お知らせ】
{new_comment["日時"]}

期間: {開始日} ～ {終了日}
の週間予定投稿に {commenter} さんがコメントしました。
コメント内容: {comment}
"""
            execute_query("""
                INSERT INTO notices (タイトル, 内容, 日付, 既読, 対象ユーザー)
                VALUES (%s, %s, %s, %s, %s)
            """, (
                "新しいコメントが届きました！", notification_content, new_comment["日時"], 0, 投稿者
            ))
        print(f"✅ 週間予定 (ID: {schedule_id}) にコメントを保存し、通知を追加しました！")

def get_weekly_schedule_for_all_users(start_date, end_date):
    """
    指定期間の全ユーザーの週間予定データを取得する
    """
    rows = execute_query("""
        SELECT user_id, schedule_date, schedule_content, comment
        FROM weekly_schedule
        WHERE schedule_date BETWEEN %s AND %s
    """, (start_date, end_date), fetch=True)

    user_schedules = {}
    for user_id, schedule_date, schedule_content, comment in rows:
        if user_id not in user_schedules:
            user_schedules[user_id] = []
        user_schedules[user_id].append({
            "date": schedule_date,
            "content": schedule_content,
            "comment": comment
        })
    return user_schedules

def get_daily_schedule(user_name: str, target_date: str) -> str:
    """指定日の週間予定を取得"""
    row = execute_query("""
        SELECT 開始日, 月曜日, 火曜日, 水曜日, 木曜日, 金曜日, 土曜日, 日曜日
        FROM weekly_schedules
        WHERE 投稿者 = %s AND %s BETWEEN 開始日 AND 終了日
        ORDER BY 投稿日時 DESC
        LIMIT 1
    """, (user_name, target_date), fetch=True)

    if not row:
        return ""

    start_date = datetime.strptime(row[0][0], "%Y-%m-%d").date()
    target = datetime.strptime(target_date, "%Y-%m-%d").date()
    day_diff = (target - start_date).days

    if 0 <= day_diff <= 6:
        return row[0][day_diff + 1]

    return ""
