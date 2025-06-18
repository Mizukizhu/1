from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
import openai
import os
import json
import random
from long_term_memory import load_user_memory, save_user_memory

app = Flask(__name__)

# 環境變數
LINE_CHANNEL_ACCESS_TOKEN = os.environ.get('LINE_CHANNEL_ACCESS_TOKEN')
LINE_CHANNEL_SECRET = os.environ.get('LINE_CHANNEL_SECRET')
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')

# 初始化
line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)
openai.api_key = OPENAI_API_KEY

# 記憶參數
MEMORY_FILE = 'user_memory.json'
MAX_MEMORY = 30  # 可修改記憶條數限制

@app.route("/webhook", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return 'OK'

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_id = event.source.user_id
    user_input = event.message.text.strip()

    # 載入對話記憶
    memory = load_user_memory(user_id, MEMORY_FILE)

    # 新訊息加入記憶（對話格式為角色扮演）
    memory.append({"role": "user", "content": user_input})

    # 組合人設與記憶
    with open("persona.txt", "r", encoding="utf-8") as f:
        persona = f.read()

    messages = [{"role": "system", "content": persona}] + memory

    # 呼叫 GPT 模型
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4o",  # 可改為你指定的模型
            messages=messages,
            max_tokens=1000,
            temperature=0.8,
        )
        reply_text = response.choices[0].message.content.strip()

        # 自動斷句成 3～5 句訊息
        replies = reply_text.split("\n")
        replies = [line.strip() for line in replies if line.strip()]
        random.shuffle(replies)
        replies = replies[:random.randint(3, 5)]
        reply_messages = [TextSendMessage(text=line) for line in replies]

        # 儲存記憶
        memory.append({"role": "assistant", "content": reply_text})
        save_user_memory(user_id, memory, MEMORY_FILE, max_memory=MAX_MEMORY)

        # 回傳訊息
        line_bot_api.reply_message(event.reply_token, reply_messages)

    except Exception as e:
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="哥哥這邊壞掉了，等等再來找我好不好～"))

if __name__ == "__main__":
    app.run()
