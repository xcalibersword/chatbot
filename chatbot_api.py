from chatbot.py import Chatbot
import http.server
import socketserver

class ChatbotRequestHandler(http.server.BaseHTTPRequestHandler):
    def __init__(self):
        self.chatbot = Chatbot()
        self.chatbot.start()

    def handle(self):
        print("IM HANDLING IT")
        return
        

if __name__ == "__main__":
    bot = Chatbot()
    bot.start()
    while 1:
        incoming_msg = input()
        bot.recv_new_message("MyUserId",incoming_msg)


