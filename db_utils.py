import sqlite3
import json
from datetime import datetime, timedelta
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

DB_PATH = "/mount/src/ok-nippou-kun/data/reports.db"

def get_db_connection():
    try: conn = sqlite3.connect(DB_PATH); logging.info("データベース接続成功"); return conn
    except sqlite3.Error as e: logging.error(f"データベース接続エラー: {e}"); return None

def authenticate_user(employee_code, password):
    try:
        with open("data/users_data.json", "r", encoding="utf-8-sig") as file: users = json.load(file)
        return next((user for user in users if user["code"] == employee_code and user["password"] == password), None)
    except (FileNotFoundError, json.JSONDecodeError): return None

def init_db(keep_existing=True):
    conn = get_db_connection(); if conn is None: return
    cur = conn.cursor()
    if not keep_existing: cur.execute("DROP TABLE IF EXISTS reports"); cur.execute("DROP TABLE IF EXISTS notices"); cur.execute("DROP TABLE IF EXISTS weekly_schedules")
    cur.execute("""CREATE TABLE IF NOT EXISTS reports (id INTEGER PRIMARY KEY AUTOINCREMENT, 投稿者 TEXT, 実行日 TEXT, カテゴリ TEXT, 場所 TEXT, 実施内容 TEXT, 所感 TEXT, いいね INTEGER DEFAULT 0, ナイスファイト INTEGER DEFAULT 0, コメント TEXT DEFAULT '[]', 画像 TEXT, 投稿日時 TEXT)""")
    cur.execute("""CREATE TABLE IF NOT EXISTS notices (id INTEGER PRIMARY KEY AUTOINCREMENT, タイトル TEXT, 内容 TEXT, 日付 TEXT, 既読 INTEGER DEFAULT 0, 対象ユーザー TEXT)""")
    cur.execute("""CREATE TABLE IF NOT EXISTS weekly_schedules (id INTEGER PRIMARY KEY AUTOINCREMENT, 投稿者 TEXT, 開始日 TEXT, 終了日 TEXT, 月曜日 TEXT, 火曜日 TEXT, 水曜日 TEXT, 木曜日 TEXT, 金曜日 TEXT, 土曜日 TEXT, 日曜日 TEXT, 投稿日時 TEXT, コメント TEXT DEFAULT '[]')""")
    conn.commit(); conn.close()

def update_db_schema():
    conn = get_db_connection(); if conn is None: return
    cur = conn.cursor(); cur.execute("PRAGMA table_info(notices)"); columns = [col[1] for col in cur.fetchall()]
    if "対象ユーザー" not in columns:
        try: cur.execute("ALTER TABLE notices ADD COLUMN 対象ユーザー TEXT"); conn.commit(); logging.info("対象ユーザーカラムを追加しました")
        except Exception as e: logging.error(f"スキーマ更新エラー: {e}")
    else: logging.info("対象ユーザーカラムは既に存在します")
    conn.close()

update_db_schema()

def save_report(report):
    conn = get_db_connection(); if conn is None: return
    try:
        cur = conn.cursor(); report["投稿日時"] = (datetime.now() + timedelta(hours=9)).strftime("%Y-%m-%d %H:%M:%S")
        if '実行日' not in report or not report['実行日']: report['実行日'] = (datetime.now() + timedelta(hours=9)).strftime("%Y-%m-%d")
        cur.execute("""INSERT INTO reports (投稿者, 実行日, カテゴリ, 場所, 実施内容, 所感, いいね, ナイスファイト, コメント, 画像, 投稿日時) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""", (report["投稿者"], report["実行日"], report["カテゴリ"], report["場所"], report["実施内容"], report["所感"], 0, 0, json.dumps([]), report.get("image", None), report["投稿日時"]))
        conn.commit(); logging.info(f"日報を保存しました（投稿者: {report['投稿者']}, 実行日: {report['実行日']}）")
    except sqlite3.Error as e: logging.error(f"データベースエラー: {e}"); conn.rollback(); raise
    except Exception as e: logging.error(f"予期せぬエラー: {e}"); conn.rollback(); raise
    finally: conn.close()

def load_reports():
    conn = get_db_connection(); if conn is None: return []
    cur = conn.cursor(); cur.execute("SELECT * FROM reports ORDER BY 投稿日時 DESC"); rows = cur.fetchall(); conn.close()
    return [{ "id": row[0], "投稿者": row[1], "実行日": row[2], "カテゴリ": row[3], "場所": row[4], "実施内容": row[5], "所感": row[6], "いいね": row[7], "ナイスファイト": row[8], "コメント": json.loads(row[9]), "image": row[10], "投稿日時": row[11] } for row in rows]

def update_reaction(report_id, reaction_type):
    conn = get_db_connection(); if conn is None: return
    cur = conn.cursor(); cur.execute(f"UPDATE reports SET {reaction_type} = {reaction_type} + 1 WHERE id = ?", (report_id,)); conn.commit(); conn.close()

def save_comment(report_id, commenter, comment):
    conn = get_db_connection(); if conn is None: return
    try:
        cur = conn.cursor(); cur.execute("UPDATE reports SET コメント = json_set(コメント, '$[last()]', json_object('投稿者', ?, 'コメント', ?, '日時', ?) ) WHERE id = ?", (commenter, comment, (datetime.now() + timedelta(hours=9)).strftime("%Y-%m-%d %H:%M:%S"), report_id))
        conn.commit(); logging.info(f"コメントを保存しました（投稿ID: {report_id}, 投稿者: {commenter}）")
    except sqlite3.Error as e: logging.error(f"コメント保存エラー: {e}"); conn.rollback(); raise
    except Exception as e: logging.error(f"予期せぬエラー: {e}"); conn.rollback(); raise
    finally: conn.close()

def load_commented_reports(user_name):
    conn = get_db_connection(); if conn is None: return []
    cur = conn.cursor(); cur.execute("SELECT * FROM reports WHERE コメント LIKE ?", f'%"{user_name}"%'); rows = cur.fetchall(); conn.close()
    return [{ "id": row[0], "投稿者": row[1], "実行日": row[2], "カテゴリ": row[3], "場所": row[4], "実施内容": row[5], "所感": row[6], "いいね": row[7], "ナイスファイト": row[8], "コメント": json.loads(row[9]), "image": row[10], "投稿日時": row[11] } for row in rows]

def save_notice(notice):
    conn = get_db_connection(); if conn is None: return
    try:
        cur = conn.cursor(); cur.execute("INSERT INTO notices (タイトル, 内容, 日付, 対象ユーザー) VALUES (?, ?, ?, ?)", (notice["タイトル"], notice["内容"], (datetime.now() + timedelta(hours=9)).strftime("%Y-%m-%d %H:%M:%S"), notice["対象ユーザー"])); conn.commit(); logging.info("お知らせを保存しました")
    except sqlite3.Error as e: logging.error(f"お知らせ保存エラー: {e}"); conn.rollback(); raise
    except Exception as e: logging.error(f"予期せぬエラー: {e}"); conn.rollback(); raise
    finally: conn.close()

def load_notices(user_name):
    conn = get_db_connection(); if conn is None: return []
    cur = conn.cursor(); cur.execute("SELECT * FROM notices WHERE 対象ユーザー = ? OR 対象ユーザー IS NULL", (user_name,)); rows = cur.fetchall(); conn.close()
    return [{ "id": row[0], "タイトル": row[1], "内容": row[2], "日付": row[3], "既読": row[4], "対象ユーザー": row[5] } for row in rows]

def mark_notice_as_read(notice_id):
    conn = get_db_connection(); if conn is None: return
    try: cur = conn.cursor(); cur.execute("UPDATE notices SET 既読 = 1 WHERE id = ?", (notice_id,)); conn.commit(); logging.info(f"お知らせID {notice_id} を既読にしました")
    except sqlite3.Error as e: logging.error(f"既読更新エラー: {e}"); conn.rollback(); raise
    except Exception as e: logging.error(f"予期せぬエラー: {e}"); conn.rollback(); raise
    finally: conn.close()

def save_weekly_schedule(schedule):
    conn = get_db_connection(); if conn is None: return
    try: cur = conn.cursor(); cur.execute("INSERT INTO weekly_schedules (投稿者, 開始日, 終了日, 月曜日, 火曜日, 水曜日, 木曜日, 金曜日, 土曜日, 日曜日, 投稿日時) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (schedule["投稿者"], schedule["開始日"], schedule["終了日"], schedule["月曜日"], schedule["火曜日"], schedule["水曜日"], schedule["木曜日"], schedule["金曜日"], schedule["土曜日"], schedule["日曜日"], schedule["投稿日時"])); conn.commit(); logging.info("週間予定を保存しました")
except Exception as e: logging.error(f"週間予定保存エラー: {e}"); conn.rollback(); raise
    finally: conn.close()

def load_weekly_schedules():
    conn = get_db_connection(); if conn is None: return []
    cur = conn.cursor(); cur.execute("SELECT *, コメント FROM weekly_schedules ORDER BY 投稿日時 DESC"); rows = cur.fetchall(); conn.close()
    return [{ "id": row[0], "投稿者": row[1], "開始日": row[2], "終了日": row[3], "月曜日": row[4], "火曜日": row[5], "水曜日": row[6], "木曜日": row[7], "金曜日": row[8], "土曜日": row[9], "日曜日": row[10], "投稿日時": row[11], "コメント": json.loads(row[12]) if row[12] else [] } for row in rows]

def save_weekly_schedule_comment(schedule_id, commenter, comment):
    conn = get_db_connection(); if conn is None: return
    try:
        cur = conn.cursor(); cur.execute("UPDATE weekly_schedules SET コメント = json_set(コメント, '$[last()]', json_object('投稿者', ?, 'コメント', ?, '日時', ?) ) WHERE id = ?", (commenter, comment, (datetime.now() + timedelta(hours=9)).strftime("%Y-%m-%d %H:%M:%S"), schedule_id))
        conn.commit(); logging.info(f"週間予定コメントを保存しました（予定ID: {schedule_id}, 投稿者: {commenter}）")
    except sqlite3.Error as e: logging.error(f"週間予定コメント保存エラー: {e}"); conn.rollback(); raise
    except Exception as e: logging.error(f"予期せぬエラー: {e}"); conn.rollback(); raise
    finally: conn.close()

def add_comments_column():
    conn = get_db_connection(); if conn is None: return
    try:
        cur = conn.cursor(); cur.execute("PRAGMA table_info(weekly_schedules)"); columns = [col[1] for col in cur.fetchall()]
        if "コメント" not in columns: cur.execute("ALTER TABLE weekly_schedules ADD COLUMN コメント TEXT DEFAULT '[]'"); conn.commit(); logging.info("週間予定テーブルにコメントカラムを追加しました")
        else: logging.info("週間予定テーブルには既にコメントカラムが存在します")
    except Exception as e: logging.error(f"週間予定テーブルの更新エラー: {e}")
    finally: conn.close()
