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
    except Exception as e:
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

        return [
            (
                row[0], row[1], row[2], row[3], row[4],
                row[5], row[6], row[7], row[8], json.loads(row[9]) if row[9] else [],
                row[10]  # 画像データ
            )
            for row in rows
        ]
    except Exception as e:
        print(f"❌ レポートの取得中にエラーが発生しました: {e}")
        return []
    finally:
        conn.close()
