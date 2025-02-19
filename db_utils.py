import sqlite3
import json

DB_FILE = "reports.db"  # データベースファイル名

# ✅ データベース初期化
def init_db(keep_existing=True):
    """
    データベースを初期化する関数。
    keep_existing: True の場合、既存のデータを保持する。
    """
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    # reports テーブルが存在しない場合のみ作成
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            投稿者 TEXT NOT NULL,
            実行日 TEXT NOT NULL,
            カテゴリ TEXT,
            場所 TEXT,
            実施内容 TEXT,
            所感 TEXT,
            いいね INTEGER DEFAULT 0,
            ナイスファイト INTEGER DEFAULT 0,
            コメント TEXT DEFAULT '[]',  -- JSON文字列として初期化
            画像 BLOB
        )
    """)

    # notices テーブルが存在しない場合のみ作成
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS notices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            内容 TEXT NOT NULL,
            タイトル TEXT,
            日付 TEXT,
            既読 INTEGER DEFAULT 0
        )
    """)

    conn.commit()
    conn.close()
    print(f"✅ データベースの初期化が完了しました（既存データ保持: {keep_existing}）")

# ✅ ユーザー認証
def authenticate_user(employee_code, password):
    """
    ユーザーを認証する関数。
    """
    try:
        with open("users_data.json", "r", encoding="utf-8-sig") as file:
            users = json.load(file)
        
        for user in users:
            if user["code"] == employee_code and user["password"] == password:
                return user  # ログイン成功
        return None  # ログイン失敗
    except FileNotFoundError:
        print("❌ ユーザーデータファイルが見つかりません。")
        return None
    except json.JSONDecodeError as e:
        print(f"❌ ユーザーデータのJSON解析エラー: {e}")
        return None
    except Exception as e:
        print(f"❌ ユーザー認証エラー: {e}")
        return None

# ✅ 日報を保存
def save_report(report):
    """
    日報を保存する関数。
    """
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO reports (投稿者, 実行日, カテゴリ, 場所, 実施内容, 所感, コメント, 画像)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            report["投稿者"],
            report["実行日"],
            report["カテゴリ"],
            report["場所"],
            report["実施内容"],
            report["所感"],
            json.dumps(report.get("コメント", [])),  # コメントをJSON形式で保存
            report.get("画像")
        ))
        conn.commit()
        print("✅ 日報が正常に保存されました。")
    except sqlite3.Error as e:
        print(f"❌ 日報の保存中にエラーが発生しました: {e}")
    finally:
        conn.close()

# ✅ 日報を取得
def load_reports():
    """
    日報を取得する関数。
    """
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM reports ORDER BY 実行日 DESC")
        rows = cursor.fetchall()

        # デバッグ用：取得したデータを表示
        print("✅ 取得した日報データ:", rows)

        return [
            {
                "id": row[0],
                "投稿者": row[1],
                "実行日": row[2],
                "カテゴリ": row[3],
                "場所": row[4],
                "実施内容": row[5],
                "所感": row[6],
                "いいね": row[7],
                "ナイスファイト": row[8],
                "コメント": json.loads(row[9]) if row[9] else [],
                "画像": row[10]
            }
            for row in rows
        ]
    except sqlite3.Error as e:
        print(f"❌ 日報の取得中にエラーが発生しました: {e}")
        return []
    finally:
        conn.close()

# ✅ お知らせを取得
def load_notices():
    """
    お知らせを取得する関数。
    """
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM notices ORDER BY 日付 DESC")
        rows = cursor.fetchall()

        return [
            {
                "id": row[0],
                "内容": row[1],
                "タイトル": row[2],
                "日付": row[3],
                "既読": row[4]
            }
            for row in rows
        ]
    except sqlite3.Error as e:
        print(f"❌ お知らせ取得中にエラーが発生しました: {e}")
        return []
    finally:
        conn.close()

# ✅ お知らせを既読にする
def mark_notice_as_read(notice_id):
    """
    お知らせを既読にする関数。
    """
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE notices SET 既読 = 1 WHERE id = ?", (notice_id,))
        conn.commit()
        print(f"✅ お知らせ (ID: {notice_id}) を既読にしました。")
    except sqlite3.Error as e:
        print(f"❌ お知らせ既読処理中にエラーが発生しました: {e}")
    finally:
        conn.close()

# ✅ 投稿を編集
def edit_report(report):
    """
    投稿を編集する関数。
    """
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    try:
        cursor.execute("""
            UPDATE reports
            SET カテゴリ = ?, 場所 = ?, 実施内容 = ?, 所感 = ?, 画像 = ?
            WHERE id = ?
        """, (
            report["カテゴリ"],
            report["場所"],
            report["実施内容"],
            report["所感"],
            report["画像"],
            report["id"]
        ))
        conn.commit()
        print(f"✅ 日報 (ID: {report['id']}) を編集しました。")
    except sqlite3.Error as e:
        print(f"❌ 日報編集中にエラーが発生しました: {e}")
    finally:
        conn.close()

# ✅ 投稿を削除
def delete_report(report_id):
    """
    投稿を削除する関数。
    """
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM reports WHERE id = ?", (report_id,))
        conn.commit()
        print(f"✅ 日報 (ID: {report_id}) を削除しました。")
    except sqlite3.Error as e:
        print(f"❌ 日報削除中にエラーが発生しました: {e}")
    finally:
        conn.close()
