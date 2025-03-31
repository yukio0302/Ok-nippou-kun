import sqlite3
import json
import os
from datetime import datetime, timedelta
import streamlit as st

# ✅ データベースのパス
DB_PATH = "/mount/src/ok-nippou-kun/data/reports.db"

# db_utils.pyに追加
def get_db_connection():
    try:
        conn = sqlite3.connect(DB_PATH)
        return conn
    except sqlite3.Error as e:
        print(f"⚠️ データベース接続エラー: {e}")
        return None

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
    conn = get_db_connection()
    if conn is None:
        return

    cur = conn.cursor()

    if not keep_existing:
        cur.execute("DROP TABLE IF EXISTS reports")
        cur.execute("DROP TABLE IF EXISTS notices")
        cur.execute("DROP TABLE IF EXISTS weekly_schedules")  # 週間予定テーブルを削除

    # ✅ 日報データのテーブル作成（存在しない場合のみ）
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

    # ✅ お知らせデータのテーブル作成（存在しない場合のみ）
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

    # ✅ 週間予定データのテーブル作成（存在しない場合のみ）
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

def update_db_schema():
    """既存のデータベーススキーマを安全に更新する"""
    conn = get_db_connection()
    if conn is None:
        return

    cur = conn.cursor()

    # ✅ カラム存在チェック
    cur.execute("PRAGMA table_info(notices)")
    columns = [col[1] for col in cur.fetchall()]  # カラム名のリスト取得

    if "対象ユーザー" not in columns:
        try:
            cur.execute("ALTER TABLE notices ADD COLUMN 対象ユーザー TEXT")
            conn.commit()
            print("✅ 対象ユーザーカラムを追加しました！")
        except Exception as e:
            print(f"⚠️ スキーマ更新エラー: {e}")
    else:
        print("✅ 対象ユーザーカラムは既に存在します")

    conn.close()

# ✅ データベーススキーマを更新
update_db_schema()

def save_report(report):
    """日報をデータベースに保存（表示形式は変更しない安定版）"""
    conn = get_db_connection()
    if conn is None:
        return

    try:
        cur = conn.cursor()

        # 投稿日時をJSTで保存（元の形式保持）
        report["投稿日時"] = (datetime.now() + timedelta(hours=9)).strftime("%Y-%m-%d %H:%M:%S")

        # 実行日が未設定の場合のみ現在日付を使用
        if '実行日' not in report or not report['実行日']:
            report['実行日'] = (datetime.now() + timedelta(hours=9)).strftime("%Y-%m-%d")

        # 元のINSERT文をそのまま保持
        cur.execute("""
            INSERT INTO reports (投稿者, 実行日, カテゴリ, 場所, 実施内容, 所感, いいね, ナイスファイト, コメント, 画像, 投稿日時)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                report["投稿者"],
                report["実行日"],
                report["カテゴリ"],
                report["場所"],
                report["実施内容"],
                report["所感"],
                0,  # いいね初期値
                0,  # ナイスファイト初期値
                json.dumps([]),  # 空のコメント配列
                report.get("image", None),
                report["投稿日時"]
            ))

        conn.commit()
        print(f"✅ 日報を保存しました（投稿者: {report['投稿者']}, 実行日: {report['実行日']}）")

    except sqlite3.Error as e:
        print(f"⚠️ データベースエラー: {e}")
        conn.rollback()  # エラー発生時はロールバック
        raise  # 呼び出し元でエラーハンドリングさせる
    except Exception as e:
        print(f"⚠️ 予期せぬエラー: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

def load_reports():
    """日報データを取得（最新の投稿順にソート）"""
    conn = get_db_connection()
    if conn is None:
        return []

    cur = conn.cursor()

    cur.execute("SELECT * FROM reports ORDER BY 投稿日時 DESC")
    rows = cur.fetchall()
    conn.close()

    # ✅ データを辞書リストに変換
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
    conn = get_db_connection()
    if conn is None:
        return

    cur = conn.cursor()

    if reaction_type == "いいね":
        cur.execute("UPDATE reports SET いいね = いいね + 1 WHERE id = ?", (report_id,))
    elif reaction_type == "ナイスファイト":
        cur.execute("UPDATE reports SET ナイスファイト = ナイスファイト + 1 WHERE id = ?", (report_id,))

    conn.commit()
    conn.close()

def save_comment(report_id, commenter, comment):
    """コメントを保存＆通知を追加"""
    conn = get_db_connection()
    if conn is None:
        return

    cur = conn.cursor()

    # ✅ 投稿の情報を取得
    cur.execute("SELECT 投稿者, 実行日, 場所, 実施内容, コメント FROM reports WHERE id = ?", (report_id,))
    row = cur.fetchone()

    if row:
        投稿者 = row[0]  # 投稿者名
        実行日 = row[1]  # 実施日
        場所 = row[2]  # 場所
        実施内容 = row[3]  # 実施内容
        comments = json.loads(row[4]) if row[4] else []

        # ✅ 新しいコメントを追加
        new_comment = {
            "投稿者": commenter,
            "日時": (datetime.now() + timedelta(hours=9)).strftime("%Y-%m-%d %H:%M:%S"),
            "コメント": comment
        }
        comments.append(new_comment)

        # ✅ コメントを更新
        cur.execute("UPDATE reports SET コメント = ? WHERE id = ?", (json.dumps(comments), report_id))

        # ✅ 投稿者がコメント者と違う場合、投稿者にお知らせを追加
        if 投稿者 != commenter:
            notification_content = f"""【お知らせ】 
{new_comment["日時"]} 

実施日: {実行日} 
場所: {場所} 
実施内容: {実施内容} 

の投稿に {commenter} さんがコメントしました。 
コメント内容: {comment}
"""

            # ✅ お知らせを追加
            cur.execute("""
                INSERT INTO notices (タイトル, 内容, 日付, 既読, 対象ユーザー)
                VALUES (?, ?, ?, ?, ?)
                """, (
                    "新しいコメントが届きました！",
                    notification_content,
                    new_comment["日時"],
                    0,  # 既読フラグ（未読）
                    投稿者  # お知らせの対象ユーザー（日報投稿主）
                ))

        conn.commit()

    conn.close()

def load_commented_reports(commenter_name):
    """指定したユーザーがコメントした投稿を取得（コメント日時の降順でソート）"""
    conn = get_db_connection()
    if conn is None:
        return []

    cur = conn.cursor()

    cur.execute("SELECT * FROM reports")
    rows = cur.fetchall()
    conn.close()

    # コメントした投稿をフィルタリング
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
                    "コメント日時": comment["日時"]  # コメント日時を追加
                })
                break  # 同じ投稿に複数コメントがあっても1回だけ表示

    # コメント日時で降順にソート
    commented_reports.sort(key=lambda x: x["コメント日時"], reverse=True)

    return commented_reports

def load_notices(user_name):
    """お知らせデータを取得（対象ユーザーのみ）"""
    conn = get_db_connection()
    if conn is None:
        return []

    cur = conn.cursor()

    # ✅ 対象ユーザーに紐づくお知らせのみを取得
    cur.execute("SELECT * FROM notices WHERE 対象ユーザー = ? ORDER BY 日付 DESC", (user_name,))
    rows = cur.fetchall()
    conn.close()

    # ✅ データを辞書リストに変換
    notices = []
    for row in rows:
        notices.append({
            "id": row[0], "タイトル": row[1], "内容": row[2], "日付": row[3], "既読": row[4]
        })
    return notices

def mark_notice_as_read(notice_id):
    """お知らせを既読にする"""
    conn = get_db_connection()
    if conn is None:
        return

    cur = conn.cursor()

    cur.execute("UPDATE notices SET 既読 = 1 WHERE id = ?", (notice_id,))
    conn.commit()
    conn.close()

def edit_report(report_id, new_date, new_location, new_content, new_remarks):
    """投稿を編集する"""
    conn = get_db_connection()
    if conn is None:
        return

    try:
        c = conn.cursor()
        c.execute("""
            UPDATE reports
            SET 実行日 = ?, 場所 = ?, 実施内容 = ?, 所感 = ?
            WHERE id = ?
        """, (new_date, new_location, new_content, new_remarks, report_id))
        conn.commit()
        print(f"✅ 投稿 (ID: {report_id}) を編集しました！")  # デバッグ用ログ
    except sqlite3.Error as e:
        print(f"❌ データベースエラー: {e}")  # エラーログ
    finally:
        conn.close()

def delete_report(report_id):
    """投稿を削除する（エラーハンドリング付き）"""
    conn = get_db_connection()
    if conn is None:
        return False

    try:
        c = conn.cursor()
        print(f"️ 削除処理開始: report_id={report_id}")  # デバッグ用
        c.execute("DELETE FROM reports WHERE id = ?", (report_id,))
        conn.commit()

        # 削除が成功したかチェック
        if c.rowcount == 0:
            print(f"⚠️ 削除対象の投稿（ID: {report_id}）が見つかりませんでした。")
            return False

        print("✅ 削除成功！")
        return True

    except sqlite3.Error as e:
        print(f"❌ データベースエラー: {e}")
        return False
    finally:
        conn.close()

def save_weekly_schedule(schedule):
    """週間予定をデータベースに保存"""
    conn = get_db_connection()
    if conn is None:
        return

    try:
        cur = conn.cursor()

        # ✅ 投稿日時を JST で保存
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
        print("✅ 週間予定を保存しました！")  # デバッグログ
    except Exception as e:
        print(f"⚠️ 週間予定の保存エラー: {e}")  # エラー内容を表示
        conn.rollback()
    finally:
        conn.close()

def load_weekly_schedules():
    """週間予定データを取得（最新の投稿順にソート）"""
    conn = get_db_connection()
    if conn is None:
        return []

    cur = conn.cursor()

    cur.execute("SELECT *, コメント FROM weekly_schedules ORDER BY 投稿日時 DESC")  # コメントカラムも取得
    rows = cur.fetchall()
    conn.close()

    # ✅ データを辞書リストに変換
    schedules = []
    for row in rows:
        schedules.append({
            "id": row[0], "投稿者": row[1], "開始日": row[2], "終了日": row[3],
            "月曜日": row[4], "火曜日": row[5], "水曜日": row[6],
            "木曜日": row[7], "金曜日": row[8], "土曜日": row[9],
            "日曜日": row[10], "投稿日時": row[11],
            "コメント": json.loads(row[12]) if row[12] else []  # コメントをJSONデコード
        })
    return schedules

def update_weekly_schedule(schedule_id, monday, tuesday, wednesday, thursday, friday, saturday, sunday):
    """週間予定を更新する"""
    conn = get_db_connection()
    if conn is None:
        return

    try:
        cur = conn.cursor()
        cur.execute("""
            UPDATE weekly_schedules
            SET 月曜日 = ?, 火曜日 = ?, 水曜日 = ?, 木曜日 = ?, 金曜日 = ?, 土曜日 = ?, 日曜日 = ?
            WHERE id = ?
        """, (monday, tuesday, wednesday, thursday, friday, saturday, sunday, schedule_id))
        conn.commit()
        print(f"✅ 週間予定 (ID: {schedule_id}) を編集しました！")  # デバッグ用ログ
    except sqlite3.Error as e:
        print(f"❌ データベースエラー: {e}")  # エラーログ
        conn.rollback()
    finally:
        conn.close()

def add_comments_column():
    """weekly_schedules テーブルにコメントカラムを追加（存在しない場合のみ）"""
    conn = get_db_connection()
    if conn is None:
        return

    cur = conn.cursor()
    try:
        # カラムが存在するかチェック
        cur.execute("SELECT コメント FROM weekly_schedules LIMIT 1")
    except sqlite3.OperationalError:
        # カラムが存在しない場合のみ追加
        cur.execute("ALTER TABLE weekly_schedules ADD COLUMN コメント TEXT DEFAULT '[]'")
        conn.commit()
        print("✅ コメントカラムを追加しました！")
    finally:
        conn.close()

def save_weekly_schedule_comment(schedule_id, commenter, comment):
    """週間予定へのコメントを保存＆通知を追加"""
    conn = get_db_connection()
    if conn is None:
        return

    cur = conn.cursor()

    try:
        # 週間予定の情報を取得
        cur.execute("SELECT 投稿者, 開始日, 終了日, コメント FROM weekly_schedules WHERE id = ?", (schedule_id,))
        row = cur.fetchone()

        if row:
            投稿者 = row[0]
            開始日 = row[1]
            終了日 = row[2]
            comments = json.loads(row[3]) if row[3] else []

            # 新しいコメントを追加
            new_comment = {
                "投稿者": commenter,
                "日時": (datetime.now() + timedelta(hours=9)).strftime("%Y-%m-%d %H:%M:%S"),
                "コメント": comment
            }
            comments.append(new_comment)

            # コメントを更新
            cur.execute("UPDATE weekly_schedules SET コメント = ? WHERE id = ?", (json.dumps(comments, ensure_ascii=False), schedule_id))

            # 投稿者がコメント者と違う場合、投稿者にお知らせを追加
            if 投稿者 != commenter:
                notification_content = f"""【お知らせ】
{new_comment["日時"]}

期間: {開始日} ～ {終了日}
の週間予定投稿に {commenter} さんがコメントしました。
コメント内容: {comment}
"""
                # お知らせを追加
                cur.execute("""
                    INSERT INTO notices (タイトル, 内容, 日付, 既読, 対象ユーザー)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    "新しいコメントが届きました！",
                    notification_content,
                    new_comment["日時"],
                    0,  # 既読フラグ（未読）
                    投稿者  # お知らせの対象ユーザー（週間予定投稿主）
                ))

            conn.commit()
            print(f"✅ 週間予定 (ID: {schedule_id}) にコメントを保存し、通知を追加しました！")  # デバッグログ

    except sqlite3.Error as e:
        print(f"⚠️ 週間予定 (ID: {schedule_id}) へのコメント保存中にエラーが発生しました: {e}")  # エラーログ
        conn.rollback()  # エラー発生時はロールバック
    finally:
        conn.close()

def get_weekly_schedule_for_all_users(start_date, end_date):
    """
    指定期間の全ユーザーの週間予定データを取得する
    """
    conn = get_db_connection()
    if conn is None:
        return {}

    cursor = conn.cursor()

    cursor.execute("""
        SELECT user_id, schedule_date, schedule_content, comment
        FROM weekly_schedule
        WHERE schedule_date BETWEEN ? AND ?
    """, (start_date, end_date))

    results = cursor.fetchall()
    conn.close()

    # ユーザーごとにデータを整理
    user_schedules = {}
    for user_id, schedule_date, schedule_content, comment in results:
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
    conn = get_db_connection()
    if conn is None:
        return ""

    cur = conn.cursor()

    try:
        # 最新の週間予定から該当曜日の予定を取得
        cur.execute("""
            SELECT 開始日, 月曜日, 火曜日, 水曜日, 木曜日, 金曜日, 土曜日, 日曜日
            FROM weekly_schedules
            WHERE 投稿者 = ? AND ? BETWEEN 開始日 AND 終了日
            ORDER BY 投稿日時 DESC
            LIMIT 1
        """, (user_name, target_date))

        result = cur.fetchone()
        if not result:
            return ""

        start_date = datetime.strptime(result[0], "%Y-%m-%d").date()
        target = datetime.strptime(target_date, "%Y-%m-%d").date()
        day_diff = (target - start_date).days

        if 0 <= day_diff <= 6:
            return result[day_diff + 1]  # 月曜日=1 index

        return ""

    except sqlite3.Error as e:
        print(f"週間予定取得エラー: {e}")
        return ""
    finally:
        conn.close()
