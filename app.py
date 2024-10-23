from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import \*
import os
import openai
import traceback

app = Flask(__name__)
static_tmp_path = os.path.join(os.path.dirname(__file__), 'static', 'tmp')

# 读取环境变量中的LINE Channel Access Token和Channel Secret
line_bot_api = LineBotApi(os.getenv('CHANNEL_ACCESS_TOKEN'))
handler = WebhookHandler(os.getenv('CHANNEL_SECRET'))
# 读取环境变量中的OpenAI API Key，并进行初始化
openai.api_key = os.getenv('OPENAI_API_KEY')

# 用于存储对话历史
conversation_history = []

def GPT_response(messages):
    try:
        # 调用OpenAI的ChatCompletion API，使用指定的模型ID
        response = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=messages,
            temperature=0.5,
            max_tokens=500
        )
        # 提取GPT的回复
        answer = response['choices'][0]['message']['content']
        return answer
    except Exception as e:
        print(f"Error communicating with OpenAI: {e}")
        return "抱歉，我無法處理你的請求。"

# 监听所有来自 /callback 的 POST 请求
@app.route("/callback", methods=['POST'])
def callback():
    # 获取X-Line-Signature头
    signature = request.headers['X-Line-Signature']
    # 获取请求体内容
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)
    
    # 处理webhook body
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'

# 处理讯息
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    global conversation_history  # 声明为全局变量
    msg = event.message.text

    # 将用户消息添加到对话历史
    conversation_history.append({"role": "user", "content": msg})
    
    try:
        GPT_answer = GPT_response(conversation_history)
        print(GPT_answer)

        # 将GPT的回复添加到对话历史
        conversation_history.append({"role": "assistant", "content": GPT_answer})
        
        # 使用LINE API回复用户消息
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=GPT_answer))
    except Exception as e:
        print(traceback.format_exc())
        line_bot_api.reply_message(
            event.reply_token, 
            TextSendMessage(text='你所使用的OPENAI API key額度可能已經超過，請於後台Log內確認錯誤訊息')
        )

# 处理Postback事件
@handler.add(PostbackEvent)
def handle_postback(event):
    print(event.postback.data)

# 新成员加入事件
@handler.add(MemberJoinedEvent)
def welcome(event):
    uid = event.joined.members[0].user_id
    gid = event.source.group_id
    profile = line_bot_api.get_group_member_profile(gid, uid)
    name = profile.display_name
    message = TextSendMessage(text=f'{name}歡迎加入')
    line_bot_api.reply_message(event.reply_token, message)

if __name__ == "__main__":
    # 运行 Flask 应用
    app.run(port=5000)
