from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
import os
import json
import random
import openai
from long_term_memory import load_user_memory, save_user_memory

app = Flask(__name__)

# 環境變數
LINE_CHANNEL_ACCESS_TOKEN = os.environ.get('LINE_CHANNEL_ACCESS_TOKEN')
LINE_CHANNEL_SECRET = os.environ.get('LINE_CHANNEL_SECRET')
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')

line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)
client = openai.OpenAI(api_key=OPENAI_API_KEY)  # ✅ 新版 SDK 初始化

MEMORY_FILE = "memory.json"
MAX_MEMORY = 30

# Webhook 路由
@app.route("/webhook", methods=["POST"])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return "OK"

# 訊息處理
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_id = event.source.user_id
    user_input = event.message.text.strip()

    memory = load_user_memory(user_id, MEMORY_FILE)
    memory.append({"role": "user", "content": user_input})

    try:
        with open("persona.txt", "r", encoding="utf-8") as f:
            persona = f.read()

        messages = [{"role": "system", "content": persona}] + memory

        # ✅ 新版 GPT 呼叫
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            max_tokens=1000,
            temperature=0.8
        )

        reply_text = response.choices[0].message.content.strip()

        # 隨機回覆 3~5 句
        replies = [line.strip() for line in reply_text.split("\n") if line.strip()]
        random.shuffle(replies)
        replies = replies[:random.randint(3, 5)]
        reply_messages = [TextSendMessage(text=line) for line in replies]

        # 儲存回應
        memory.append({"role": "assistant", "content": reply_text})
        save_user_memory(user_id, memory, MEMORY_FILE, max_memory=MAX_MEMORY)

        # 回傳訊息
        line_bot_api.reply_message(event.reply_token, reply_messages)

    except Exception as e:
        import traceback
        traceback.print_exc()
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="哥哥出錯了嗚嗚…\n" + str(e))
        )

if __name__ == "__main__":
    app.run()
