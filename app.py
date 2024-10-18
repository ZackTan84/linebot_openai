from flask import Flask, request, abort

from linebot import (
    LineBotApi, WebhookHandler
)
from linebot.exceptions import (
    InvalidSignatureError
)
from linebot.models import *

#======python的函數庫==========
import tempfile, os
import datetime
import openai
import time
import traceback
#======python的函數庫==========

app = Flask(__name__)
static_tmp_path = os.path.join(os.path.dirname(__file__), 'static', 'tmp')

# Channel Access Token
line_bot_api = LineBotApi(os.getenv('CHANNEL_ACCESS_TOKEN'))
# Channel Secret
handler = WebhookHandler(os.getenv('CHANNEL_SECRET'))
# OPENAI API Key初始化設定
openai.api_key = os.getenv('OPENAI_API_KEY')

# 用于存储对话历史
conversation_history = []

def GPT_response(messages):
    # 接收回應
    response = openai.ChatCompletion.create(
        model="gpt-4o-mini-2024-07-18",
        messages=messages,
        temperature=0.5,
        max_tokens=500
    )

    # 提取 GPT 的回复
    answer = response['choices'][0]['message']['content']
    return answer
    
# DALL·E 3 图像生成
def DALL_E_image(prompt):
    response = openai.Image.create(
        model="dall-e-3",
        prompt=prompt,
        size="512x512"
    )
    image_url = response['data'][0]['url']
    return image_url

# Whisper 音频转文字
def Whisper_transcribe(audio_path):
    with open(audio_path, "rb") as audio_file:
        response = openai.Audio.transcribe(
            model="whisper-1",
            file=audio_file
        )
    transcript = response['text']
    return transcript

# 監聽所有來自 /callback 的 Post Request
@app.route("/callback", methods=['POST'])
def callback():
    # get X-Line-Signature header value
    signature = request.headers['X-Line-Signature']
    # get request body as text
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)
    # handle webhook body
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

    # 将用户消息添加到对话历史
    conversation_history.append({"role": "user", "content": msg})
    
    try:
        GPT_answer = GPT_response(conversation_history)
        print(GPT_answer)

        # 将 GPT 的回复添加到对话历史
        conversation_history.append({"role": "assistant", "content": GPT_answer})
        
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=GPT_answer))
    except:
        print(traceback.format_exc())
        line_bot_api.reply_message(
            event.reply_token, 
            TextSendMessage('你所使用的OPENAI API key額度可能已經超過，請於後台Log內確認錯誤訊息')
        )

@handler.add(PostbackEvent)
def handle_message(event):
    print(event.postback.data)

@handler.add(MemberJoinedEvent)
def welcome(event):
    uid = event.joined.members[0].user_id
    gid = event.source.group_id
    profile = line_bot_api.get_group_member_profile(gid, uid)
    name = profile.display_name
    message = TextSendMessage(text=f'{name}歡迎加入')
    line_bot_api.reply_message(event.reply_token, message)
