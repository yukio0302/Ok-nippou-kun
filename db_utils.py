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
                実施内容 TEXT,
                所感 TEXT,
                今後のアクション TEXT,
                投稿日時 TIMESTAMP,
                reactions JSONB DEFAULT '{}',
                comments JSONB DEFAULT '[]',
                visited_stores JSONB DEFAULT '[]'
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
                コメント JSONB DEFAULT '[]',
                月曜日_visited_stores JSONB DEFAULT '[]',
                火曜日_visited_stores JSONB DEFAULT '[]',
                水曜日_visited_stores JSONB DEFAULT '[]',
                木曜日_visited_stores JSONB DEFAULT '[]',
                金曜日_visited_stores JSONB DEFAULT '[]',
                土曜日_visited_stores JSONB DEFAULT '[]',
                日曜日_visited_stores JSONB DEFAULT '[]'
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
        
        # 店舗訪問履歴テーブル作成
        cur.execute('''
            CREATE TABLE IF NOT EXISTS store_visits (
                id SERIAL PRIMARY KEY,
                user_code TEXT,
                store_code TEXT,
                store_name TEXT,
                visit_date DATE,
                report_id INTEGER,
                visit_type TEXT
            )
        ''')
        
        # 画像テーブル作成
        cur.execute('''
            CREATE TABLE IF NOT EXISTS report_images (
                id SERIAL PRIMARY KEY,
                report_id INTEGER,
                file_name TEXT,
                file_type TEXT,
                image_data TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
        
        # 訪問した店舗情報を取得
        visited_stores = report.get("visited_stores", [])
        
        cur.execute("""
            INSERT INTO reports (投稿者, 所属部署, 日付, 実施内容, 所感, 今後のアクション, 投稿日時, visited_stores)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (
            report["投稿者"], report["所属部署"], report["日付"],
            report["実施内容"], report["所感"], report["今後のアクション"], 
            report["投稿日時"], Json(visited_stores)
        ))
        
        report_id = cur.fetchone()[0]
        
        # 訪問店舗の記録を保存
        user_code = report.get("user_code", "")
        for store in visited_stores:
            cur.execute("""
                INSERT INTO store_visits (user_code, store_code, store_name, visit_date, report_id, visit_type)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (
                user_code, 
                store.get("code", ""), 
                store.get("name", ""), 
                report["日付"],
                report_id,
                "daily_report"
            ))
        
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

def load_reports(depart=None, limit=None, time_range=None):
    """日報データを取得（最新の投稿順にソート）
    
    Args:
        depart: 部署でフィルタリング
        limit: 取得件数上限
        time_range: 時間範囲('24h'=24時間以内, '1w'=1週間以内, None=すべて)
    """
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        query = "SELECT * FROM reports"
        params = []
        where_added = False
        
        if depart:
            query += " WHERE 所属部署 = %s"
            params.append(depart)
            where_added = True
        
        # 時間範囲でフィルタリング
        if time_range:
            current_time = datetime.now() + timedelta(hours=9)  # JST
            
            if time_range == '24h':  # 24時間以内
                time_threshold = (current_time - timedelta(hours=24)).strftime("%Y-%m-%d %H:%M:%S")
                if where_added:
                    query += " AND 投稿日時 >= %s"
                else:
                    query += " WHERE 投稿日時 >= %s"
                    where_added = True
                params.append(time_threshold)
                
            elif time_range == '1w':  # 1週間以内
                time_threshold = (current_time - timedelta(days=7)).strftime("%Y-%m-%d %H:%M:%S")
                if where_added:
                    query += " AND 投稿日時 >= %s"
                else:
                    query += " WHERE 投稿日時 >= %s"
                    where_added = True
                params.append(time_threshold)
        
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
            if isinstance(report["visited_stores"], str):
                report["visited_stores"] = json.loads(report["visited_stores"])
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
            if isinstance(report["visited_stores"], str):
                report["visited_stores"] = json.loads(report["visited_stores"])
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
        
        # 訪問店舗情報も更新
        visited_stores = updated_report.get("visited_stores", [])
        
        cur.execute("""
            UPDATE reports
            SET 実施内容 = %s, 所感 = %s, 今後のアクション = %s, visited_stores = %s
            WHERE id = %s
        """, (
            updated_report["実施内容"], 
            updated_report["所感"], updated_report["今後のアクション"], 
            Json(visited_stores), report_id
        ))
        
        # 以前の訪問記録を削除
        cur.execute("DELETE FROM store_visits WHERE report_id = %s", (report_id,))
        
        # 更新された訪問記録を保存
        original_report = load_report_by_id(report_id)
        user_code = updated_report.get("user_code", "")
        for store in visited_stores:
            cur.execute("""
                INSERT INTO store_visits (user_code, store_code, store_name, visit_date, report_id, visit_type)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (
                user_code, 
                store.get("code", ""), 
                store.get("name", ""), 
                original_report["日付"],
                report_id,
                "daily_report"
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
        
        # 関連する店舗訪問記録も削除
        cur.execute("DELETE FROM store_visits WHERE report_id = %s", (report_id,))
        
        # 日報を削除
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
    """自分がコメントした日報を取得"""
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # Json データからコメント投稿者を検索するクエリ
        cur.execute("""
            SELECT * FROM reports 
            WHERE comments @> '[{"投稿者": "%s"}]'::jsonb 
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
            if isinstance(report["visited_stores"], str):
                report["visited_stores"] = json.loads(report["visited_stores"])
            result.append(dict(report))
        
        return result
    except Exception as e:
        logging.error(f"コメント付き日報取得エラー: {e}")
        return []
    finally:
        if conn:
            conn.close()

def load_notices(department=None):
    """お知らせを取得（最新の投稿順にソート）"""
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        if department:
            # 特定の部署向けのお知らせと全体向けのお知らせを取得
            query = """
                SELECT * FROM notices 
                WHERE 対象部署 = %s OR 対象部署 = '全体' 
                ORDER BY 投稿日時 DESC
            """
            cur.execute(query, (department,))
        else:
            # すべてのお知らせを取得
            query = "SELECT * FROM notices ORDER BY 投稿日時 DESC"
            cur.execute(query)
        
        notices = cur.fetchall()
        
        # 辞書形式に変換
        result = []
        for notice in notices:
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

def save_notice(notice):
    """お知らせをデータベースに保存"""
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute("""
            INSERT INTO notices (投稿者, タイトル, 内容, 対象部署, 投稿日時, 既読者)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (
            notice["投稿者"], notice["タイトル"], notice["内容"], 
            notice["対象部署"], notice["投稿日時"], Json(notice.get("既読者", []))
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

def load_reports_by_date(start_date, end_date, depart=None):
    """指定された期間の日報を取得"""
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        query = "SELECT * FROM reports WHERE 日付 BETWEEN %s AND %s"
        params = [start_date, end_date]
        
        if depart:
            query += " AND 所属部署 = %s"
            params.append(depart)
        
        query += " ORDER BY 日付 DESC, 投稿日時 DESC"
        
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
            if isinstance(report["visited_stores"], str):
                report["visited_stores"] = json.loads(report["visited_stores"])
            result.append(dict(report))
        
        return result
    except Exception as e:
        logging.error(f"日報取得エラー (期間: {start_date} 〜 {end_date}): {e}")
        return []
    finally:
        if conn:
            conn.close()

def mark_notice_as_read(notice_id, user_name):
    """お知らせを既読にする"""
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # 現在の既読者リストを取得
        cur.execute("SELECT 既読者 FROM notices WHERE id = %s", (notice_id,))
        result = cur.fetchone()
        
        if not result:
            return False
        
        read_users = result[0] if result[0] else []
        if isinstance(read_users, str):
            read_users = json.loads(read_users)
        
        # ユーザーが既に既読リストにいるかチェック
        if user_name not in read_users:
            read_users.append(user_name)
            
            # 更新をデータベースに保存
            cur.execute(
                "UPDATE notices SET 既読者 = %s WHERE id = %s",
                (Json(read_users), notice_id)
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

def create_notification(user_name, content, link_type, link_id):
    """通知を作成"""
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute("""
            INSERT INTO notifications (user_name, content, link_type, link_id)
            VALUES (%s, %s, %s, %s)
        """, (user_name, content, link_type, link_id))
        
        conn.commit()
        logging.info(f"通知を作成しました（ユーザー: {user_name}）")
        return True
    except Exception as e:
        logging.error(f"通知作成エラー: {e}")
        if conn:
            conn.rollback()
        return False
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
        
        # 辞書形式に変換
        result = []
        for notification in notifications:
            result.append(dict(notification))
        
        return result
    except Exception as e:
        logging.error(f"通知取得エラー: {e}")
        return []
    finally:
        if conn:
            conn.close()

def mark_notification_as_read(notification_id):
    """通知を既読にする"""
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute("UPDATE notifications SET is_read = TRUE WHERE id = %s", (notification_id,))
        
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

def save_weekly_schedule(schedule):
    """週間予定を保存"""
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # 投稿日時を JST で保存
        schedule["投稿日時"] = (datetime.now() + timedelta(hours=9)).strftime("%Y-%m-%d %H:%M:%S")
        
        # 各曜日の訪問店舗データを取得
        visited_stores = {
            "月曜日_visited_stores": schedule.get("月曜日_visited_stores", []),
            "火曜日_visited_stores": schedule.get("火曜日_visited_stores", []),
            "水曜日_visited_stores": schedule.get("水曜日_visited_stores", []),
            "木曜日_visited_stores": schedule.get("木曜日_visited_stores", []),
            "金曜日_visited_stores": schedule.get("金曜日_visited_stores", []),
            "土曜日_visited_stores": schedule.get("土曜日_visited_stores", []),
            "日曜日_visited_stores": schedule.get("日曜日_visited_stores", [])
        }
        
        cur.execute("""
            INSERT INTO weekly_schedules 
            (投稿者, 開始日, 終了日, 月曜日, 火曜日, 水曜日, 木曜日, 金曜日, 土曜日, 日曜日, 投稿日時,
             月曜日_visited_stores, 火曜日_visited_stores, 水曜日_visited_stores, 木曜日_visited_stores, 
             金曜日_visited_stores, 土曜日_visited_stores, 日曜日_visited_stores)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (
            schedule["投稿者"], schedule["開始日"], schedule["終了日"],
            schedule["月曜日"], schedule["火曜日"], schedule["水曜日"], schedule["木曜日"],
            schedule["金曜日"], schedule["土曜日"], schedule["日曜日"], schedule["投稿日時"],
            Json(visited_stores["月曜日_visited_stores"]), Json(visited_stores["火曜日_visited_stores"]), 
            Json(visited_stores["水曜日_visited_stores"]), Json(visited_stores["木曜日_visited_stores"]), 
            Json(visited_stores["金曜日_visited_stores"]), Json(visited_stores["土曜日_visited_stores"]), 
            Json(visited_stores["日曜日_visited_stores"])
        ))
        
        schedule_id = cur.fetchone()[0]
        
        # 店舗訪問記録を保存
        user_code = schedule.get("user_code", "")
        start_date = datetime.strptime(schedule["開始日"], "%Y-%m-%d").date()
        
        # 曜日ごとに店舗訪問を記録
        weekdays = ["月曜日", "火曜日", "水曜日", "木曜日", "金曜日", "土曜日", "日曜日"]
        for i, weekday in enumerate(weekdays):
            visit_date = start_date + timedelta(days=i)
            stores_key = f"{weekday}_visited_stores"
            
            for store in visited_stores[stores_key]:
                cur.execute("""
                    INSERT INTO store_visits (user_code, store_code, store_name, visit_date, report_id, visit_type)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (
                    user_code, 
                    store.get("code", ""), 
                    store.get("name", ""), 
                    visit_date,
                    schedule_id,
                    "weekly_schedule"
                ))
        
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
    """週間予定を取得（最新の投稿順にソート）"""
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        cur.execute("""
            SELECT * FROM weekly_schedules 
            ORDER BY 投稿日時 DESC
        """)
        
        schedules = cur.fetchall()
        
        # 辞書形式に変換
        result = []
        for schedule in schedules:
            if isinstance(schedule["コメント"], str):
                schedule["コメント"] = json.loads(schedule["コメント"])
                
            # 各曜日の訪問店舗データを変換
            for day in ["月曜日", "火曜日", "水曜日", "木曜日", "金曜日", "土曜日", "日曜日"]:
                key = f"{day}_visited_stores"
                if isinstance(schedule[key], str):
                    schedule[key] = json.loads(schedule[key])
                    
            result.append(dict(schedule))
        
        return result
    except Exception as e:
        logging.error(f"週間予定取得エラー: {e}")
        return []
    finally:
        if conn:
            conn.close()

def add_comments_column():
    """コメントカラムの存在を確認し、なければ追加"""
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # weekly_schedules テーブルにコメントカラムが存在するか確認
        cur.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'weekly_schedules' AND column_name = 'コメント'
        """)
        
        if not cur.fetchone():
            # コメントカラムを追加
            cur.execute("""
                ALTER TABLE weekly_schedules
                ADD COLUMN コメント JSONB DEFAULT '[]'
            """)
            conn.commit()
            logging.info("weekly_schedules テーブルにコメントカラムを追加しました")
        
        conn.commit()
    except Exception as e:
        logging.error(f"コメントカラム追加エラー: {e}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()

def save_weekly_schedule_comment(schedule_id, comment):
    """週間予定にコメントを追加"""
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # 現在のコメントを取得
        cur.execute("SELECT コメント FROM weekly_schedules WHERE id = %s", (schedule_id,))
        result = cur.fetchone()
        
        if not result:
            return False
        
        comments = result[0] if result[0] else []
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
        logging.info(f"週間予定にコメントを追加しました（ID: {schedule_id}, ユーザー: {comment['投稿者']}）")
        return True
    except Exception as e:
        logging.error(f"週間予定コメント追加エラー: {e}")
        if conn:
            conn.rollback()
        return False
    finally:
        if conn:
            conn.close()

def get_user_store_visits(user_code=None, user_name=None, year=None, month=None):
    """ユーザーの店舗訪問履歴を取得（月別）
    
    Args:
        user_code: ユーザーコード（社員コード）
        user_name: ユーザー名
        year: 年
        month: 月
    """
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        query = "SELECT v.* FROM store_visits v"
        params = []
        
        # ユーザーコードが指定されている場合
        if user_code:
            query += " WHERE v.user_code = %s"
            params.append(user_code)
        # ユーザー名が指定されている場合
        elif user_name:
            # reportsテーブルを結合してユーザー名から店舗訪問を検索
            query = """
                SELECT v.* FROM store_visits v
                JOIN reports r ON v.report_id = r.id
                WHERE r.投稿者 = %s
            """
            params.append(user_name)
        else:
            # どちらも指定されていない場合は空のリストを返す
            return []
        
        # 年月フィルタ
        if year and month:
            # 指定された年月の訪問履歴を取得
            start_date = f"{year}-{month:02d}-01"
            # 次の月の初日を計算
            if month == 12:
                next_year = year + 1
                next_month = 1
            else:
                next_year = year
                next_month = month + 1
            end_date = f"{next_year}-{next_month:02d}-01"
            
            if "WHERE" in query:
                query += " AND v.visit_date >= %s AND v.visit_date < %s"
            else:
                query += " WHERE v.visit_date >= %s AND v.visit_date < %s"
            params.extend([start_date, end_date])
        
        query += " ORDER BY visit_date DESC"
        
        cur.execute(query, params)
        visits = cur.fetchall()
        
        # 辞書形式に変換
        result = []
        for visit in visits:
            result.append(dict(visit))
        
        return result
    except Exception as e:
        logging.error(f"店舗訪問履歴取得エラー: {e}")
        return []
    finally:
        if conn:
            conn.close()

def get_user_stores(user_code):
    """ユーザーの担当店舗を取得"""
    try:
        store_file = "data/stores_data.json"
        
        if not os.path.exists(store_file):
            return []
        
        with open(store_file, "r", encoding="utf-8-sig") as file:
            stores = json.load(file)
        
        # ユーザーコードに一致する店舗を抽出
        user_stores = [store for store in stores if store.get("担当者社員コード") == user_code]
        return user_stores
    except Exception as e:
        logging.error(f"担当店舗取得エラー: {e}")
        return []

def search_stores(search_term):
    """店舗を名前や住所で検索する"""
    try:
        store_file = "data/stores_data.json"
        
        if not os.path.exists(store_file):
            return []
        
        with open(store_file, "r", encoding="utf-8-sig") as file:
            stores = json.load(file)
        
        # 検索語が空の場合は全店舗を返す
        if not search_term:
            return stores
            
        # 検索語を含む店舗を抽出
        search_term = search_term.lower()
        matched_stores = [
            store for store in stores 
            if search_term in store.get("name", "").lower() or 
               search_term in store.get("address", "").lower() or
               search_term in str(store.get("code", "")).lower()
        ]
        return matched_stores
    except Exception as e:
        logging.error(f"店舗検索エラー: {e}")
        return []

def get_store_visit_stats(user_code=None, year=None, month=None, user_name=None):
    """月ごとの店舗訪問統計を取得
    
    Args:
        user_code: ユーザーコード（社員コード）
        year: 年
        month: 月
        user_name: ユーザー名
    """
    visits = get_user_store_visits(user_code=user_code, user_name=user_name, year=year, month=month)
    
    # 店舗ごとの訪問回数を集計
    stats = {}
    for visit in visits:
        store_code = visit["store_code"]
        store_name = visit["store_name"]
        key = f"{store_code}:{store_name}"
        
        if key not in stats:
            stats[key] = {
                "code": store_code,
                "name": store_name,
                "count": 0,
                "dates": []
            }
        
        visit_date = visit["visit_date"].strftime("%Y-%m-%d") if isinstance(visit["visit_date"], datetime) else visit["visit_date"]
        if visit_date not in stats[key]["dates"]:
            stats[key]["dates"].append(visit_date)
            stats[key]["count"] += 1
    
    # 結果をリスト形式で返す
    result = [stats[key] for key in stats]
    return sorted(result, key=lambda x: x["count"], reverse=True)

def save_stores_data(stores_data):
    """店舗データをJSONファイルに保存"""
    try:
        # data ディレクトリがなければ作成
        os.makedirs("data", exist_ok=True)
        
        # JSONファイルに保存
        with open("data/stores_data.json", "w", encoding="utf-8") as file:
            json.dump(stores_data, file, ensure_ascii=False, indent=2)
        
        logging.info("店舗データを保存しました")
        return True
    except Exception as e:
        logging.error(f"店舗データ保存エラー: {e}")
        return False

def get_monthly_report_count(user_code=None, user_name=None, year=None, month=None):
    """月ごとの日報投稿数を取得
    
    Args:
        user_code: 特定ユーザーの投稿数のみを取得する場合に指定
        user_name: 特定ユーザー名の投稿数のみを取得する場合に指定
        year: 特定年のデータを取得する場合に指定
        month: 特定月のデータを取得する場合に指定
    
    Returns:
        ユーザーごとの月別投稿数データのリストまたは
        指定ユーザーの月別投稿数データのリスト
    """
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        query = """
            SELECT 
                投稿者, 
                TO_CHAR(日付, 'YYYY-MM') AS 年月, 
                COUNT(*) AS 投稿数
            FROM reports
            WHERE 1=1
        """
        params = []
        
        # ユーザーフィルタ
        if user_code:
            query += " AND user_code = %s"
            params.append(user_code)
            
        if user_name:
            query += " AND 投稿者 = %s"
            params.append(user_name)
        
        # 年月フィルタ
        if year:
            query += " AND EXTRACT(YEAR FROM 日付) = %s"
            params.append(year)
            
            if month:
                query += " AND EXTRACT(MONTH FROM 日付) = %s"
                params.append(month)
        
        query += " GROUP BY 投稿者, 年月 ORDER BY 年月 DESC, 投稿数 DESC"
        
        cur.execute(query, params)
        results = cur.fetchall()
        
        # 結果を辞書に変換
        data = []
        for row in results:
            data.append({
                "投稿者": row[0],
                "年月": row[1],
                "投稿数": row[2]
            })
        
        return data
    except Exception as e:
        logging.error(f"日報投稿数統計取得エラー: {e}")
        return []
    finally:
        if conn:
            conn.close()

def get_user_monthly_report_summary(user_code=None, user_name=None):
    """特定ユーザーの年月ごとの日報投稿数サマリーを取得
    
    Args:
        user_code: ユーザーコード
        user_name: ユーザー名
        
    Returns:
        各月の投稿数データの辞書
        {
            "2024-01": 5,
            "2024-02": 3,
            ...
        }
    """
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        query = """
            SELECT 
                TO_CHAR(日付, 'YYYY-MM') AS 年月, 
                COUNT(*) AS 投稿数
            FROM reports
            WHERE 1=1
        """
        params = []
        
        if user_code:
            query += " AND user_code = %s"
            params.append(user_code)
            
        if user_name:
            query += " AND 投稿者 = %s"
            params.append(user_name)
            
        query += " GROUP BY 年月 ORDER BY 年月 DESC"
        
        cur.execute(query, params)
        results = cur.fetchall()
        
        # 結果を辞書に変換
        data = {}
        for row in results:
            data[row[0]] = row[1]
        
        return data
    except Exception as e:
        logging.error(f"ユーザー日報サマリー取得エラー: {e}")
        return {}
    finally:
        if conn:
            conn.close()
            
def get_all_users():
    """システム内の全ユーザーの名前一覧を取得"""
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        query = """
            SELECT DISTINCT 投稿者
            FROM reports
            ORDER BY 投稿者
        """
        
        cur.execute(query)
        users = [row[0] for row in cur.fetchall()]
        
        return users
    except Exception as e:
        logging.error(f"ユーザー一覧取得エラー: {e}")
        return []
    finally:
        if conn:
            conn.close()

def get_all_users_store_visits(year=None, month=None):
    """全ユーザーの店舗訪問データを取得する
    
    Args:
        year: 年（指定しない場合は全期間）
        month: 月（指定しない場合は全期間または指定年の全月）
        
    Returns:
        ユーザー名をキー、店舗訪問統計リストを値とする辞書
    """
    try:
        # すべてのユーザー名を取得
        user_names = get_all_users()
        
        # 各ユーザーの店舗訪問データを取得
        result = {}
        for user_name in user_names:
            visits = get_store_visit_stats(user_name=user_name, year=year, month=month)
            if visits:  # 訪問データがある場合のみ追加
                result[user_name] = visits
        
        return result
    except Exception as e:
        logging.error(f"全ユーザー店舗訪問データ取得エラー: {e}")
        return {}

def save_report_image(report_id, file_name, file_type, image_data):
    """日報に添付された画像をデータベースに保存する
    
    Args:
        report_id: 関連する日報ID
        file_name: ファイル名
        file_type: ファイルの種類 (MIME type)
        image_data: base64エンコードされた画像データ
        
    Returns:
        画像ID (成功時) または None (失敗時)
    """
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute("""
            INSERT INTO report_images (report_id, file_name, file_type, image_data)
            VALUES (%s, %s, %s, %s)
            RETURNING id
        """, (report_id, file_name, file_type, image_data))
        
        image_id = cur.fetchone()[0]
        conn.commit()
        logging.info(f"画像を保存しました（ID: {image_id}, 日報ID: {report_id}）")
        return image_id
    except Exception as e:
        logging.error(f"画像保存エラー: {e}")
        if conn:
            conn.rollback()
        return None
    finally:
        if conn:
            conn.close()

def get_report_images(report_id):
    """特定の日報に関連付けられた画像を取得する
    
    Args:
        report_id: 日報ID
        
    Returns:
        画像情報のリスト
    """
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        cur.execute("""
            SELECT id, file_name, file_type, image_data, created_at
            FROM report_images 
            WHERE report_id = %s
            ORDER BY created_at ASC
        """, (report_id,))
        
        images = cur.fetchall()
        return [dict(img) for img in images]
    except Exception as e:
        logging.error(f"画像取得エラー（日報ID: {report_id}）: {e}")
        return []
    finally:
        if conn:
            conn.close()

def delete_report_image(image_id):
    """画像を削除する
    
    Args:
        image_id: 画像ID
        
    Returns:
        削除成功時はTrue、失敗時はFalse
    """
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute("DELETE FROM report_images WHERE id = %s", (image_id,))
        conn.commit()
        logging.info(f"画像を削除しました（ID: {image_id}）")
        return True
    except Exception as e:
        logging.error(f"画像削除エラー: {e}")
        if conn:
            conn.rollback()
        return False
    finally:
        if conn:
            conn.close()
