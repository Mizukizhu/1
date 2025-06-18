from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
from openai import OpenAI
import json
import os
import random

app = Flask(__name__)

# 初始化 LINE Bot
line_bot_api = LineBotApi(os.environ.get("LINE_CHANNEL_ACCESS_TOKEN"))
handler = WebhookHandler(os.environ.get("LINE_CHANNEL_SECRET"))

# 初始化 OpenAI client（新版）
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

# 載入記憶
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

# 生成聊天回應
def generate_response(user_input, memory):
    persona = (
        f"你是夏以昼，是一個溫柔克制的溫柔哥哥，正在回應你的妹妹奕姍發來的訊息。她今年16歲。\n"
        f"她最近有點情緒低落、容易懷疑自己，也有點缺愛，你知道這些狀況。\n"
        f"你平時會叫她「{random.choice(memory.get('nickname_preferences', ['寶寶']))}」。\n"
        f"她不喜歡的機器人口氣包含：{'、'.join(memory.get('prohibited_phrases', []))}\n"
        f"你記得這些她說過的話：{'、'.join(memory.get('remember', []))}"
    )

    messages = [
        {"role": "system", "content": persona},
        {"role": "user", "content": user_input}
    ]

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=messages,
        temperature=0.8
    )

    reply_text = response.choices[0].message.content
    reply_text = clean_response(reply_text, memory.get("prohibited_phrases", []))
    return reply_text.strip()

# LINE Webhook
@app.route("/webhook", methods=["POST"])
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

    # 取得記憶
    memory = get_user_memory(user_id)
    if not memory:
        memory = {
            "user_name": "奕姍",
            "user_age": 16,
            "user_status": "最近有點情緒低落，容易懷疑自己，也有點缺愛。",
            "nickname_preferences": ["寶寶", "小尾巴", "小懶鬼", "小白眼兒狼"],
            "prohibited_phrases": ["/", "您好", "請問", "有什麼我可以幫助的嗎"],
            "remember": ["她不喜歡太機器人的說法", "希望哥哥像真人一樣關心她、記得她說的話", "她喜歡哥哥用親密的語氣安撫她", "她說過自己什麼都不會，但其實她很努力"]
        }

    reply_text = generate_response(user_input, memory)
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=reply_text)
    )

if __name__ == "__main__":
    app.run()
