from flask import Flask, request, abort

from linebot import (
    LineBotApi, WebhookHandler
)
from linebot.exceptions import (
    InvalidSignatureError
)
from linebot.models import \*

#======python的函數庫==========
import os
import openai
import traceback
#======python的函數庫==========

app = Flask(__name__)

# Channel Access Token，从环境变量中读取
line_bot_api = LineBotApi(os.getenv('CHANNEL_ACCESS_TOKEN'))
# Channel Secret，从环境变量中读取
handler = WebhookHandler(os.getenv('CHANNEL_SECRET'))
# OPENAI API Key初始化設定
openai.api_key = os.getenv('OPENAI_API_KEY')

# 用户对话历史记录变量
conversation_history = []

def get_GPT_response(messages):
    try:
        # 调用OpenAI的ChatCompletion API
        response = openai.ChatCompletion.create(
            # 使用在OpenAI上新增的assistant模型ID
            model="asst_tHl6O766wFQ7oQN1TaIjKg2A",
            messages=messages,
            temperature=0.5,
            max_tokens=500
        )

        # 提取 GPT 的回复
        answer = response['choices'][0]['message']['content']
        return answer
    except Exception as e:
        print(f"Error communicating with OpenAI: {e}")
        return "抱歉，我無法處理你的請求。"

# 監聽所有來自 /callback 的 Post Request
@app.route("/callback", methods=['POST'])
def callback():
    # 获取X-Line-Signature头签名
    signature = request.headers['X-Line-Signature']
    # 获取请求body
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)
    # 处理webhook body
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'

# 處理訊息
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    global conversation_history  # 声明为全局变量
    msg = event.message.text

    # 将用户消息添加到对话历史记录
    conversation_history.append({"role": "user", "content": msg})
    
    try:
        # 获取GPT的回复
        GPT_answer = get_GPT_response(conversation_history)
        print(GPT_answer)

        # 将GPT的回复添加到对话历史记录
        conversation_history.append({"role": "assistant", "content": GPT_answer})

        # 使用LINE Messaging API回复用户
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=GPT_answer))
    except Exception as e:
        print(traceback.format_exc())
        line_bot_api.reply_message(
            event.reply_token, 
            TextSendMessage(text='发生错误，请稍后再试。')
        )

@handler.add(PostbackEvent)
def handle_postback(event):
    print(event.postback.data)

@handler.add(MemberJoinedEvent)
def welcome(event):
    uid = event.joined.members[0].user_id
    gid = event.source.group_id
    profile = line_bot_api.get_group_member_profile(gid, uid)
    name = profile.display_name
    message = TextSendMessage(text=f'{name}歡迎加入')
    line_bot_api.reply_message(event.reply_token, message)

if __name__ == "__main__":
    app.run(port=5000)
