def download_weekly_schedule_excel(start_date, end_date):
    """
    週間予定をExcelファイルとしてダウンロードする
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=DictCursor)
        
        cur.execute("""
            SELECT 投稿者, 開始日, 終了日, 月曜日, 火曜日, 水曜日, 木曜日, 金曜日, 土曜日, 日曜日, 投稿日時
            FROM weekly_schedules
            WHERE 開始日 = %s AND 終了日 = %s
        """, (start_date, end_date))
        rows = cur.fetchall()
        
        if not rows:
            return None
        
        wb = openpyxl.Workbook()
        ws = wb.active
        
        headers = ["投稿者", "開始日", "終了日", "月曜日", "火曜日", "水曜日", "木曜日", "金曜日", "土曜日", "日曜日", "投稿日時"]
        for col_num, header in enumerate(headers, 1):
            ws.cell(row=1, column=col_num, value=header)
        
        for row_num, row in enumerate(rows, 2):
            for col_num, value in enumerate(row, 1):
                ws.cell(row=row_num, column=col_num, value=value)
        
        excel_file = BytesIO()
        wb.save(excel_file)
        excel_file.seek(0)
        
        return excel_file
        
    except Exception as e:
        print(f"エラーが発生しました: {e}")
        return None
        
    finally:
        if conn:
            cur.close()
            conn.close()
