import os
import json
import logging
from datetime import datetime, timedelta
import psycopg2
from psycopg2 import sql
from psycopg2.extras import RealDictCursor, Json

# Neon Database connection information
DB_HOST = os.getenv("PGHOST", "ep-dawn-credit-a16vhe5b-pooler.ap-southeast-1.aws.neon.tech")
DB_NAME = os.getenv("PGDATABASE", "neondb")
DB_USER = os.getenv("PGUSER", "neondb_owner")
DB_PASSWORD = os.getenv("PGPASSWORD", "npg_E63kPJglOeih")
DB_PORT = os.getenv("PGPORT", "5432")

# ログ設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def get_db_connection():
    """PostgreSQLデータベースへの接続を作成"""
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            port=DB_PORT
        )
        return conn
    except Exception as e:
        logging.error(f"データベース接続エラー: {e}")
        raise

def init_db(keep_existing=True):
    """初期データベースセットアップ"""
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # 日報テーブル作成
        cur.execute('''
            CREATE TABLE IF NOT EXISTS reports (
                id SERIAL PRIMARY KEY,
                投稿者 TEXT,
                所属部署 TEXT,
                日付 DATE,
                業務内容 TEXT,
                メンバー状況 TEXT,
                作業時間 TEXT,
                翌日予定 TEXT,
                相談事項 TEXT,
                投稿日時 TIMESTAMP,
                reactions JSONB DEFAULT '{}',
                comments JSONB DEFAULT '[]'
            )
        ''')
        
        # お知らせテーブル作成
        cur.execute('''
            CREATE TABLE IF NOT EXISTS notices (
                id SERIAL PRIMARY KEY,
                投稿者 TEXT,
                タイトル TEXT,
                内容 TEXT,
                対象部署 TEXT,
                投稿日時 TIMESTAMP,
                既読者 JSONB DEFAULT '[]'
            )
        ''')
        
        # 週間予定テーブル作成
        cur.execute('''
            CREATE TABLE IF NOT EXISTS weekly_schedules (
                id SERIAL PRIMARY KEY,
                投稿者 TEXT,
                開始日 DATE,
                終了日 DATE,
                月曜日 TEXT,
                火曜日 TEXT,
                水曜日 TEXT,
                木曜日 TEXT,
                金曜日 TEXT,
                土曜日 TEXT,
                日曜日 TEXT,
                投稿日時 TIMESTAMP,
                コメント JSONB DEFAULT '[]'
            )
        ''')
        
        # 通知テーブル作成
        cur.execute('''
            CREATE TABLE IF NOT EXISTS notifications (
                id SERIAL PRIMARY KEY,
                user_name TEXT,
                content TEXT,
                link_type TEXT,
                link_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_read BOOLEAN DEFAULT FALSE
            )
        ''')
        
        conn.commit()
        logging.info("データベースを初期化しました")
    except Exception as e:
        logging.error(f"データベース初期化エラー: {e}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()

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
                # adminフィールドが存在しない場合はデフォルトでFalseを設定
                if "admin" not in user:
                    user["admin"] = False
                return user
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logging.error(f"ユーザー認証エラー: {e}")
        pass

    return None

def save_report(report):
    """日報をデータベースに保存"""
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # 投稿日時を JST で保存
        report["投稿日時"] = (datetime.now() + timedelta(hours=9)).strftime("%Y-%m-%d %H:%M:%S")
        
        cur.execute("""
            INSERT INTO reports (投稿者, 所属部署, 日付, 業務内容, メンバー状況, 作業時間, 翌日予定, 相談事項, 投稿日時)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (
            report["投稿者"], report["所属部署"], report["日付"],
            report["業務内容"], report["メンバー状況"], report["作業時間"],
            report["翌日予定"], report["相談事項"], report["投稿日時"]
        ))
        
        report_id = cur.fetchone()[0]
        conn.commit()
        logging.info(f"日報を保存しました（ID: {report_id}）")
        return report_id
    except Exception as e:
        logging.error(f"日報保存エラー: {e}")
        if conn:
            conn.rollback()
        return None
    finally:
        if conn:
            conn.close()

def load_reports(depart=None, limit=None):
    """日報データを取得（最新の投稿順にソート）"""
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        query = "SELECT * FROM reports"
        params = []
        
        if depart:
            query += " WHERE 所属部署 = %s"
            params.append(depart)
        
        query += " ORDER BY 投稿日時 DESC"
        
        if limit:
            query += " LIMIT %s"
            params.append(limit)
        
        cur.execute(query, params)
        reports = cur.fetchall()
        
        # 辞書形式に変換
        result = []
        for report in reports:
            # 文字列から辞書へ変換
            if isinstance(report["reactions"], str):
                report["reactions"] = json.loads(report["reactions"])
            if isinstance(report["comments"], str):
                report["comments"] = json.loads(report["comments"])
            result.append(dict(report))
        
        return result
    except Exception as e:
        logging.error(f"日報取得エラー: {e}")
        return []
    finally:
        if conn:
            conn.close()

def load_report_by_id(report_id):
    """指定されたIDの日報を取得"""
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        cur.execute("SELECT * FROM reports WHERE id = %s", (report_id,))
        report = cur.fetchone()
        
        if report:
            # 文字列から辞書へ変換
            if isinstance(report["reactions"], str):
                report["reactions"] = json.loads(report["reactions"])
            if isinstance(report["comments"], str):
                report["comments"] = json.loads(report["comments"])
            return dict(report)
        return None
    except Exception as e:
        logging.error(f"日報取得エラー (ID: {report_id}): {e}")
        return None
    finally:
        if conn:
            conn.close()

def edit_report(report_id, updated_report):
    """日報を編集"""
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute("""
            UPDATE reports
            SET 業務内容 = %s, メンバー状況 = %s, 作業時間 = %s, 翌日予定 = %s, 相談事項 = %s
            WHERE id = %s
        """, (
            updated_report["業務内容"], updated_report["メンバー状況"], 
            updated_report["作業時間"], updated_report["翌日予定"], 
            updated_report["相談事項"], report_id
        ))
        
        conn.commit()
        logging.info(f"日報を編集しました（ID: {report_id}）")
        return True
    except Exception as e:
        logging.error(f"日報編集エラー: {e}")
        if conn:
            conn.rollback()
        return False
    finally:
        if conn:
            conn.close()

def delete_report(report_id):
    """日報を削除"""
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute("DELETE FROM reports WHERE id = %s", (report_id,))
        conn.commit()
        logging.info(f"日報を削除しました（ID: {report_id}）")
        return True
    except Exception as e:
        logging.error(f"日報削除エラー: {e}")
        if conn:
            conn.rollback()
        return False
    finally:
        if conn:
            conn.close()

def update_reaction(report_id, user_name, reaction_type):
    """日報へのリアクション更新"""
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # 現在のリアクションを取得
        cur.execute("SELECT reactions FROM reports WHERE id = %s", (report_id,))
        result = cur.fetchone()
        
        if not result:
            return False
            
        reactions = result[0] if result[0] else {}
        if isinstance(reactions, str):
            reactions = json.loads(reactions)
        
        # リアクション更新
        if reaction_type not in reactions:
            reactions[reaction_type] = []
            
        user_exists = user_name in reactions[reaction_type]
        
        if user_exists:
            reactions[reaction_type].remove(user_name)
            if not reactions[reaction_type]:  # 空なら削除
                del reactions[reaction_type]
        else:
            reactions[reaction_type].append(user_name)
        
        # 更新をデータベースに保存
        cur.execute(
            "UPDATE reports SET reactions = %s WHERE id = %s",
            (Json(reactions), report_id)
        )
        
        conn.commit()
        logging.info(f"リアクションを更新しました（ID: {report_id}, ユーザー: {user_name}, タイプ: {reaction_type}）")
        return True
    except Exception as e:
        logging.error(f"リアクション更新エラー: {e}")
        if conn:
            conn.rollback()
        return False
    finally:
        if conn:
            conn.close()

def save_comment(report_id, comment):
    """日報にコメントを追加"""
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # 現在の日報とコメントを取得
        cur.execute("SELECT 投稿者, comments, 日付 FROM reports WHERE id = %s", (report_id,))
        result = cur.fetchone()
        
        if not result:
            return False
            
        report_author = result[0]
        comments = result[1] if result[1] else []
        report_date = result[2]
        
        if isinstance(comments, str):
            comments = json.loads(comments)
        
        # コメント追加
        comment["投稿日時"] = (datetime.now() + timedelta(hours=9)).strftime("%Y-%m-%d %H:%M:%S")
        comments.append(comment)
        
        # 更新をデータベースに保存
        cur.execute(
            "UPDATE reports SET comments = %s WHERE id = %s",
            (Json(comments), report_id)
        )
        
        conn.commit()
        logging.info(f"コメントを追加しました（ID: {report_id}, ユーザー: {comment['投稿者']}）")
        
        # 投稿主に通知を送信（自分自身へのコメント以外）
        if comment["投稿者"] != report_author:
            notification_content = f"{comment['投稿者']}さんがあなたの投稿にコメントしました。投稿: {report_date}"
            create_notification(
                report_author, 
                notification_content,
                "report", 
                report_id
            )
            logging.info(f"{report_author}さんに通知を送信しました")
        
        return True
    except Exception as e:
        logging.error(f"コメント追加エラー: {e}")
        if conn:
            conn.rollback()
        return False
    finally:
        if conn:
            conn.close()

def load_commented_reports(user_name):
    """指定ユーザーがコメントした日報を取得"""
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # JSONBフィールドを検索するクエリ
        cur.execute("""
            SELECT * FROM reports 
            WHERE comments @> '[{"投稿者": "%s"}]'
            ORDER BY 投稿日時 DESC
        """ % user_name)
        
        reports = cur.fetchall()
        
        # 辞書形式に変換
        result = []
        for report in reports:
            # 文字列から辞書へ変換
            if isinstance(report["reactions"], str):
                report["reactions"] = json.loads(report["reactions"])
            if isinstance(report["comments"], str):
                report["comments"] = json.loads(report["comments"])
            result.append(dict(report))
        
        return result
    except Exception as e:
        logging.error(f"コメント付き日報取得エラー: {e}")
        return []
    finally:
        if conn:
            conn.close()

def save_notice(notice):
    """お知らせをデータベースに保存"""
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # 投稿日時を JST で保存
        notice["投稿日時"] = (datetime.now() + timedelta(hours=9)).strftime("%Y-%m-%d %H:%M:%S")
        
        cur.execute("""
            INSERT INTO notices (投稿者, タイトル, 内容, 対象部署, 投稿日時, 既読者)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (
            notice["投稿者"], notice["タイトル"], notice["内容"],
            notice["対象部署"], notice["投稿日時"], Json([])
        ))
        
        notice_id = cur.fetchone()[0]
        conn.commit()
        logging.info(f"お知らせを保存しました（ID: {notice_id}）")
        return notice_id
    except Exception as e:
        logging.error(f"お知らせ保存エラー: {e}")
        if conn:
            conn.rollback()
        return None
    finally:
        if conn:
            conn.close()

def load_notices(depart=None):
    """お知らせデータを取得（最新の投稿順にソート）"""
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        query = "SELECT * FROM notices"
        params = []
        
        if depart:
            query += " WHERE 対象部署 = %s OR 対象部署 = 'すべて'"
            params.append(depart)
        
        query += " ORDER BY 投稿日時 DESC"
        
        cur.execute(query, params)
        notices = cur.fetchall()
        
        # 辞書形式に変換
        result = []
        for notice in notices:
            # 文字列から辞書へ変換
            if isinstance(notice["既読者"], str):
                notice["既読者"] = json.loads(notice["既読者"])
            result.append(dict(notice))
        
        return result
    except Exception as e:
        logging.error(f"お知らせ取得エラー: {e}")
        return []
    finally:
        if conn:
            conn.close()

def mark_notice_as_read(notice_id, user_name):
    """お知らせを既読としてマーク"""
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # 現在の既読者リストを取得
        cur.execute("SELECT 既読者 FROM notices WHERE id = %s", (notice_id,))
        result = cur.fetchone()
        
        if not result:
            return False
            
        read_by = result[0] if result[0] else []
        if isinstance(read_by, str):
            read_by = json.loads(read_by)
        
        # ユーザーが既に既読リストにいなければ追加
        if user_name not in read_by:
            read_by.append(user_name)
            
            # 更新をデータベースに保存
            cur.execute(
                "UPDATE notices SET 既読者 = %s WHERE id = %s",
                (Json(read_by), notice_id)
            )
            
            conn.commit()
            logging.info(f"お知らせを既読にしました（ID: {notice_id}, ユーザー: {user_name}）")
        
        return True
    except Exception as e:
        logging.error(f"お知らせ既読エラー: {e}")
        if conn:
            conn.rollback()
        return False
    finally:
        if conn:
            conn.close()

def save_weekly_schedule(schedule):
    """週間予定をデータベースに保存"""
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # 投稿日時を JST で保存
        schedule["投稿日時"] = (datetime.now() + timedelta(hours=9)).strftime("%Y-%m-%d %H:%M:%S")
        
        cur.execute("""
            INSERT INTO weekly_schedules (投稿者, 開始日, 終了日, 月曜日, 火曜日, 水曜日, 木曜日, 金曜日, 土曜日, 日曜日, 投稿日時)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (
            schedule["投稿者"], schedule["開始日"], schedule["終了日"],
            schedule["月曜日"], schedule["火曜日"], schedule["水曜日"],
            schedule["木曜日"], schedule["金曜日"], schedule["土曜日"],
            schedule["日曜日"], schedule["投稿日時"]
        ))
        
        schedule_id = cur.fetchone()[0]
        conn.commit()
        logging.info(f"週間予定を保存しました（ID: {schedule_id}）")
        return schedule_id
    except Exception as e:
        logging.error(f"週間予定保存エラー: {e}")
        if conn:
            conn.rollback()
        return None
    finally:
        if conn:
            conn.close()

def load_weekly_schedules():
    """週間予定データを取得（最新の投稿順にソート）"""
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        cur.execute("SELECT * FROM weekly_schedules ORDER BY 投稿日時 DESC")
        schedules = cur.fetchall()
        
        # 辞書形式に変換
        result = []
        for schedule in schedules:
            # コメントをJSONから変換
            if isinstance(schedule["コメント"], str):
                schedule["コメント"] = json.loads(schedule["コメント"])
            result.append(dict(schedule))
        
        return result
    except Exception as e:
        logging.error(f"週間予定取得エラー: {e}")
        return []
    finally:
        if conn:
            conn.close()

def save_weekly_schedule_comment(schedule_id, comment):
    """週間予定にコメントを追加"""
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # 現在の週間予定情報とコメントを取得
        cur.execute("SELECT 投稿者, コメント, 開始日, 終了日 FROM weekly_schedules WHERE id = %s", (schedule_id,))
        result = cur.fetchone()
        
        if not result:
            return False
        
        schedule_author = result[0]
        comments = result[1] if result[1] else []
        start_date = result[2]
        end_date = result[3]
        
        if isinstance(comments, str):
            comments = json.loads(comments)
        
        # コメント追加
        comment["投稿日時"] = (datetime.now() + timedelta(hours=9)).strftime("%Y-%m-%d %H:%M:%S")
        comments.append(comment)
        
        # 更新をデータベースに保存
        cur.execute(
            "UPDATE weekly_schedules SET コメント = %s WHERE id = %s",
            (Json(comments), schedule_id)
        )
        
        conn.commit()
        logging.info(f"週間予定コメント追加（ID: {schedule_id}, ユーザー: {comment['投稿者']}）")
        
        # 投稿主に通知を送信（自分自身へのコメント以外）
        if comment["投稿者"] != schedule_author:
            notification_content = f"{comment['投稿者']}さんがあなたの週間予定にコメントしました。期間: {start_date} 〜 {end_date}"
            create_notification(
                schedule_author, 
                notification_content,
                "weekly_schedule", 
                schedule_id
            )
            logging.info(f"{schedule_author}さんに通知を送信しました")
        
        return True
    except Exception as e:
        logging.error(f"週間予定コメント追加エラー: {e}")
        if conn:
            conn.rollback()
        return False
    finally:
        if conn:
            conn.close()

def add_comments_column():
    """週間予定テーブルにコメントカラムが存在することを保証"""
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # カラムが存在するか確認
        cur.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'weekly_schedules' AND column_name = 'コメント'
        """)
        
        if not cur.fetchone():
            # カラム追加
            cur.execute("ALTER TABLE weekly_schedules ADD COLUMN コメント JSONB DEFAULT '[]'")
            conn.commit()
            logging.info("週間予定テーブルにコメントカラムを追加しました")
        
        return True
    except Exception as e:
        logging.error(f"コメントカラム追加エラー: {e}")
        if conn:
            conn.rollback()
        return False
    finally:
        if conn:
            conn.close()

def create_notification(user_name, content, link_type, link_id):
    """ユーザーへの通知を作成"""
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute("""
            INSERT INTO notifications (user_name, content, link_type, link_id, created_at, is_read)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (
            user_name, content, link_type, link_id, 
            (datetime.now() + timedelta(hours=9)).strftime("%Y-%m-%d %H:%M:%S"),
            False
        ))
        
        notification_id = cur.fetchone()[0]
        conn.commit()
        logging.info(f"通知を作成しました（ID: {notification_id}, ユーザー: {user_name}）")
        return notification_id
    except Exception as e:
        logging.error(f"通知作成エラー: {e}")
        if conn:
            conn.rollback()
        return None
    finally:
        if conn:
            conn.close()

def get_user_notifications(user_name, unread_only=False):
    """ユーザーの通知を取得"""
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        query = "SELECT * FROM notifications WHERE user_name = %s"
        params = [user_name]
        
        if unread_only:
            query += " AND is_read = FALSE"
            
        query += " ORDER BY created_at DESC"
        
        cur.execute(query, params)
        notifications = cur.fetchall()
        
        return [dict(notification) for notification in notifications]
    except Exception as e:
        logging.error(f"通知取得エラー: {e}")
        return []
    finally:
        if conn:
            conn.close()

def mark_notification_as_read(notification_id):
    """通知を既読としてマーク"""
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute("""
            UPDATE notifications
            SET is_read = TRUE
            WHERE id = %s
        """, (notification_id,))
        
        conn.commit()
        logging.info(f"通知を既読にしました（ID: {notification_id}）")
        return True
    except Exception as e:
        logging.error(f"通知既読エラー: {e}")
        if conn:
            conn.rollback()
        return False
    finally:
        if conn:
            conn.close()

def mark_all_notifications_as_read(user_name):
    """ユーザーの全通知を既読としてマーク"""
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute("""
            UPDATE notifications
            SET is_read = TRUE
            WHERE user_name = %s AND is_read = FALSE
        """, (user_name,))
        
        conn.commit()
        logging.info(f"全通知を既読にしました（ユーザー: {user_name}）")
        return True
    except Exception as e:
        logging.error(f"全通知既読エラー: {e}")
        if conn:
            conn.rollback()
        return False
    finally:
        if conn:
            conn.close()
