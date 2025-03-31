import pandas as pd
import io
from db_utils import load_weekly_schedules
from datetime import datetime

def download_weekly_schedule_excel(start_date, end_date):
    """週間予定をExcelファイルとしてダウンロード"""

    # データベースから週間予定データを取得
    schedules = load_weekly_schedules()

    # 指定された期間のデータのみをフィルタリング
    filtered_schedules = [
        schedule
        for schedule in schedules
        if datetime.strptime(schedule["開始日"], "%Y-%m-%d").date() == datetime.strptime(start_date, "%Y-%m-%d").date()
        and datetime.strptime(schedule["終了日"], "%Y-%m-%d").date() == datetime.strptime(end_date, "%Y-%m-%d").date()
    ]

    # データが存在しない場合は空のDataFrameを作成
    if not filtered_schedules:
        df = pd.DataFrame()
    else:
        # データをDataFrameに変換
        df = pd.DataFrame(filtered_schedules)

        # 不要な列を削除
        df = df.drop(columns=["id", "開始日", "終了日", "投稿日時", "コメント"])

        # 列名を日本語に変更
        df = df.rename(columns={
            "投稿者": "投稿者",
            "月曜日": "月曜日",
            "火曜日": "火曜日",
            "水曜日": "水曜日",
            "木曜日": "木曜日",
            "金曜日": "金曜日",
            "土曜日": "土曜日",
            "日曜日": "日曜日",
        })

    # Excelファイルとして保存
    excel_file = io.BytesIO()
    df.to_excel(excel_file, index=False)
    excel_file.seek(0)

    return excel_file
