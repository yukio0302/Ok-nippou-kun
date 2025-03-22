    import sqlite3
import json
import os
from datetime import datetime, timedelta
import streamlit as st

# ✅ データベースのパス
DB_PATH = "/mount/src/Ok-nippou-kun/data/reports.db"

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
    db_folder = os.path.dirname(DB_PATH)  # データフォルダのパスを取得
    os.makedirs(db_folder, exist_ok=True)  # データフォルダがなければ作成
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    if not keep_existing:
        cur.execute("DROP TABLE IF EXISTS reports")
        cur.execute("DROP TABLE IF EXISTS notices")
        cur.execute("DROP TABLE IF EXISTS weekly_plans")  # 週間予定テーブルを追加
        cur.execute("DROP TABLE IF EXISTS weekly_reports") # 週報テーブルを追加

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
            既読 INTEGER DEFAULT 0
        )
    """)

    # ✅ 週間予定データのテーブル作成（存在しない場合のみ）
    cur.execute("""
        CREATE TABLE IF NOT EXISTS weekly_plans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            投稿者 TEXT,
            週開始日 TEXT,
            週終了日 TEXT,
            予定 TEXT,
            いいね INTEGER DEFAULT 0,
            ナイスファイト INTEGER DEFAULT 0,
            コメント TEXT DEFAULT '[]',
            投稿日時 TEXT
        )
    """)

    # ✅ 週報データのテーブル作成（存在しない場合のみ）
    cur.execute("""
        CREATE TABLE IF NOT EXISTS weekly_reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            投稿者 TEXT,
            週開始日 TEXT,
            週終了日 TEXT,
            週報内容 TEXT,
            いいね INTEGER DEFAULT 0,
            ナイスファイト INTEGER DEFAULT 0,
            コメント TEXT DEFAULT '[]',
            投稿日時 TEXT
        )
    """)

    conn.commit()
    conn.close()

def save_report(report):
    """日報をデータベースに保存"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()

        # ✅ 投稿日時を JST で保存
        report["投稿日時"] = (datetime.now() + timedelta(hours=9)).strftime("%Y-%m-%d %H:%M:%S")

        cur.execute("""
            INSERT INTO reports (投稿者, 実行日, カテゴリ, 場所, 実施内容, 所感, いいね, ナイスファイト, コメント, 画像, 投稿日時)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            report["投稿者"], report["実行日"], report["カテゴリ"], report["場所"],
            report["実施内容"], report["所感"], 0, 0, json.dumps([]),
            report.get("image", None), report["投稿日時"]
        ))

        conn.commit()
        conn.execute("VACUUM")  # ← これで強制的にデータベースを更新
        conn.close()
        print("✅ データベースに日報を保存しました！")  # デバッグログ
    except Exception as e:
        print(f"⚠️ データベース保存エラー: {e}")  # エラー内容を表示

def load_reports():
    """日報データを取得（最新の投稿順にソート）"""
    conn = sqlite3.connect(DB_PATH)
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
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    if reaction_type == "いいね":
        cur.execute("UPDATE reports SET いいね = いいね + 1 WHERE id = ?", (report_id,))
    elif reaction_type == "ナイスファイト":
        cur.execute("UPDATE reports SET ナイスファイト = ナイスファイト + 1 WHERE id = ?", (report_id,))

    conn.commit()
    conn.close()

def save_comment(report_id, commenter, comment):
    """コメントを保存＆通知を追加"""
    conn = sqlite3.connect(DB_PATH)
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

        # ✅ 投稿者がコメント者と違う場合、お知らせを追加
        if 投稿者 != commenter:
            notification_content = f"""【お知らせ】
{new_comment["日時"]}

実施日: {実行日}
場所: {場所}
実施内容: {実施内容}

の投稿に {commenter} さんがコメントしました。
コメント内容: {comment}
"""

            cur.execute("""
                INSERT INTO notices (タイトル, 内容, 日付, 既読)
                VALUES (?, ?, ?, ?)
            """, (
                "新しいコメントが届きました！",
                notification_content,
                new_comment["日時"],
                0  # 既読フラグ（未読）
            ))

        conn.commit()

    conn.close()

def load_notices():
    """お知らせデータを取得"""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("SELECT * FROM notices ORDER BY 日付 DESC")
    rows = cur.fetchall()
    conn.close()

    # ✅ データを辞書リストに変換
    notices = []
    for row in rows:
        notices.append({
            "id": row[0], "タイトル": row[1], "内容": row[2], "日付": row[3], "既読": row
        })
    return notices

def mark_notice_as_read(notice_id):
    """お知らせを既読にする"""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("UPDATE notices SET 既読 = 1 WHERE id = ?", (notice_id,))
    conn.commit()
    conn.close()

def edit_report(report_id, new_date, new_location, new_content, new_remarks):
    """投稿を編集する"""
    try:
        conn = sqlite3.connect(DB_PATH)  # DB_PATHを使用
        c = conn.cursor()
        c.execute("""
            UPDATE reports
            SET 実行日 = ?, 場所 = ?, 実施内容 = ?, 所感 = ?
            WHERE id = ?
        """, (new_date, new_location, new_content, new_remarks, report_id))
        conn.commit()
        conn.close()
        print(f"✅ 投稿 (ID: {report_id}) を編集しました！")  # デバッグ用ログ
    except sqlite3.Error as e:
        print(f"❌ データベースエラー: {e}")  # エラーログ

def delete_report(report_id):
    """投稿を削除する（エラーハンドリング付き）"""
    try:
        with sqlite3.connect(DB_PATH) as conn:
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

# ✅ 週間予定関連の関数
def save_weekly_plan(投稿者, 週開始日, 週終了日, 予定):
    """週間予定をデータベースに保存"""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO weekly_plans (投稿者, 週開始日, 週終了日, 予定, 投稿日時)
        VALUES (?, ?, ?, ?, ?)
    """, (投稿者, 週開始日, 週終了日, 予定, (datetime.now() + timedelta(hours=9)).strftime("%Y-%m-%d %H:%M:%S")))

    conn.commit()
    conn.close()

def load_weekly_plans():
    """週間予定データを取得"""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("SELECT * FROM weekly_plans ORDER BY 投稿日時 DESC")
    rows = cur.fetchall()
    conn.close()

    weekly_plans = []
    for row in rows:
        weekly_plans.append({
            "id": row[0], "投稿者": row[1], "週開始日": row[2], "週終了日": row[3],
            "予定": row[4], "いいね": row[5], "ナイスファイト": row[6], "コメント": json.loads(row[7]),
            "投稿日時": row[8]
        })
    return weekly_plans

# ✅ 週報関連の関数
def save_weekly_report(投稿者, 週開始日, 週終了日, 週報内容):
    """週報をデータベースに保存"""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO weekly_reports (投稿者, 週開始日, 週終了日, 週報内容, 投稿日時)
        VALUES (?, ?, ?, ?, ?)
    """, (投稿者, 週開始日, 週終了日, 週報内容, (datetime.now() + timedelta(hours=9)).strftime("%Y-%m-%d %H:%M:%S")))

    conn.commit()
    conn.close()

def load_weekly_reports():
    """週報データを取得"""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("SELECT * FROM weekly_reports ORDER BY 投稿日時 DESC")
    rows = cur.fetchall()
    conn.close()

    weekly_reports = []
    for row in rows:
        weekly_reports.append({
            "id": row[0], "投稿者": row[1], "週開始日": row[2], "週終了日": row[3],
            "週報内容": row[4], "いいね": row[5], "ナイスファイト": row[6], "コメント": json.loads(row[7]),
            "投稿日時": row[8]
        })
    return weekly_reports
