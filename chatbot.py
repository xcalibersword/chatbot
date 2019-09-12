import random
import re
import json
import cbsv
from chatbot_supp import *

DEBUG = 1

# Functions that don't need other inits
def rand_response(response_list):
    return random.choice(response_list)

def read_json(json_filename):
    with open(json_filename, 'r') as f:
        data = json.loads(f.read())
    return data

# Default things

pattern = "你还记得(.*)吗？"
random_chat = [
    "多说一点！",
    "为什么你那么认为？"
]
# SALES_PITCH = "您好，欢迎光临唯洛社保，很高兴为您服务。本店现在可以代缴上海、北京、长沙、广州、苏州、杭州、成都的五险一金。请问需要代缴哪个城市的呢？需要从几月份开始代缴呢？注意：社保局要求已怀孕的客户（代缴后再怀孕的客户不受影响）和重大疾病或者慢性病状态客户，我司不能为其代缴社保，如有隐瞒恶意代缴的责任自负！请注意参保手续开始办理后，无法退款。"


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

# Big Chatbot class
class Chatbot():
    INTENTS, STATES, MATCH_DB, REPLY_DB, ALL_PRODUCTS = ({},{},{},{},{})
    def __init__(self,json_data):
        self.PREV_REPLY_FLAG = "prev_state_message"
        self.init_bot(json_data)

    def init_bot(self,jdata):
        self.init_json_info(jdata)
        self.init_mappings()
        return

    def init_json_info(self, jdata):
        global INTENTS, STATES, MATCH_DB, REPLY_DB    
        INTENTS = jdata["intents"]
        STATES = jdata["states"]
        MATCH_DB = jdata["match_db"]
        REPLY_DB = jdata["reply_db"]
        ALL_PRODUCTS = jdata['products']
        return

    def start(self):
        print("Hello, I am a bot!")
        self.chats = {}
        return

    def make_new_chat(self,chatID):
        # inital issues = {}
        initial_state = STATES["init"]
        newchat = Chat(chatID, {},initial_state)
        self.chats[chatID] = newchat
        return

    def recv_new_message(self,chatID,msg):
        # Create a new chat if never chat before
        if not chatID in self.chats:
            self.make_new_chat(chatID)
        curr_chat = self.chats[chatID]
        reply = self.respond_to_msg(curr_chat,msg)
        print(reply)
        return

    # Generates a pure reply as in a text
    def generate_reply(self, reply_key, chat):
        REPLY_DATABASE = self.REPLY_DATABASE
        CONTEXT_REPLY_STATES = self.CONTEXT_REPLY_STATES
        def get_reply_list(rkey):
            reply_list = REPLY_DATABASE[rkey]
            return reply_list

        if reply_key == self.PREV_REPLY_FLAG:
            return chat.pop_prev_msg()

        if not reply_key:
            return cbsv.DEFAULT_CONFUSED()

        curr_state = chat.get_state()
        if curr_state in CONTEXT_REPLY_STATES:
            context_info = chat.get_selection()
            if DEBUG: print("ctxt",context_info)
            msg_template = reply_key # TODO have proper message template lookups instead of hardcoded reply key
            # construct message
            name, price, desc = context_info
            replytext = msg_template.format(name, desc, price)
            # print("replytxt", replytext)  
            return replytext

        if reply_key in REPLY_DATABASE:
            r_list = get_reply_list(reply_key)
            replytext = rand_response(r_list)
            return replytext

        # Since reply_key are strings, this works for a fixed response.
        # TODO: Convert all replies to dictionaries
        return reply_key
    
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
        GENERAL_INTENT_LIST = self.GENERAL_INTENT_LIST
        POLICY_RULES = self.POLICY_RULES
        RECORDING_STATES = self.RECORDING_STATES
        SPECIAL_INTENT_LIST = self.SPECIAL_INTENT_LIST
        STATIC_INTENTS = self.STATIC_INTENTS
        UNIVERSAL_INTENTS = self.UNIVERSAL_INTENTS

        curr_state = chat.get_state()
        intent = message_to_intent(curr_state, msg)
        select = self.process_intent(intent, msg)
        if not isinstance(select, int):
            chat.set_selection(select)

        # print("intent",intent)
        new_state, reply_key = intent_to_reply(curr_state, intent)

        # TODO: Better software engine practice
        # Change state first
        self.change_chat_state(chat, new_state)
        # Get reply
        reply = self.generate_reply(reply_key,chat)
        chat.set_prev_msg(reply)

        if DEBUG:
            return (reply, chat.get_state())

        return reply

        def get_intent_from_db(msg, intent_db_list, exact=False):
            for intent_db in intent_db_list:
                intent = intent_db[0]
                regex_db = intent_db[1]
                if check_input_against_db(msg,regex_db,exact):
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

        def get_general_intent(msg):
            # Global reference to GENERAL_INTENT_LIST
            return get_intent_from_db(msg,GENERAL_INTENT_LIST)

        # Overall function
        def message_to_intent(curr_state,msg):
            select = -1
            # RECORD MSG
            if curr_state in RECORDING_STATES:
                record_msg(msg)

            p_msg = format_text(msg)
            # print("pmsg: <"+p_msg+">")
            intent = get_special_intent(curr_state,p_msg)
            if not intent:
                intent = get_general_intent(p_msg)
            
            if DEBUG: print("Intent is:",intent,"\n")

            return intent

        ### INTENT ###
        # Checks message for db keywords
        # TODO: implement better word comprehension
        def check_input_against_db(msg, db, exact):
            search_fn = lambda x,y: re.search(x,y)
            if exact:
                search_fn = lambda x,y: re.fullmatch(x,y)
            match = False

            for keyword in db:
                match = search_fn(keyword,msg)
                if match:
                    break
            return match

        def intent_to_reply(state, intent):
            state_n_reply = check_policies(state,intent)
            if not state_n_reply:
                return (state, False)
            return state_n_reply

        # Returns next state and reply_key
        def check_policies(curr_state, intent):
            pr_key = (curr_state,intent)
            if pr_key in POLICY_RULES:
                return POLICY_RULES[pr_key]
            if intent in UNIVERSAL_INTENTS:
                # Changes state no matter where you are
                return UNIVERSAL_INTENTS[intent]
            if intent in STATIC_INTENTS:
                # State doesnt change
                rep_key = STATIC_INTENTS[intent]
                return (curr_state,rep_key)
            return False

    def change_chat_state(self, chat, new_state, selection = -1):
        # Go to previous state
        if new_state == cbsv.PREV_STATE_FLAG():
            new_state = chat.get_prev_state()

        if not isinstance(selection,int):
            chat.set_selection(selection)

        chat.change_state(new_state)
        
    def init_mappings(self):
        # These dicts can only be built AFTER resources are initalized 
        self.REPLY_DATABASE = {}
        REPLY_DB_LIST = ["greet", "purchase", "goodbye", "sales_query", "ask_name", "sales_pitch"]
        for k in REPLY_DB_LIST:
            dbk = "r_" + k
            # Append as a tuple
            self.REPLY_DATABASE[k] = REPLY_DB[dbk]

        # Changes state no matter what current state is
        self.UNIVERSAL_INTENTS = {
            INTENTS['purchase']: (STATES['choose_plan'], "purchase"),
            INTENTS['sales_query']: (STATES['sales_query'], "sales_query"),
            INTENTS['report_issue']: (STATES['log_issue'], "Please state your issue"),
            INTENTS['deny']: (STATES['PREV_STATE'], self.PREV_REPLY_FLAG)
        }

        self.STATIC_INTENTS = {
            INTENTS['greet']: 'greet',
            INTENTS['ask_name']: 'ask_name',
        }

        # List for lookup purposes
        self.RECORDING_STATES = [
            STATES['log_issue'],
        ]

        self.CONTEXT_REPLY_STATES = [
            
            STATES["confirm_plan"],
            STATES["payment"]
        ]

        self.SPECIAL_PARSE_INTENTS = {
            INTENTS['indicate_plan']: parse_plan_selection
        }

        self.GENERAL_INTENT_LIST = []
        GEN_INTENT_LIST_KEYS = ["greet", "ask_name", "affirm", "deny", "purchase", "gen_query", "sales_query", "pay_query","report_issue","goodbye"]
        for k in GEN_INTENT_LIST_KEYS:
            dbk = "db_" + k
            # Append as a tuple
            self.GENERAL_INTENT_LIST.append((INTENTS[k],MATCH_DB[dbk]))

        # Contextual Intents
        # key: state, val: list of intents
        # As opposed to general intents, these special intents are only looked for when in certain states
        self.SPECIAL_INTENT_LIST = [
            (STATES['gen_query'],[(INTENTS['indicate_query'], MATCH_DB["db_gen_query"])]),
            (STATES['choose_plan'],[(INTENTS['indicate_plan'], MATCH_DB["db_indicate_plan"])])
        ]

        ### POLICIES ###
        self.POLICY_RULES = {
            (STATES['init'], INTENTS['greet']): (STATES['init'], "sales_pitch"),
            (STATES['init'], INTENTS['gen_query']) : (STATES['confirm_query'], "您要问什么呢？"),
            (STATES['init'], INTENTS['purchase']): (STATES['init_sale'], "sales_query"),
            (STATES['init'], INTENTS['pay_query']): (STATES['pay_query'], "好的，那么"),
            (STATES['init'], INTENTS['goodbye']): (STATES['goodbye'], "BYE BYE"),
            (STATES['sales_query'], INTENTS['purchase']): (STATES['pay_query'], "好的，那么"),
            (STATES['sales_query'], INTENTS['goodbye']): (STATES['goodbye'], "WHY SIA"),
            (STATES['init_sale'], INTENTS['affirm']): (STATES['choose_plan'], "purchase"),
            (STATES['choose_plan'], INTENTS['confusion']): (STATES['sales_query'], "Oh, let me clarify the plans."),
            (STATES['choose_plan'], INTENTS['affirm']): (STATES['choose_plan'], "Great! But you still have to choose a plan."),
            (STATES['choose_plan'], INTENTS['indicate_plan']): (STATES['confirm_plan'], "Just to confirm, your have selected is {0}.\n Description:\n{1}"),
            (STATES['confirm_plan'], INTENTS['affirm']): (STATES['payment'], "That will be ${2}!"),
            (STATES['payment'], INTENTS['affirm']): (STATES['finish_sale'], "Success! Thank you for using SHEBAO! Is there anything else I can help with?"),
            (STATES['finish_sale'], INTENTS['affirm']): (STATES['init'], "sales_pitch"),
            (STATES['finish_sale'], INTENTS['deny']): (STATES['goodbye'], "Bye! Hope to see you again soon!"),
            (STATES['finish_sale'], INTENTS['goodbye']): (STATES['goodbye'], "Bye! Hope to see you again soon!"),
            (STATES['sales_query'], INTENTS['goodbye']): (STATES['goodbye'], "WHY SIA"),
            (STATES['goodbye'], INTENTS['goodbye']): (STATES['goodbye'],"You already said bye")
        }
        return 




# Check if search allows trailing chars
# E.g. plan alakazam = plan a

# if __name__ == "__main__":
#     def chk(inp):
#         o = re.search("plan (a|b|c)",inp)
#         print(o)
#         return
#     while 1:
#         i = input()
#         chk(i)


if __name__ == "__main__":
    print("Initializing...")
    # load json and print
    json_data = read_json("chatbot_resource.json")
    bot = Chatbot(json_data)
    bot.start()
    while 1:
        incoming_msg = input()
        bot.recv_new_message("MyUserId",incoming_msg)