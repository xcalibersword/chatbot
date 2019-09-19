import random
import re
import json
import cbsv
import signal
from initalizers import master_initalize
from chatbot_supp import *
from chatclass import *

DEBUG = 1

def dict_lookup(key, dictionary):
    if key in dictionary:
        return dictionary[key]
    return False

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
    timeout = 20
    def __init__(self, comps):
        self.PREV_REPLY_FLAG = "prev_state_message"
        self.dm = comps['dmanager']
        self.ip = comps['iparser']
        self.pk = comps['pkeeper']
        self.rg = comps['replygen']
    
    def make_new_chatmgr(self, chat):
        return ChatManager(chat, self.ip, self.pk, self.rg, self.dm)

    def start(self):
        print("Hello, I am a bot!")
        self.chat_dict = {}
        self.chat_timestamps = {}
        self.triggered = False

        return

    def trigger_backup(self):
        if not self.triggered:
            self.set_backup_alarm()
            self.triggered = True

    def set_backup_alarm(self):
        if not self.triggered:
            # No need for backup when no new messages
            return
        signal.signal(signal.SIGALRM, self.backup_chats)
        signal.alarm(self.timeout)

    def backup_chats(self, signum, frame):
        self.triggered = False
        signal.alarm(0)
        print("BACKING UP CHAT","signum",signum)
        for c in list(self.chat_dict.keys()):
            self.chat_dict[c].backup_chat()
        self.set_backup_alarm()

    def make_new_chat(self,chatID):
        # inital issues = {}
        chat_hist = {}
        newchat = Chat(chatID, chat_hist)
        new_manager = self.make_new_chatmgr(newchat)
        self.chat_dict[chatID] = new_manager
        return

    def clean_message(self, rawtext):
        cln_txt = format_text(rawtext)
        return cln_txt

    def recv_new_message(self,chatID,msg):
        self.trigger_backup()
        # Create a new chat if never chat before
        if not chatID in self.chat_dict:
            self.make_new_chat(chatID)
        curr_chat_mgr = self.chat_dict[chatID]
        # curr_chat = self.chats[chatID]
        # reply = self.respond_to_msg(curr_chat,msg)
        f_msg = self.clean_message(msg)
        reply = curr_chat_mgr.respond_to_message(f_msg)
        print(reply)
        return



# EXTENSIONS:
# Looking at a deeper history rather than just the previous state. LOC: decide_action


if __name__ == "__main__":
    # load json and print
    components = master_initalize()
    bot = Chatbot(components)
    bot.start()
    while 1:
        incoming_msg = input()
        bot.recv_new_message("MyUserId",incoming_msg)