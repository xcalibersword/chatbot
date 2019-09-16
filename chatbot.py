import random
import re
import json
import cbsv
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
    STATES = jdata["states"]
    REPLY_DB = jdata["reply_db"]

    STS_REPLY_KEY_LOOKUP = {
        (STATES["init_sale"], STATES["choose_plan"]): "r_list_plans",
        (STATES['choose_plan'], STATES['confirm_plan']): "r_confirm_plan",
        (STATES['confirm_plan'], STATES['payment']): "r_confirm_price",
        (STATES['payment'], STATES['finish_sale']): "r_sale_done"
    }

    SS_REPLY_KEY_LOOKUP = {
        STATES['init_sale']:"r_sales_intro",
        STATES['ask_if_issue']:"r_ask_if_issue"
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
    ### POLICIES ###

    default_policy_set = [
        (INTENTS['greet'],SIP.same_state()),
        (INTENTS['ask_name'],SIP.same_state()),
        (INTENTS['deny'], SIP.go_back_state()),
        (INTENTS['goodbye'], SIP(STATES["goodbye"])),
        (INTENTS['report_issue'], SIP(STATES['log_issue']))
    ]
    make_policy = lambda s_ints: Policy(default_policy_set,s_ints)

    POLICY_RULES = {
        STATES['init']: make_policy([
            (INTENTS['deny'],SIP(STATES['init'])),
            (INTENTS['greet'],SIP(STATES['init'])),
            (INTENTS['gen_query'],SIP(STATES['confirm_query'])),
            (INTENTS['purchase'], SIP(STATES['init_sale'])),
            (INTENTS['pay_query'], SIP(STATES['pay_query'])),
            (INTENTS['sales_query'], SIP(STATES['sales_query']))
            ]
        ),
        STATES['init_sale']: make_policy([
            (INTENTS['affirm'], SIP(STATES['choose_plan'])),
            (INTENTS['deny'], SIP(STATES['ask_if_issue']))
            ]
        ),
        STATES['choose_plan']: make_policy([
            (INTENTS['indicate_plan'], SIP(STATES['confirm_plan'])),
            (INTENTS['deny'], SIP(STATES['ask_if_issue']))
            ]
        ),
        STATES['confirm_plan']: make_policy([
            (INTENTS['affirm'], SIP(STATES['payment'])),
            (INTENTS['deny'], SIP(STATES['ask_if_issue']))
            ]
        ),
        STATES['payment']: make_policy([
            (INTENTS['affirm'], SIP(STATES['finish_sale'])),
            (INTENTS['deny'], SIP(STATES['ask_if_issue']))
            ]
        )
    }

    # Loop to make all policies
    existing = list(POLICY_RULES.keys())
    for k in list(STATES.keys()):
        state_value = STATES[k]
        if state_value in existing:
            continue # Don't overwrite existing policy lookup values
        POLICY_RULES[state_value] = make_policy([])


    INTENT_LOOKUP_TABLE = {}
    for k in list(MATCH_DB.keys()):
        look_key = k[3:]
        kv = INTENTS[look_key]
        INTENT_LOOKUP_TABLE[kv] = MATCH_DB[k]

    return PolicyKeeper(POLICY_RULES, INTENT_LOOKUP_TABLE)


def master_initalize(jdata):
    # INTENTS = jdata["intents"]
    # STATES = jdata["states"]
    # MATCH_DB = jdata["match_db"]

    components["replygen"] = init_replygen(jdata)
    components["pkeeper"] = init_policykeeper(jdata)
    return components

# Big Chatbot class
class Chatbot():
    INTENTS, STATES, MATCH_DB, REPLY_DB, ALL_PRODUCTS = ({},{},{},{},{})
    def __init__(self, vault, infoparser, components):
        self.PREV_REPLY_FLAG = "prev_state_message"
        self.vault = vault
        self.pkeeper = pkeeper
        self.replygen = replygen
        self.gs = gs
    
    def make_new_chatmgr(self, chat):
        return ChatManager(chat, self.pkeeper, self.replygen, self.gs)

    def start(self):
        print("Hello, I am a bot!")
        self.chat_dict = {}
        return

    def make_new_chat(self,chatID):
        # inital issues = {}
        initial_state = STATES["init"]
        newchat = Chat(chatID, {},initial_state)
        self.chat_dict[chatID] = self.make_new_chatmgr(newchat)
        return

    def clean_message(self, rawtext):
        cln_txt = format_text(rawtext)
        return cln_txt

    def recv_new_message(self,chatID,msg):
        # Create a new chat if never chat before
        if not chatID in self.chat_dict:
            self.make_new_chat(chatID)
        # curr_chat = self.chats[chatID]
        # reply = self.respond_to_msg(curr_chat,msg)
        f_msg = self.clean_message(msg)
        curr_chat_mgr = self.chat_dict[chatID]
        reply = chat_manager.respond_to_message(f_msg)
        print(reply)
        return


    # TODO: reimplement this
    # REMOVED
    def decide_action(self, uds, chat):
        STS_REPLY_KEY_LOOKUP = self.STS_REPLY_KEY_LOOKUP
        SS_REPLY_KEY_LOOKUP = self.SS_REPLY_KEY_LOOKUP
        INTENT_REPLY_KEY_LOOKUP = self.INTENT_REPLY_KEY_LOOKUP

        def getreplykey(curr_state, intent, next_state):
            context = (curr_state, next_state)
            print("cstate, nstate",context)
            # Specific state to state
            rkey = dict_lookup(context, STS_REPLY_KEY_LOOKUP)
            
            # Single state
            if not rkey:
                rkey = dict_lookup(next_state, SS_REPLY_KEY_LOOKUP)
            
            # Intent
            if not rkey:
                rkey = dict_lookup(intent, INTENT_REPLY_KEY_LOOKUP)

            return rkey

        sip = uds.get_sip()
        if sip.is_go_back():
            replytxt = chat.pop_prev_msg()
            return action.go_back()
            
        # Somehow have a callback for changing chat state.

        curr_state = chat.get_state()
        reply_key = getreplykey(curr_state, uds.intent, sip.get_state())
        
        print("reply_key <", reply_key,">")

        replytxt = self.generate_reply(reply_key)
        action = Action.reply(replytxt)
    
        return action

    def process_intent(self, intent, msg):
        SPECIAL_PARSE_INTENTS = self.SPECIAL_PARSE_INTENTS
        if intent in SPECIAL_PARSE_INTENTS:
            callback = SPECIAL_PARSE_INTENTS[intent]
            print("callback",callback)
            select = callback(msg)
            return select 

        return -1
    

    # Returns a text reply
    def respond_to_msg(self, chat, msg):
        INTENT_LOOKUP_TABLE = self.INTENT_LOOKUP_TABLE
        RECORDING_STATES = self.RECORDING_STATES # EXISTS BUT NOT USED RN
        SPECIAL_INTENT_LIST = self.SPECIAL_INTENT_LIST

        # STATIC_INTENTS = self.STATIC_INTENTS
        # UNIVERSAL_INTENTS = self.UNIVERSAL_INTENTS
        def get_intent_from_db(msg, intent_db_list, exact=False):
            for intent_db in intent_db_list:
                intent = intent_db[0]
                regex_db = intent_db[1]
                if cbsv.check_input_against_db(msg,regex_db,exact):
                    return intent
            return False

        # Special intent match exact?
        def get_special_intent(state, msg):
            def get_sil_state(e):
                return e[0]
            def get_sil_pairlist(e):
                return e[1]
            for entry in SPECIAL_INTENT_LIST:
                s_db_list = get_sil_pairlist(entry)
                if state == get_sil_state(entry):
                    return get_intent_from_db(msg,s_db_list,exact = True)
                

        ### INTENT ###
        # Checks message for db keywords
        # TODO: implement better word comprehension

        curr_state = chat.get_state()
        curr_uds = self.decipher_message(curr_state, msg)
        intent = curr_uds.intent

        # print("intent",intent)
        packet = curr_uds.get_sip()

        # TODO: Better software engine practice
        action = self.decide_action(curr_uds, chat)

        # Change state of chat
        self.change_chat_state(chat, packet, select)
        
        # Get reply        
        reply = action.message
        chat.set_prev_msg(reply)

        # if DEBUG:
        #     return (reply, chat.get_state())

        return reply

    def change_chat_state(self, chatmgr, sip, selection = -1):
        # Go to previous state
        chat.update_chat(sip)
        
    def init_mappings(self):
        # These dicts can only be built AFTER resources are initalized 
        if DEBUG: print("Initalizing mappings")
        # List for lookup purposes
        self.RECORDING_STATES = [
            STATES['log_issue'],
        ]

        self.SPECIAL_PARSE_INTENTS = {
            INTENTS['indicate_plan']: parse_plan_selection
        }

        # Contextual Intents
        # key: state, val: list of intents
        # As opposed to general intents, these special intents are only looked for when in certain states
        self.SPECIAL_INTENT_LIST = [
            (STATES['gen_query'],[(INTENTS['indicate_query'], MATCH_DB["db_gen_query"])]),
            (STATES['choose_plan'],[(INTENTS['indicate_plan'], MATCH_DB["db_indicate_plan"])])
        ]

        self.STS_REPLY_KEY_LOOKUP = {
            (STATES["init_sale"], STATES["choose_plan"]): "r_list_plans",
            (STATES['choose_plan'], STATES['confirm_plan']): "r_confirm_plan",
            (STATES['confirm_plan'], STATES['payment']): "r_confirm_price",
            (STATES['payment'], STATES['finish_sale']): "r_sale_done"
        }

        self.SS_REPLY_KEY_LOOKUP = {
            STATES['init_sale']:"r_sales_intro",
            STATES['ask_if_issue']:"r_ask_if_issue"
        }

        self.INTENT_REPLY_KEY_LOOKUP = {}
        gen_reply_list = ["ask_name", "greet", "goodbye"]
        for i in gen_reply_list:
            intent = INTENTS[i]
            dbk = "r_"+str(i)
            self.INTENT_REPLY_KEY_LOOKUP[intent] = dbk
    
        # Changes state no matter what current state is
        # INTENTS['report_issue']: (STATES['log_issue'], "Please state your issue")

        # These policies are accessible from every state
        default_policy_set = [
            (INTENTS['greet'],SIP.same_state()),
            (INTENTS['ask_name'],SIP.same_state()),
            (INTENTS['deny'], SIP.go_back_state()),
            (INTENTS['goodbye'], SIP(STATES["goodbye"])),
            (INTENTS['report_issue'], SIP(STATES['log_issue']))
        ]

        # (INTENTS['provide_info'],SIP.same_state()),


        make_policy = lambda s_ints: Policy(default_policy_set,s_ints)

        ### POLICIES ###
        self.POLICY_RULES = {
            STATES['init']: make_policy([
                (INTENTS['deny'],SIP(STATES['init'])),
                (INTENTS['greet'],SIP(STATES['init'])),
                (INTENTS['gen_query'],SIP(STATES['confirm_query'])),
                (INTENTS['purchase'], SIP(STATES['init_sale'])),
                (INTENTS['pay_query'], SIP(STATES['pay_query'])),
                (INTENTS['sales_query'], SIP(STATES['sales_query']))
                ]
            ),
            STATES['init_sale']: make_policy([
                (INTENTS['affirm'], SIP(STATES['choose_plan'])),
                (INTENTS['deny'], SIP(STATES['ask_if_issue']))
                ]
            ),
            STATES['choose_plan']: make_policy([
                (INTENTS['indicate_plan'], SIP(STATES['confirm_plan'])),
                (INTENTS['deny'], SIP(STATES['ask_if_issue']))
                ]
            ),
            STATES['confirm_plan']: make_policy([
                (INTENTS['affirm'], SIP(STATES['payment'])),
                (INTENTS['deny'], SIP(STATES['ask_if_issue']))
                ]
            ),
            STATES['payment']: make_policy([
                (INTENTS['affirm'], SIP(STATES['finish_sale'])),
                (INTENTS['deny'], SIP(STATES['ask_if_issue']))
                ]
            )
        }

        # Loop to make all policies
        existing = list(self.POLICY_RULES.keys())
        for k in list(STATES.keys()):
            state_value = STATES[k]
            if state_value in existing:
                continue
            self.POLICY_RULES[state_value] = make_policy([])
        # print("Policy keys",list(self.POLICY_RULES.keys()))

        return 

    
class Info_Vault():
    def __init__(self, json_data):
        self.plans = json_data["plans"]
        self.city_keys = list(self.plans.keys())
        self.other_keys = ["asd"]
    # General query
    def lookup(self, q):
        if q in city_keys:
            return lookup_city(q)
        if q in other_keys:
            return lookup_other(q)
        return False
        
    def lookup_city(self, city):
        if city in self.city_keys:
            return self.plans[city]

    def lookup_other(self, thing):
        if thing in self.other_keys:
            return 1



# TODO: Maybe have a ReplyGenerator object so I can remove it from Chatbot?


# EXTENSIONS:
# Looking at a deeper history rather than just the previous state. LOC: decide_action



if __name__ == "__main__":
    # load json and print
    json_data = read_json("chatbot_resource.json")
    vault = Info_Vault(json_data)
    parser = InfoParser()
    components = master_initalize(json_data)
    bot = Chatbot(json_data,vault,parser,components)
    bot.start()
    while 1:
        incoming_msg = input()
        bot.recv_new_message("MyUserId",incoming_msg)