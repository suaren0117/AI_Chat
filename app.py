from flask import Flask, render_template, request, make_response
from openai import OpenAI
import os
from dotenv import load_dotenv
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials
from gspread.exceptions import WorksheetNotFound

# --- 環境変数読み込み ---
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# SPREADSHEET_ID = os.getenv("GOOGLE_SHEET_ID")
# CREDENTIALS_JSON = os.getenv("SERVICE_ACCOUNT_JSON")

# --- Google認証（今回はコメントアウトしておく） ---
# SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
# credentials = Credentials.from_service_account_file(CREDENTIALS_JSON, scopes=SCOPES)
# gc = gspread.authorize(credentials)

# try:
#     sh = gc.open_by_key(SPREADSHEET_ID)
# except Exception as e:
#     print("❌ スプレッドシートにアクセスできません。IDまたは共有設定を確認してください。")
#     print(e)
#     exit()

app = Flask(__name__, template_folder="templates")

# --- 履歴管理（CSV部分はコメントアウト） ---
def load_history(limit=20):
    # 今回は履歴を保存しないので空リストを返す
    return []

def save_history(user_input, ai_response):
    # 保存処理を無効化
    pass

def write_comments_to_sheet(job_title, location, user_input, ai_response):
    # Googleスプレッドシート保存も無効化
    pass

# --- 求人提案（ダミー化） ---
def suggest_jobs(job_title, location, employment_type, top_n=5):
    return "（デモ用のダミー求人データです）"

# --- AI応答 ---
def generate_response(user_input, job_title=None, location=None, employment_type=None):
    messages = [{"role": "user", "content": user_input}]
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages
    )
    ai_text = response.choices[0].message.content
    return ai_text

# --- ルーティング ---
@app.route("/", methods=["GET", "POST"])
def index():
    chat_history = load_history()

    # 初回表示では条件入力フォームを表示するけど、今回は使わなくてもOK
    show_conditions = True

    if request.method == "POST":
        user_input = request.form.get("user_input")

        if user_input:
            ai_response = generate_response(user_input)
            save_history(user_input, ai_response)
            # write_comments_to_sheet(job_title, location, user_input, ai_response)

            show_conditions = False

            # レンダリング
            response = make_response(render_template("index.html", chat_history=[{"user": user_input, "ai": ai_response}], show_conditions=show_conditions))
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
            return response

    return render_template("index.html", chat_history=chat_history, show_conditions=show_conditions)

if __name__ == "__main__":
    app.run(debug=True)
