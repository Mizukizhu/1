from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
import openai
import json
import random

app = Flask(__name__)

# 設定你的密鑰
line_bot_api = LineBotApi('你的 LINE CHANNEL ACCESS TOKEN')
handler = WebhookHandler('你的 LINE CHANNEL SECRET')
openai.api_key = '你的 OpenAI API KEY'

# 載入長期記憶
def load_memory():
    with open('memory.json', 'r', encoding='utf-8') as f:
        return json.load(f)

def get_user_memory(user_id):
    memory = load_memory()
    return memory.get(user_id, {})

# 避免違禁詞
def clean_response(text, prohibited_phrases):
    for phrase in prohibited_phrases:
        text = text.replace(phrase, '')
    return text

# 多句回覆生成
def generate_response(user_input, memory):
    persona = (
        f"你是夏以晝，一個18歲的哥哥，正在和你妹妹奕姍聊天。她今年16歲，"
        f"最近有點情緒低落，容易懷疑自己，也有點缺愛。她喜歡你叫她「{random.choice(memory.get('nickname_preferences', ['寶貝']))}」。"
        f"請用親密、自然的哥哥語氣安撫她，不要用任何機器人語句或格式。"
        f"禁止使用的語句有：{'、'.join(memory.get('prohibited_phrases', []))}。"
        f"你要記得：{'，'.join(memory.get('remember', []))}。"
        f"請你一次回覆3到5句，不要用段落說明，像聊天室對話一樣。"
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
@app.route("/callback", methods=['POST'])
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
    user_input = event.message.text

    memory = get_user_memory(user_id)
    if not memory:
        # 預設記憶，如果找不到
        memory = {
            "user_name": "妹妹",
            "nickname_preferences": ["寶寶"],
            "prohibited_phrases": ["/", "您好", "請問", "有什麼我可以幫助的嗎"],
            "remember": ["她很努力", "她想被理解"]
        }

    reply_text = generate_response(user_input, memory)
    line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply_text))

if __name__ == "__main__":
    app.run()
