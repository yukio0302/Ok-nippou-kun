import sqlite3
import json

DB_FILE = "reports.db"  # データベースファイル名

# ✅ 日報を取得（画像カラム削除）
def load_reports():
    """
    日報を取得する関数。
    """
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT id, 投稿者, 実行日, カテゴリ, 場所, 実施内容, 所感, いいね, ナイスファイト, コメント FROM reports ORDER BY 実行日 DESC")
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
                "コメント": json.loads(row[9]) if row[9] else []
            }
            for row in rows
        ]
    except sqlite3.Error as e:
        print(f"❌ 日報の取得中にエラーが発生しました: {e}")
        return []
    finally:
        conn.close()
