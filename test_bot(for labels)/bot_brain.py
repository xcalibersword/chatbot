#identify slot,intent and context of a given query
#kiv context

import jieba
import re

intent_dict = {
                "user.request.product_details":
                {
                    "pattern":r"(http://item[.]taobao[.]com/item[.]htm[?]id=\d+|[[]卡片[]])"
                },
                "user.greet":
                {
                    "pattern":r"(你好|在吗|hi|hello|hey)"
                },
                "user.request.fee":
                {
                    "pattern":r"(怎么收费呢)",
                    "slot_required":["city","product","month","hasAcc"]
                },
                "user.affirm":
                {
                    "pattern":r"(有)"
                },
                "user.inform":
                {
                    "pattern":r"(有)"
                }
            }
#r"\b()\b"
slot_dict = {
                "city":
                {
                    "上海":r"(上海)"
                },
                "product":
                {
                    "代缴":r"(社保公积金代缴)"
                },
                "hasAcc":
                {
                    "有":r"(上海户籍|有)",
                    "没有":r"(没有)"
                },
                "month":
                {
                    "四月":r"(四月)",
                    "五月":r"(五月)"
                }
            }

context_dict = {
    "PER":[],
    "ORG":[],
    "LOC":[],
    "PRODUCT":[],
    }

class NLU():
    def __init__(self):
        self.intent = intent_dict
        self.slot = slot_dict
        self.context = context_dict
    
    def match_intent(self,msg):
        intent_found = ""
        req_slot = []
        for k,v in self.intent.items():
            if re.search(v["pattern"],msg):
                intent_found = k
                try:
                    req_slot = v["slot_required"]
                except Exception:
                    req_slot = []
        return intent_found,req_slot

    def match_slot(self,msg,req_slot):
        slot_found = {}
        for slot in req_slot:
            for k,v in self.slot[slot].items():
                if re.search(v,msg):
                    slot_found[slot]=k
                else:
                    slot_found[slot]=""
        return slot_found

    def get_nlu(self,msg):
        #do single intent first
        intent,req_slot = self.match_intent(msg)
        filled_slot = self.match_slot(msg,req_slot)
        print("="*20)
        print("NLU result")
        print("Intents: {}".format(intent))
        print("Slots: {}".format(filled_slot))
        print("="*20)
        return intent,filled_slot

if __name__ == "__main__":
    n = NLU()
    while True:
        msg = input()
        n.get_nlu(msg)