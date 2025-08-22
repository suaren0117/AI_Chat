from flask import Flask, render_template, request, redirect, make_response
import pandas as pd
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

HISTORY_FILE = "career_chat_history.csv"
JOBS_FILE = "dummy_jobs.csv"

SPREADSHEET_ID = os.getenv("GOOGLE_SHEET_ID")
CREDENTIALS_JSON = os.getenv("SERVICE_ACCOUNT_JSON")

# --- Google認証 ---
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
credentials = Credentials.from_service_account_file(CREDENTIALS_JSON, scopes=SCOPES)
gc = gspread.authorize(credentials)

try:
    sh = gc.open_by_key(SPREADSHEET_ID)
except Exception as e:
    print("❌ スプレッドシートにアクセスできません。IDまたは共有設定を確認してください。")
    print(e)
    exit()

app = Flask(__name__, template_folder="templates")

# --- 履歴 ---
def load_history(limit=20):
    if not os.path.exists(HISTORY_FILE):
        return []
    df = pd.read_csv(HISTORY_FILE)
    history = []
    for _, row in df.tail(limit).iterrows():
        history.append({"user": row["ユーザー入力"], "ai": row["AI回答"]})
    return history

def save_history(user_input, ai_response):
    new_row = pd.DataFrame([{
        "ユーザー入力": user_input,
        "AI回答": ai_response
    }])
    if os.path.exists(HISTORY_FILE):
        new_row.to_csv(HISTORY_FILE, mode="a", header=False, index=False, encoding="utf-8-sig")
    else:
        new_row.to_csv(HISTORY_FILE, mode="w", header=True, index=False, encoding="utf-8-sig")

def write_comments_to_sheet(job_title, location, user_input, ai_response):
    today = datetime.now().strftime("%Y%m%d")
    sheet_name = f"{today}_{job_title}_{location}"
    try:
        ws = sh.worksheet(sheet_name)
    except WorksheetNotFound:
        ws = sh.add_worksheet(title=sheet_name, rows="1000", cols="5")
        ws.append_row(["ユーザー入力", "AI回答"])
    ws.append_row([user_input, ai_response])

# --- 求人提案 ---
def suggest_jobs(job_title, location, employment_type, top_n=5):
    jobs_df = pd.read_csv(JOBS_FILE)
    if "employment_type" not in jobs_df.columns:
        jobs_df["employment_type"] = "正社員"
    matches = jobs_df[
        jobs_df["title"].str.contains(job_title, na=False) &
        jobs_df["location"].str.contains(location, na=False) &
        jobs_df["employment_type"].str.contains(employment_type, na=False)
    ]
    if matches.empty:
        return "条件に合う求人は見つかりませんでした。"
    top_matches = matches.head(top_n)
    suggestions = ""
    for _, row in top_matches.iterrows():
        suggestions += f"{row['title']} / {row['company']} / {row['location']} / {row['salary']}万円 / {row['employment_type']}\n"
    return suggestions

# --- AI応答 ---
def generate_response(user_input, job_title=None, location=None, employment_type=None):
    messages = [{"role": "user", "content": user_input}]
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages
    )
    ai_text = response.choices[0].message.content
    if job_title and location and employment_type:
        job_suggestions = suggest_jobs(job_title, location, employment_type)
        ai_text += "\n\n【おすすめ求人】\n" + job_suggestions
    return ai_text

# --- ルーティング ---
@app.route("/", methods=["GET", "POST"])
def index():
    chat_history = load_history()

    # 初回表示では条件入力フォームを必ず表示
    show_conditions = True

    if request.method == "POST":
        user_input = request.form.get("user_input")
        # 条件入力フォームから値を取得（初回のみ）
        job_title = request.form.get("job_title")
        location = request.form.get("location")
        employment_type = request.form.get("employment_type")

        if user_input:
            ai_response = generate_response(user_input, job_title, location, employment_type)
            save_history(user_input, ai_response)
            write_comments_to_sheet(job_title, location, user_input, ai_response)

            # 条件入力はPOST後は不要にする
            show_conditions = False

            # リダイレクトしてブラウザキャッシュを防ぐ
            response = make_response(render_template("index.html", chat_history=load_history(), show_conditions=show_conditions))
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
            return response

    # GET時も毎回CSVから読み込む
    return render_template("index.html", chat_history=chat_history, show_conditions=show_conditions)

if __name__ == "__main__":
    app.run(debug=True)
