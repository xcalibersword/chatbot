import sys
import socketio
import requests
# import subprocess as sp
from aiohttp import web
from chatbot import Chatbot

chatbot_api_PORT = 8881
chatbot_api_url = "localhost:"+str(chatbot_api_PORT)
static_files = {"/":{"filename":"index.html"}}

sio = socketio.AsyncServer()
# app = socketio.ASGIApp(sio, static_files=static_files)
app = web.Application() # This is implicitly an aiohttp apparently
sio.attach(app)

def init_chatbot():
    bot = Chatbot()
    bot.start()
    return bot

def get_bot_reply(bot, cid, message):
    replytext = bot.get_bot_reply(cid,message)
    reply = "<机器人>:" + replytext
    return reply

def display_own_message(msg):
    return "<您>:"+msg

bot = init_chatbot()

def index(request):
    indexfilepath = 'testing_server/index.html'
    with open(indexfilepath) as f:
        return web.Response(text = f.read(), content_type = 'text/html')

@sio.event
async def connect(sid, environ):
    print("A connection!")
    print("Contacted by someone at", sid)
    await sio.emit('message', "Greetings!")

@sio.event
async def disconnect(sid):
    print('disconnect', sid)

@sio.on('chat')
async def chat_message(sid, msg):
    await sio.emit('message',display_own_message(msg))
    print("Messaged recieved from",sid)
    reply = get_bot_reply(bot, sid, msg)
    await sio.emit('message', reply)

app.router.add_get('/', index)

if __name__ == '__main__':
    web.run_app(app)