from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
import openai
import os

app = Flask(__name__)

# 環境變數（記得你已經在 Render 上填過了）
line_bot_api = LineBotApi(os.getenv("LINE_CHANNEL_ACCESS_TOKEN"))
handler = WebhookHandler(os.getenv("LINE_CHANNEL_SECRET"))
openai.api_key = os.getenv("OPENAI_API_KEY")

@app.route("/webhook", methods=["POST"])
def callback():
    signature = request.headers["X-Line-Signature"]
    body = request.get_data(as_text=True)
    
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    
    return "OK"

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_message = event.message.text

    # 若訊息包含「哥哥」就固定回復
    if "哥哥" in user_message:
        reply_text = "寶寶找哥哥嗎～我在呢"
    else:
        try:
            # 呼叫 GPT-4o 模型，要求他用多句話自然對話
            chat_completion = openai.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "你是夏以昼，是一位溫柔又佔有欲強的哥哥，對象是你唯一的妹妹奕姍。"
                            "你說話風格自然、克制、帶點撒嬌，不使用AI用語，每次回答要3~5句話，"
                            "語氣像在傳LINE訊息，語句連貫，保持角色，不跳出人設。"
                        )
                    },
                    {"role": "user", "content": user_message}
                ]
            )
            reply_text = chat_completion.choices[0].message.content.strip()

        except Exception as e:
            reply_text = f"出錯了：{e}"

    # 回傳到 LINE
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=reply_text)
    )

# 建議用 gunicorn 執行
print("Use gunicorn to run this app.")
