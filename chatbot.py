import re
import cbsv
import threading
from initalizers import master_initalize
from chatbot_supp import *
from chatclass import *
from chatbot_be import DatabaseRunner

DEBUG = 0

# The main file that ties everything together.
# This is more or less the API center with the all important method: "get_bot_reply"
# To initalize the bot:
    # bot = Chatbot()
    # bot.start()

# Calls all the supporting functions from chatclass and chatbot_supp and initalizers
# Required libraries: 
# - mypysql used in cb_sql

# Server libraries:
# - python-socketio
# - aiohttp

# EXTENSIONS:
# Looking at a deeper history rather than just the previous state. LOC: decide_action

# This text replacer should be put in a class or smth
SUB_LIST = [
    ("'s"," is"),
]

REMOVE_LIST = [
    ".",
    ",",
    "!",
    "，",
    "。",
    "！",
]

# Removes punctuation characters and converts to lowercase if english
def format_text(text):
    text = text.lower()
    for character in REMOVE_LIST:
        text = text.replace(character,"")
    for pair in SUB_LIST:
        text = text.replace(pair[0],pair[1])
    return text


# Big Chatbot class
class Chatbot():
    timeout = 15
    def __init__(self):
        self.PREV_REPLY_FLAG = "prev_state_message"
        self.chat_dict = {}
        self.triggered = False
    
    def _fetch_user_DB_info(self, user):
        return self.dbr.fetch_user_info(user)

    def make_new_chatmgr(self, chat):
        makeCM = lambda c: ChatManager(c, self.ip, self.pk, self.rg, self.dm, self.gk)
        return makeCM(chat)

    def start(self):
        comps = master_initalize()
        self.dm = comps['dmanager']
        self.ip = comps['iparser']
        self.pk = comps['pkeeper']
        self.rg = comps['replygen']
        self.gk = comps['gkeeper']
        self.dbr = DatabaseRunner()
        self.dm.set_runner(self.dbr)
        print("SHEBAO chatbot started!")
        return

    def trigger_backup(self):
        if not self.triggered:
            self.triggered = True
            self.set_backup_alarm()

    def set_backup_alarm(self):
        if not self.triggered:
            # No need for backup when no new messages
            return
        if DEBUG: print("Scheduled an event in",self.timeout,"s")
        timer = threading.Timer(self.timeout, self.backup_chats)
        timer.start()

    def backup_chats(self):
        if DEBUG: print("Backing up chat...")
        for c in list(self.chat_dict.keys()):
            self.chat_dict[c].backup_chat()
        self.triggered = False
        self.set_backup_alarm()

    def make_new_chat(self,chatID):
        # Looks in the database for existing info
        chat_hist = {}
        newchat = Chat(chatID, chat_hist)
        new_manager = self.make_new_chatmgr(newchat)
        self.chat_dict[chatID] = new_manager
        return

    def clean_message(self, rawtext):
        cln_txt = format_text(rawtext)
        return cln_txt

    def get_bot_reply(self,chatID,msg):
        self.trigger_backup()
        # Create a new chat if never chat before
        if not chatID in self.chat_dict:
            self.make_new_chat(chatID)
        curr_chat_mgr = self.chat_dict[chatID]
        if DEBUG: print("Current chat manager is for", chatID)
        f_msg = self.clean_message(msg)
        reply = curr_chat_mgr.respond_to_message(f_msg)
        return reply

if __name__ == "__main__":
    # Local running
    bot = Chatbot()
    bot.start()
    # while 1:
    if 1:
        incoming_msg = input()
        reply = bot.get_bot_reply("MyUserId",incoming_msg)
        print(reply)