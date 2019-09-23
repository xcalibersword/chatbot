import sys
import socketio
from aiohttp import web
from chatbot import Chatbot

# This file opens a server that is a front for the chatbot. 
# Right now it defaults to localhost:8080 due to aiohttp

sio = socketio.AsyncServer()
app = web.Application() # This is implicitly an aiohttp apparently
sio.attach(app)

def init_chatbot():
    bot = Chatbot()
    bot.start()
    return bot

def robotify(msg):
    return "<机器人>:" + str(msg)

def get_bot_reply(bot, cid, message):
    replytext = bot.get_bot_reply(cid,message)
    reply = robotify(replytext)
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
    sio.enter_room(sid, sid) # Take a client and put them into a room that is their socket ID
    print("A connection!")
    print("Contacted by someone at", sid)
    greet = robotify("Greetings!")
    await sio.emit('message', greet, room=sid)

@sio.event
async def disconnect(sid):
    print('disconnect', sid)

@sio.on('chat')
async def chat_message(sid, msg):
    await sio.emit('message',display_own_message(msg),room=sid)
    print("Recieved from",sid,"Content:",msg)
    reply = get_bot_reply(bot, sid, msg)
    await sio.emit('message', reply, room=sid)

app.router.add_get('/', index)

if __name__ == '__main__':
    web.run_app(app)