#handles the formatting of the incoming message and reply them
#clean msg to remove stopword, punctuation, change from english to chinese, remove emoji, remove website, traditional to normal chinese

import re
from bot_LeftBrain import NLU
from bot_RightBrain import POLICY
from bot_Arm import ACTION
from bot_ShortTermMemory import STATE

with open(r"D:\data (unsorted)\中文停用词.txt","r",encoding="utf-8") as f:
    w = f.readlines()
stopword_list = [word.strip() for word in w]
#website,emoji,punctuation
remove_pattern = [r"http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+",r"[[].*[]]",r"[ \\[ \\] \\^ \\-_*×――(^)（^）$%~!@#$…&%￥—+=<>《》!！??？:：•`·、。，；,.;\"‘’“”-]"]

def clean_msg(msg,stopword_list,remove_pattern):
    # for pattern in remove_pattern:
    #     msg = re.sub(pattern,"",msg)
    # for stopword in stopword_list:
    #     msg = msg.replace(stopword,"")
    return msg

class Chatbot:
    def __init__(self,user_id):
        self.name = "BOT"
        self.user = user_id
        self.NLU = NLU()
        self.POLICY = POLICY()
        self.ACTION = ACTION()

    def reply(self,query_list,reply_list):
        print("-"*10)
        for query in query_list:
            print("{0}  >>>  {1}".format(self.user,query))
        for reply in reply_list:
            print("{0}  >>>  {1}".format(self.name,reply))
        print("-"*10)    
    
    def get_reply_list(self,msg_list):
        reply = []
        for msg in msg_list:
            response = self.get_reply(msg)
            if response["isImpt"]:
                reply.append(response["msg"])
        if reply == []:
            reply = [response["msg"]]
        return reply

    def get_reply(self,msg):
        intent,context,slot = self.NLU.get_nlu(msg)
        #reply = self.POLICY.get_action(intent,context,slot)


        reply = {"msg":"Hi!","isImpt": True}
        return reply

if __name__ == "__main__":
    while True:
        user_id = input("User_id: ")
        bot = Chatbot(user_id)
        query = input("Query: ")
        msg_list = query.split(" ")
        clean_msg_list = [clean_msg(msg,stopword_list,remove_pattern) for msg in msg_list if not msg.strip() == ""]
        reply = bot.get_reply_list(clean_msg_list)
        bot.reply(clean_msg_list,reply)
    