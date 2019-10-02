import json
import os

def json_file_to_dict(path):
    with open(path,'r') as f:
        dict = json.load(fp=f)
    return dict    

class Chatbot:
    def __init__(self):
        self.name = "BOT"
        self.nlu = json_file_to_dict(r"C:\Users\Administrator\Desktop\code (unsorted)\chatbot\test_bot(for labels)\preset\NLU.json")
        self.template = json_file_to_dict(r"C:\Users\Administrator\Desktop\code (unsorted)\chatbot\test_bot(for labels)\preset\dialog_template.json")
        self.cust_info = json_file_to_dict(r"C:\Users\Administrator\Desktop\code (unsorted)\chatbot\test_bot(for labels)\preset\customer_info.json")
        self.company_info = json_file_to_dict(r"C:\Users\Administrator\Desktop\code (unsorted)\chatbot\test_bot(for labels)\preset\company_info.json")        

    def reply(self,user_id,query_list,reply_list):
        print("-"*10)
        for query in query_list:
            print("{0}  >>>  {1}".format(user_id,query))
        for reply in reply_list:
            print("{0}  >>>  {1}".format(self.name,reply))
        print("-"*10)    
    
    def get_reply_list(self,user_id,msg_list):
        reply = []
        for msg in msg_list:
            response = self.get_reply(user_id,msg)
            if response["isImpt"]:
                reply.append(response["msg"])
        if reply == []:
            reply = [response["msg"]]
        return reply

    def get_reply(self,user_id,msg):



        reply = {"msg":"Hi!","isImpt": True}
        return reply

if __name__ == "__main__":

    bot = Chatbot()
    print(bot.nlu)
    print(bot.company_info)
    print(bot.cust_info)
    print(bot.template)
    # while True:
    #     user_id = input("User_id: ")
    #     msg = input("Query: ")
    #     msg = msg.split(" ")
    #     reply = bot.get_reply_list(user_id,msg)
    #     bot.reply(user_id,msg,reply)
        
"""
intent
    use pattern to match whole sentence
    decide the next course of action

action
    has slot to fill
    has context to fill
    SQl query generated based on value of slot and context to generate the ideal response    

Dialog manger
Bot take in template, take in NLU json
Use NLU json to identify the intent
Pick up the template to use based on intent
Fill the slot and context in the template
Return the model answer


NLU
Take in Query
Returns intent, slot and entity

"""