import openpyxl
from io import BytesIO
from datetime import datetime, timedelta
import db_utils

# ✅ データベースのパス
DB_PATH = "/mount/src/ok-nippou-kun/data/reports.db"

def download_weekly_schedule_excel(start_date, end_date):
    """
    週間予定をExcelファイルとしてダウンロードする
    """
    user_schedules = db_utils.get_weekly_schedule_for_all_users(start_date, end_date)

    wb = openpyxl.Workbook()
    for user_id, schedules in user_schedules.items():
        ws = wb.create_sheet(title=f"ユーザー{user_id}")

        # ヘッダー行
        headers = ["曜日", "予定"] * 7
        for col_num, header in enumerate(headers, 2):
            ws.cell(row=2, column=col_num, value=header)

        # 日付行
        current_date = datetime.strptime(start_date, "%Y-%m-%d")
        for i in range(7):
            ws.cell(row=3, column=i * 2 + 2, value=current_date.strftime("%m月%d日(%a)"))
            current_date += timedelta(days=1)

        # 予定行
        for schedule in schedules:
            schedule_date = datetime.strptime(schedule["date"], "%Y-%m-%d")
            day_index = (schedule_date - datetime.strptime(start_date, "%Y-%m-%d")).days
            ws.cell(row=4, column=day_index * 2 + 2, value=schedule["content"])

        # コメント行
        ws.cell(row=15, column=2, value="コメント")
        for schedule in schedules:
            schedule_date = datetime.strptime(schedule["date"], "%Y-%m-%d")
            day_index = (schedule_date - datetime.strptime(start_date, "%Y-%m-%d")).days
            ws.cell(row=16, column=day_index * 2 + 2, value=schedule["comment"])

    # ファイルをバイト列として保存
    excel_file = BytesIO()
    wb.save(excel_file)
    excel_file.seek(0)

    return excel_file
