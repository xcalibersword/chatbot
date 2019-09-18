import random
import re
import json
import cbsv
import signal
from chatbot_supp import *
from chatclass import *

DEBUG = 1

def dict_lookup(key, dictionary):
    if key in dictionary:
        return dictionary[key]
    return False

def read_json(json_filename):
    with open(json_filename, 'r') as f:
        data = json.loads(f.read())
    return data

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

PLAN_DICT = {"products":{
        "p_01": {
            "price": 100,
            "desc": "Basic plan A"
        },
        "p_02": {
            "price": 150,
            "desc": "More advanced plan. Plan A + feature"
        },
        "p_03": {
            "price": 9001,
            "desc": "Extremely comprehensive plan C. C for full Coverage"
        },
        "ERR":{
            "price":0,
            "desc": "Something went wrong"
        }
    }
}

def parse_plan_selection(msg):
    msg = msg.replace("plan", "")
    msg = msg.replace(" ", "")
    selection = "ERR"
    if re.fullmatch('a|1', msg):
        selection = "p_01"
    elif re.fullmatch('b|2', msg):
        selection = "p_02"
    elif re.fullmatch('c|3', msg):
        selection = "p_03"

    product = PLAN_DICT["products"][selection]
    s_data = (selection, product["price"], product["desc"])

    return s_data

def init_replygen(jdata):
    INTENTS = jdata["intents"]
    STATE_KEYS = cbsv.state_key_dict(jdata["states"])
    REPLY_DB = jdata["reply_db"]

    # Actually empty but I'm leaving a template here
    STS_REPLY_KEY_LOOKUP = {
        (STATE_KEYS['payment'], STATE_KEYS['finish_sale']): "r_sale_done"
    }

    SS_REPLY_KEY_LOOKUP = {
        STATE_KEYS["propose_plan"]: "r_state_details",
        STATE_KEYS['confirm_plan']: "r_confirm_plan",
        STATE_KEYS['payment']: "r_confirm_price",
        STATE_KEYS['finish_sale']: "r_sale_done",
        STATE_KEYS['recv_info']: "r_req_info",
        STATE_KEYS['init_sale']: "r_sales_intro",
        STATE_KEYS['ask_if_issue']: "r_ask_if_issue"
    }

    INTENT_REPLY_KEY_LOOKUP = {}
    gen_reply_list = ["ask_name", "greet", "goodbye"]
    for i in gen_reply_list:
        intent = INTENTS[i]
        dbk = "r_"+str(i)
        INTENT_REPLY_KEY_LOOKUP[intent] = dbk
    rkey_dbs = {}
    rkey_dbs["s2s"] = STS_REPLY_KEY_LOOKUP
    rkey_dbs["ss"] = SS_REPLY_KEY_LOOKUP
    rkey_dbs["intent"] = INTENT_REPLY_KEY_LOOKUP
    
    return ReplyGenerator(REPLY_DB, rkey_dbs)

def init_policykeeper(jdata):
    INTENTS = jdata["intents"]
    STATES = jdata["states"]
    STATE_KEYS = cbsv.state_key_dict(jdata["states"])
    MATCH_DB = jdata["match_db"]

    ### POLICIES ###

    default_policy_set = [
        (INTENTS['greet'], SIP.same_state()),
        (INTENTS['ask_name'],SIP.same_state()),
        (INTENTS['deny'], SIP.go_back_state()),
        (INTENTS['goodbye'], SIP(STATES["goodbye"])),
        (INTENTS['report_issue'], SIP(STATES['log_issue'])),
        (INTENTS['reset_chat'], SIP(STATES['init']))
    ]
    make_policy = lambda s_ints: Policy(default_policy_set,s_ints)

    POLICY_RULES = {
        STATE_KEYS['init']: make_policy([
            (INTENTS['deny'],SIP(STATES['init'])),
            (INTENTS['greet'],SIP(STATES['init'])),
            (INTENTS['gen_query'],SIP(STATES['confirm_query'])),
            (INTENTS['purchase'], SIP(STATES['init_sale'])),
            (INTENTS['pay_query'], SIP(STATES['pay_query'])),
            (INTENTS['sales_query'], SIP(STATES['sales_query']))
            ]
        ),
        STATE_KEYS['init_sale']: make_policy([
            (INTENTS['affirm'], SIP(STATES['propose_plan'])),
            (INTENTS['deny'], SIP(STATES['ask_if_issue']))
            ]
        ),
        STATE_KEYS['propose_plan']: make_policy([
            (INTENTS['affirm'], SIP(STATES['confirm_plan'])),
            (INTENTS['deny'], SIP(STATES['ask_if_issue']))
            ]
        ),
        STATE_KEYS['confirm_plan']: make_policy([
            (INTENTS['affirm'], SIP(STATES['payment'])),
            (INTENTS['deny'], SIP(STATES['ask_if_issue']))
            ]
        ),
        STATE_KEYS['ask_if_issue']: make_policy([
            (INTENTS['affirm'], SIP(STATES['log_issue'])),
            (INTENTS['deny'], SIP.goto_pending_state())
            ]
        ),
        STATE_KEYS['payment']: make_policy([
            (INTENTS['affirm'], SIP(STATES['finish_sale'])),
            (INTENTS['deny'], SIP(STATES['ask_if_issue']))
            ]
        )
    }

    # Loop to make all policies
    existing = list(POLICY_RULES.keys())
    for k in list(STATES.keys()):
        state_value = STATES[k]["key"]
        if state_value in existing:
            continue # Don't overwrite existing policy lookup values
        POLICY_RULES[state_value] = make_policy([])


    INTENT_LOOKUP_TABLE = {}
    for k in list(MATCH_DB.keys()):
        look_key = k[3:]
        kv = INTENTS[look_key]
        INTENT_LOOKUP_TABLE[kv] = MATCH_DB[k]

    return PolicyKeeper(POLICY_RULES, INTENT_LOOKUP_TABLE)


def init_detailmanager(jdata):
    vault = Info_Vault(jdata)
    return DetailManager(vault)

def master_initalize(jdata):
    # INTENTS = jdata["intents"]
    # STATE_KEYS = jdata["state_keys"]
    # MATCH_DB = jdata["match_db"]
    components = {}
    components["replygen"] = init_replygen(jdata)
    components["pkeeper"] = init_policykeeper(jdata)
    components["dmanager"] = init_detailmanager(jdata)
    return components

# Big Chatbot class
class Chatbot():
    timeout = 10
    def __init__(self, infoparser, comps):
        self.PREV_REPLY_FLAG = "prev_state_message"
        self.dm = comps['dmanager']
        self.ip = infoparser
        self.pk = comps['pkeeper']
        self.rg = comps['replygen']
    
    def make_new_chatmgr(self, chat):
        return ChatManager(chat, self.ip, self.pk, self.rg, self.dm)

    def start(self):
        print("Hello, I am a bot!")
        self.chat_dict = {}
        self.chat_timestamps = {}
        # Set an alarm
        self.set_backup_alarm()
        return

    def set_backup_alarm(self):
        signal.signal(signal.SIGALRM, self.backup_chats)
        signal.alarm(self.timeout)

    def backup_chats(self, signum, frame):
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




# TODO: Maybe have a ReplyGenerator object so I can remove it from Chatbot?


# EXTENSIONS:
# Looking at a deeper history rather than just the previous state. LOC: decide_action



if __name__ == "__main__":
    # load json and print
    json_data = read_json("chatbot_resource.json")
    parser = InfoParser()
    components = master_initalize(json_data)
    bot = Chatbot(parser,components)
    bot.start()
    while 1:
        incoming_msg = input()
        bot.recv_new_message("MyUserId",incoming_msg)