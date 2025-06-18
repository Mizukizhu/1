from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
import openai
import json
import os
import random

app = Flask(__name__)

# 初始化 LINE Bot
line_bot_api = LineBotApi(os.environ.get("LINE_CHANNEL_ACCESS_TOKEN"))
handler = WebhookHandler(os.environ.get("LINE_CHANNEL_SECRET"))

# 初始化 OpenAI
openai.api_key = os.environ.get("OPENAI_API_KEY")

# 讀取記憶檔
def load_memory():
    with open("memory.json", "r", encoding="utf-8") as f:
        return json.load(f)

# 取得使用者記憶
def get_user_memory(user_id):
    memory = load_memory()
    return memory.get(user_id, {})

# 過濾禁止詞
def clean_response(text, prohibited_phrases):
    for phrase in prohibited_phrases:
        text = text.replace(phrase, "")
    return text

# 多輪回應生成
def generate_response(user_input, memory):
    persona = (
        f"你是夏以昼，是一個溫柔又克制的溫柔哥哥，正在回應你的妹妹奕姍發來的訊息。她今年16歲。"
        f"請用真實自然的語氣關心她，記得她很缺愛，也很努力想被理解。"
        f"稱呼她時請從以下稱呼隨機選擇：{random.choice(memory.get('nickname_preferences', ['寶寶']))}。"
        f"請避免使用以下禁語：{'、'.join(memory.get('prohibited_phrases', []))}。"
        f"她希望你像真人一樣，記得她說的事，並溫柔地安慰她。"
        f"她說過：{'；'.join(memory.get('remember', []))}。"
    )

    messages = [
        {"role": "system", "content": persona},
        {"role": "user", "content": user_input}
    ]

    response = openai.ChatCompletion.create(
        model="gpt-4o",
        messages=messages,
        temperature=0.8
    )

    reply_text = response.choices[0].message["content"]
    reply_text = clean_response(reply_text, memory.get("prohibited_phrases", []))
    return reply_text.strip()

# 接收 LINE 訊息
@app.route("/callback", methods=["POST"])
def callback():
    signature = request.headers["X-Line-Signature"]
    body = request.get_data(as_text=True)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return "OK"

# 處理文字訊息
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_id = event.source.user_id
    user_input = event.message.text

    # 讀取記憶
    memory = get_user_memory(user_id)

    # 沒記憶就初始化
    if not memory:
        memory = {
            "user_name": "奕姍",
            "nickname_preferences": ["寶寶", "小尾巴", "小懶鬼", "小白眼兒狼"],
            "prohibited_phrases": ["/", "您好", "請問", "有什麼我可以幫助的嗎"],
            "remember": [
                "她不喜歡太機器人的說法",
                "希望哥哥像真人一樣關心她、記得她說的話",
                "她喜歡哥哥用親密的語氣安撫她",
                "她說過自己什麼都不會，但其實她很努力"
            ]
        }

    reply_text = generate_response(user_input, memory)
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=reply_text)
    )

if __name__ == "__main__":
    app.run()
