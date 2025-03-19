import sqlite3
import json
import os
from datetime import datetime, timedelta

# データベースのパス
DB_PATH = "/mount/src/ok-nippou-kun/Ok-nippou-kun/data/reports.db"

# ユーザー認証
def authenticate_user(employee_code, password):
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

# データベース初期化
def init_db(keep_existing=True):
    db_folder = os.path.dirname(DB_PATH)
    os.makedirs(db_folder, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    if not keep_existing:
        cur.execute("DROP TABLE IF EXISTS reports")
        cur.execute("DROP TABLE IF EXISTS notices")
        cur.execute("DROP TABLE IF EXISTS weekly_schedules")

    cur.execute("""
    CREATE TABLE IF NOT EXISTS reports (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
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

    cur.execute("""
    CREATE TABLE IF NOT EXISTS notices (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        タイトル TEXT,
        内容 TEXT,
        日付 TEXT,
        既読 INTEGER DEFAULT 0,
        対象ユーザー TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS weekly_schedules (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
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

    conn.commit()
    conn.close()

# データベーススキーマ更新
def update_db_schema():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    try:
        cur.execute("ALTER TABLE notices ADD COLUMN 対象ユーザー TEXT")
        conn.commit()
        print("✅ データベーススキーマを更新しました！")
    except sqlite3.OperationalError as e:
        print(f"⚠️ スキーマ更新エラー: {e} (既にカラムが存在する可能性があります)")
    conn.close()

update_db_schema()

# 日報保存
def save_report(report):
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        report["投稿日時"] = (datetime.now() + timedelta(hours=9)).strftime("%Y-%m-%d %H:%M:%S")
        report["実行日"] = (datetime.now() + timedelta(hours=9)).strftime("%Y-%m-%d")
        cur.execute("""
        INSERT INTO reports (投稿者, 実行日, カテゴリ, 場所, 実施内容, 所感, いいね, ナイスファイト, コメント, 画像, 投稿日時)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            report["投稿者"], report["実行日"], report["カテゴリ"], report["場所"], 
            report["実施内容"], report["所感"], 0, 0, json.dumps([]), 
            report.get("image", None), report["投稿日時"]
        ))
        conn.commit()
        conn.execute("VACUUM")
        conn.close()
        print("✅ データベースに日報を保存しました！")
    except Exception as e:
        print(f"⚠️ データベース保存エラー: {e}")

# 日報読み込み
def load_reports():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT * FROM reports ORDER BY 投稿日時 DESC")
    rows = cur.fetchall()
    conn.close()
    reports = []
    for row in rows:
        reports.append({
            "id": row[0], "投稿者": row[1], "実行日": row[2], "カテゴリ": row[3], 
            "場所": row[4], "実施内容": row[5], "所感": row[6], "いいね": row[7], 
            "ナイスファイト": row[8], "コメント": json.loads(row[9]), "image": row[10], 
            "投稿日時": row[11]
        })
    return reports

# リアクション更新
def update_reaction(report_id, reaction_type):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    if reaction_type == "いいね":
        cur.execute("UPDATE reports SET いいね = いいね + 1 WHERE id = ?", (report_id,))
    elif reaction_type == "ナイスファイト":
        cur.execute("UPDATE reports SET ナイスファイト = ナイスファイト + 1 WHERE id = ?", (report_id,))
    conn.commit()
    conn.close()

# コメント保存
def save_comment(report_id, commenter, comment):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT 投稿者, 実行日, 場所, 実施内容, コメント FROM reports WHERE id = ?", (report_id,))
    row = cur.fetchone()
    if row:
        投稿者, 実行日, 場所, 実施内容, comments = row
        comments = json.loads(comments) if comments else []
        new_comment = {
            "投稿者": commenter, 
            "日時": (datetime.now() + timedelta(hours=9)).strftime("%Y-%m-%d %H:%M:%S"), 
            "コメント": comment
        }
        comments.append(new_comment)
        cur.execute("UPDATE reports SET コメント = ? WHERE id = ?", (json.dumps(comments), report_id))
        if 投稿者 != commenter:
            notification_content = f"""【お知らせ】\n{new_comment["日時"]}\n\n実施日: {実行日}\n場所: {場所}\n実施内容: {実施内容}\n\nの投稿に {commenter} さんがコメントしました。\nコメント内容: {comment}"""
            cur.execute("""
                INSERT INTO notices (タイトル, 内容, 日付, 既読, 対象ユーザー)
                VALUES (?, ?, ?, ?, ?)
            """, ("新しいコメントが届きました！", notification_content, new_comment["日時"], 0, 投稿者))
        conn.commit()
    conn.close()

# コメント投稿読み込み
def load_commented_reports(commenter_name):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT * FROM reports")
    rows = cur.fetchall()
    conn.close()
    commented_reports = []
    for row in rows:
        comments = json.loads(row[9]) if row[9] else []
        for comment in comments:
            if comment["投稿者"] == commenter_name:
                commented_reports.append({
                    "id": row[0], "投稿者": row[1], "実行日": row[2], "カテゴリ": row[3], 
                    "場所": row[4], "実施内容": row[5], "所感": row[6], "いいね": row[7], 
                    "ナイスファイト": row[8], "コメント": comments, "image": row[10], 
                    "投稿日時": row[11],
                    "コメント日時": comment["日時"]
                })
                break
    commented_reports.sort(key=lambda x: x["コメント日時"], reverse=True)
    return commented_reports

# お知らせ読み込み
def load_notices(user_name):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT * FROM notices WHERE 対象ユーザー = ? ORDERDESC", (user_name,))
    rows = cur.fetchall()
    conn.close()
    notices = []
    for row in rows:
        notices.append({
            "id": row[0], "タイトル": row[1], "内容": row[2], "日付": row[3], "既読": row[4]
        })
    return notices

# お知らせ既読
def mark_notice_as_read(notice_id):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("UPDATE notices SET 既読 = 1 WHERE id = ?", (notice_id,))
    conn.commit()
    conn.close()

# 日報編集
def edit_report(report_id, new_date, new_location, new_content, new_remarks):
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("""
            UPDATE reports
            SET 実行日 = ?, 場所 = ?, 実施内容 = ?, 所感 = ?
            WHERE id = ?
        """, (new_date, new_location, new_content, new_remarks, report_id))
        conn.commit()
        conn.close()
        print(f"✅ 投稿 (ID: {report_id}) を編集しました！")
    except sqlite3.Error as e:
        print(f"❌ データベースエラー: {e}")

# 日報削除
def delete_report(report_id):
    try:
        with sqlite3.connect(DB_PATH) as conn:
            c = conn.cursor()
            print(f"️ 削除処理開始: report_id={report_id}")
            c.execute("DELETE FROM reports WHERE id = ?", (report_id,))
            conn.commit()
            if c.rowcount == 0:
                print(f"⚠️ 削除対象の投稿（ID: {report_id}）が見つかりませんでした。")
                return False
            print("✅ 削除成功！")
            return True
    except sqlite3.Error as e:
        print(f"❌ データベースエラー: {e}")
        return False
        
# 週間予定保存
def save_weekly_schedule(schedule):
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        schedule["投稿日時"] = (datetime.now() + timedelta(hours=9)).strftime("%Y-%m-%d %H:%M:%S")
        cur.execute("""
        INSERT INTO weekly_schedules (投稿者, 開始日, 終了日, 月曜日, 火曜日, 水曜日, 木曜日, 金曜日, 土曜日, 日曜日, 投稿日時)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            schedule["投稿者"], schedule["開始日"], schedule["終了日"], 
            schedule["月曜日"], schedule["火曜日"], schedule["水曜日"], 
            schedule["木曜日"], schedule["金曜日"], schedule["土曜日"], 
            schedule["日曜日"], schedule["投稿日時"]
        ))
        conn.commit()
        conn.close()
        print("✅ 週間予定を保存しました！")
    except Exception as e:
        print(f"⚠️ 週間予定の保存エラー: {e}")

# 週間予定読み込み
def load_weekly_schedules():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT * FROM weekly_schedules ORDER BY 投稿日時 DESC")
    rows = cur.fetchall()
    conn.close()
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

# 週間予定更新
def update_weekly_schedule(schedule_id, monday, tuesday, wednesday, thursday, friday, saturday, sunday):
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("""
            UPDATE weekly_schedules
            SET 月曜日 = ?, 火曜日 = ?, 水曜日 = ?, 木曜日 = ?, 金曜日 = ?, 土曜日 = ?, 日曜日 = ?
            WHERE id = ?
        """, (monday, tuesday, wednesday, thursday, friday, saturday, sunday, schedule_id))
        conn.commit()
        conn.close()
        print(f"✅ 週間予定 (ID: {schedule_id}) を編集しました！")
    except sqlite3.Error as e:
        print(f"❌ データベースエラー: {e}")

# 週間予定コメントカラム追加
def add_comments_column():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    try:
        cur.execute("SELECT コメント FROM weekly_schedules LIMIT 1")
    except sqlite3.OperationalError:
        cur.execute("ALTER TABLE weekly_schedules ADD COLUMN コメント TEXT DEFAULT '[]'")
        conn.commit()
        print("✅ コメントカラムを追加しました！")
    finally:
        conn.close()

# 週間予定コメント保存
def save_weekly_schedule_comment(schedule_id, commenter, comment):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT コメント FROM weekly_schedules WHERE id = ?", (schedule_id,))
    row = cur.fetchone()
    if row:
        comments = json.loads(row[0]) if row[0] else []
        new_comment = {
            "投稿者": commenter, 
            "日時": (datetime.now() + timedelta(hours=9)).strftime("%Y-%m-%d %H:%M:%S"), 
            "コメント": comment
        }
        comments.append(new_comment)
        cur.execute("UPDATE weekly_schedules SET コメント = ? WHERE id = ?", (json.dumps(comments), schedule_id))
        conn.commit()
    conn.close()

# 週間予定編集
def update_weekly_schedule(schedule_id, monday, tuesday, wednesday, thursday, friday, saturday, sunday):
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("""
            UPDATE weekly_schedules
            SET 月曜日 = ?, 火曜日 = ?, 水曜日 = ?, 木曜日 = ?, 金曜日 = ?, 土曜日 = ?, 日曜日 = ?
            WHERE id = ?
        """, (monday, tuesday, wednesday, thursday, friday, saturday, sunday, schedule_id))
        conn.commit()
        conn.close()
        print(f"✅ 週間予定 (ID: {schedule_id}) を編集しました！")
    except sqlite3.Error as e:
        print(f"❌ データベースエラー: {e}")

# 週間予定削除
def delete_weekly_schedule(schedule_id):
    try:
        with sqlite3.connect(DB_PATH) as conn:
            c = conn.cursor()
            print(f"️ 週間予定削除処理開始: schedule_id={schedule_id}")
            c.execute("DELETE FROM weekly_schedules WHERE id = ?", (schedule_id,))
            conn.commit()
            if c.rowcount == 0:
                print(f"⚠️ 削除対象の週間予定（ID: {schedule_id}）が見つかりませんでした。")
                return False
            print("✅ 週間予定削除成功！")
            return True
    except sqlite3.Error as e:
        print(f"❌ データベースエラー: {e}")
        return False
