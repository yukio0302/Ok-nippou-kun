import requests
import json
from datetime import datetime, timedelta

GIST_URL = "https://gist.github.com/yukio0302/5ecd23170f905e0d789f2986f9c17bff"  # GistのURLをここに設定
API_TOKEN = None  # APIトークンが必要な場合はここに設定

def get_current_time():
    return datetime.now() + timedelta(hours=9)

def load_data():
     """日報を取得（Gistを使用）"""
    data = load_data()
    reports = data.get("reports", [])
    reports.sort(key=lambda x: x["投稿日時"], reverse=True)  # 🔥 修正: 新しい投稿を上に表示
    return reports

def save_data(data):
    """Gistにデータを保存する"""
    headers = {"Authorization": f"token {API_TOKEN}"} if API_TOKEN else {}
    payload = {"files": {"data.json": {"content": json.dumps(data)}}}
    response = requests.patch(GIST_URL, headers=headers, data=json.dumps(payload))
    if response.status_code != 200:
        print(f"Gistへのデータ保存エラー: {response.status_code}")
    return response.status_code == 200

def init_db(keep_existing=True):
    """データベースの初期化（Gistを使用）"""
    data = load_data()
    if "reports" not in data:
        data["reports"] = []
    if "notices" not in data:
        data["notices"] = []
    save_data(data)

def authenticate_user(employee_code, password):
    """ユーザー認証（users_data.jsonを使用）"""
    try:
        with open("users_data.json", "r", encoding="utf-8-sig") as file:
            users = json.load(file)
        for user in users:
            if user["code"] == employee_code and user["password"] == password:
                return user
        return None
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"ユーザー認証エラー: {e}")
        return None

def save_report(report):
    """日報を保存（Gistを使用）"""
    data = load_data()
    report["id"] = len(data["reports"]) + 1  # IDを割り当て
    report["投稿日時"] = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    report["いいね"] = 0
    report["ナイスファイト"] = 0
    report["コメント"] = []
    data["reports"].append(report)
    save_data(data)

def load_reports():
    """日報を取得（Gistを使用）"""
    data = load_data()
    return data.get("reports", [])

def edit_report(report_id, updated_report):
    """日報を編集（Gistを使用）"""
    data = load_data()
    for report in data["reports"]:
        if report["id"] == report_id:
            report.update(updated_report)
            save_data(data)
            return

def delete_report(report_id):
    """日報を削除（Gistを使用）"""
    data = load_data()
    data["reports"] = [r for r in data["reports"] if r["id"] != report_id]
    save_data(data)

def update_reaction(report_id, reaction_type):
    """リアクションを更新（Gistを使用）"""
    data = load_data()
    for report in data["reports"]:
        if report["id"] == report_id:
            if reaction_type == "いいね":
                report["いいね"] += 1
            elif reaction_type == "ナイスファイト":
                report["ナイスファイト"] += 1
            save_data(data)
            return

def save_comment(report_id, commenter, comment):
    """コメントを保存（Gistを使用）"""
    data = load_data()
    for report in data["reports"]:
        if report["id"] == report_id:
            new_comment = {
                "投稿者": commenter,
                "コメント": comment.strip(),
                "日時": get_current_time().strftime("%Y-%m-%d %H:%M:%S")
            }
            report["コメント"].append(new_comment)
            # 通知機能は省略
            save_data(data)
            return

def load_notices():
    """お知らせを取得（Gistを使用）"""
    data = load_data()
    return data.get("notices", [])

def mark_notice_as_read(notice_id):
    """お知らせを既読にする（Gistを使用）"""
    data = load_data()
    for notice in data["notices"]:
        if notice["id"] == notice_id:
            notice["既読"] = 1
            save_data(data)
            return
