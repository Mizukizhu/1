from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
import os
import openai

app = Flask(__name__)

# LINE 設定
line_bot_api = LineBotApi(os.getenv("LINE_CHANNEL_ACCESS_TOKEN"))
handler = WebhookHandler(os.getenv("LINE_CHANNEL_SECRET"))

# OpenAI 設定（支援新版 SDK）
openai.api_key = os.getenv("OPENAI_API_KEY")

@app.route("/webhook", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return "OK"

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_message = event.message.text

    # 特定指令回應
    if "哥哥" in user_message:
        reply_text = "寶寶找哥哥嗎～我在呢"
    else:
        # 呼叫 OpenAI ChatCompletion（新版 SDK）
        chat_completion = openai.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "你是夏以昼，是一位溫柔、會撒嬌但有點佔有慾的哥哥。"},
                {"role": "user", "content": user_message}
            ]
        )
        reply_text = chat_completion.choices[0].message.content.strip()

    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=reply_text)
    )

# Render 用 gunicorn 啟動
if __name__ == "__main__":
    print("Use gunicorn to run this app instead.")
