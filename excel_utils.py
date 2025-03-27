import openpyxl
from io import BytesIO
from datetime import datetime, timedelta
import db_utils
import sqlite3

# ✅ データベースのパス
DB_PATH = "/mount/src/ok-nippou-kun/data/reports.db"

def download_weekly_schedule_excel(start_date, end_date):
    """
    週間予定をExcelファイルとしてダウンロードする
    """
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # 週間予定データを取得
    cur.execute("""
        SELECT users.名前, weekly_schedules.*
        FROM weekly_schedules
        JOIN posts ON weekly_schedules.postId = posts.id
        JOIN users ON posts.投稿者ID = users.id
        WHERE weekly_schedules.開始日 = ? AND weekly_schedules.終了日 = ?
    """, (start_date, end_date))
    rows = cur.fetchall()
    conn.close()

    if not rows:
        return None  # データがない場合は None を返す

    wb = openpyxl.Workbook()
    ws = wb.active

    # ヘッダー行
    headers = ["投稿者", "開始日", "終了日", "月曜日", "火曜日", "水曜日", "木曜日", "金曜日", "土曜日", "日曜日", "投稿日時"]
    for col_num, header in enumerate(headers, 1):
        ws.cell(row=1, column=col_num, value=header)

    # データ行
    for row_num, row in enumerate(rows, 2):
        for col_num, value in enumerate(row, 1):
            ws.cell(row=row_num, column=col_num, value=value)

    # ファイルをバイト列として保存
    excel_file = BytesIO()
    wb.save(excel_file)
    excel_file.seek(0)

    return excel_file
