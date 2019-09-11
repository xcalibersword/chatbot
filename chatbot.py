import random
import re
import json


# Functions that don't need other inits
def rand_response(response_list):
    return random.choice(response_list)

def read_json(json_filename):
    with open(json_filename, 'r') as f:
        data = json.loads(f.read())
    return data

# Default things
DEFAULT_CONFUSED = "不好意思，我听不懂"
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

# Big Chatbot class
class Chatbot():
    INTENTS, STATES, MATCH_DB, REPLY_DB = ({},{},{},{})
    def __init__(self,json_data):
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
        return

    def start(self):
        print("Hello, I am a bot!")
        self.chats = {}
        return

    def make_new_chat(self,chatID):
        # inital issues = {}
        newchat = Chat(chatID, {})
        self.chats[chatID] = newchat
        return

    def new_message(self,chatID,msg):
        if not chatID in self.chats:
            self.make_new_chat(chatID)
        curr_chat = self.chats[chatID]
        reply = self.get_reply_to_msg(curr_chat,msg)
        print(reply)
        return

    def get_reply_to_msg(self, chat, msg):
        GENERAL_INTENT_LIST = self.GENERAL_INTENT_LIST
        POLICY_RULES = self.POLICY_RULES
        RECORDING_STATES = self.RECORDING_STATES
        REPLY_DATABASE = self.REPLY_DATABASE
        SPECIAL_INTENT_LIST = self.SPECIAL_INTENT_LIST
        STATIC_INTENTS = self.STATIC_INTENTS
        UNIVERSAL_INTENTS = self.UNIVERSAL_INTENTS

        def get_reply_list(rkey):
            reply_list = REPLY_DATABASE[rkey]
            return reply_list

        def generate_reply(reply_key):
            if not reply_key:
                return DEFAULT_CONFUSED

            if reply_key in REPLY_DATABASE:
                r_list = get_reply_list(reply_key)
                replytext = rand_response(r_list)
                return replytext

            # Since reply_key are strings, this works for a fixed response.
            # TODO: Convert all replies to dictionaries
            return reply_key

        def get_intent_from_db(msg, intent_db_list, exact=False):
            for intent_db in intent_db_list:
                intent = intent_db[0]
                regex_db = intent_db[1]
                if check_input_against_db(msg,regex_db,exact):
                    return intent
            return False

        def get_special_intent(state, msg):
            def get_sil_state(e):
                return e[0]
            def get_sil_pairlist(e):
                return e[1]
            for entry in SPECIAL_INTENT_LIST:
                s_db_list = get_sil_pairlist(entry)
                if state == get_sil_state(entry):
                    return get_intent_from_db(msg,s_db_list)

        def get_general_intent(msg):
            # Global reference to GENERAL_INTENT_LIST
            return get_intent_from_db(msg,GENERAL_INTENT_LIST)


        # Overall function
        def message_to_intent(curr_state,msg):
            # RECORD MSG
            if curr_state in RECORDING_STATES:
                record_msg(msg)

            p_msg = format_text(msg)
            # print("pmsg: <"+p_msg+">")
            intent = get_special_intent(curr_state,p_msg)
            if not intent:
                intent = get_general_intent(p_msg)
            print("Intent is:",intent,"\n")
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

        curr_state = chat.get_state()
        intent = message_to_intent(curr_state, msg)
        # print("intent",intent)
        new_state, reply_key = intent_to_reply(curr_state, intent)
        reply = generate_reply(reply_key)
        self.update_chat(chat, new_state, reply)
        # reply = reply_key
        
        return reply

    def change_chat_state(self, chat, new_state, selection = -1):
        if new_state == self.PREV_STATE_FLAG:
            new_state = chat.get_prev_state()
        if not isinstance(selection,int):

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
            INTENTS['report_issue']: (STATES['log_issue'], "Please state your issue")
            INTENTS['deny']: (STATES['PREV_STATE'],"prev_state_msg")
        }

        self.STATIC_INTENTS = {
            INTENTS['greet']: 'greet',
            INTENTS['ask_name']: 'ask_name',
        }

    # KIV for lookup
    # MASTER_INTENT_DICT = {
    #     (INTENTS['greet'],db_greetings),
    #     (INTENTS['affirm'],db_affirm),
    #     (INTENTS['deny'],db_deny),
    #     (INTENTS['indicate_plan'],db_indicate_plan),
    #     (INTENTS['purchase'],db_purchase),
    #     (INTENTS['gen_query'],db_gen_query),
    #     (INTENTS['sales_query'], db_sales_query),
    #     (INTENTS['pay_query'], db_pay_query),
    #     (INTENTS['goodbye'],db_goodbye),
    #     (INTENTS['ask_name'],db_ask_name),
    #     (INTENTS['report_issue'],db_report_issue),
    # }

        # List for lookup purposes
        self.RECORDING_STATES = [
            STATES['log_issue'],
        ]

        self.GENERAL_INTENT_LIST = []
        GEN_INTENT_LIST_KEYS = ["greet", "ask_name", "affirm", "deny", "purchase", "gen_query", "sales_query", "pay_query","report_issue","goodbye"]
        for k in GEN_INTENT_LIST_KEYS:
            dbk = "db_" + k
            # Append as a tuple
            self.GENERAL_INTENT_LIST.append((INTENTS[k],MATCH_DB[dbk]))

        # self.MASTER_INTENT_LIST = [
        #     (INTENTS['greet'],db_greetings),
        #     (INTENTS['affirm'],db_affirm),
        #     (INTENTS['deny'],db_deny),
        #     (INTENTS['indicate_plan'],db_indicate_plan),
        #     (INTENTS['purchase'],db_purchase),
        #     (INTENTS['gen_query'],db_gen_query),
        #     (INTENTS['sales_query'], db_sales_query),
        #     (INTENTS['pay_query'], db_pay_query),
        #     (INTENTS['goodbye'],db_goodbye),
        #     (INTENTS['ask_name'],db_ask_name),
        #     (INTENTS['report_issue'],db_report_issue),
        # ]


        # Contextual Intents
        # key: state, val: list of intents
        self.SPECIAL_INTENT_LIST = [
            (STATES['gen_query'],[(INTENTS['indicate_query'], MATCH_DB["db_gen_query"])]),
            (STATES['choose_plan'],[(INTENTS['indicate_plan'],MATCH_DB["db_indicate_plan"])])
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
            (STATES['choose_plan'], INTENTS['indicate_plan']): (STATES['confirm_plan'], "Just to confirm, your plan is XXX."),
            (STATES['confirm_plan'], INTENTS['affirm']): (STATES['payment'], "That will be $100!"),
            (STATES['payment'], INTENTS['affirm']): (STATES['finish_sale'], "Success! Thank you for using SHEBAO! Is there anything else I can help with?"),
            (STATES['finish_sale'], INTENTS['affirm']): (STATES['init'], "sales_pitch"),
            (STATES['finish_sale'], INTENTS['deny']): (STATES['goodbye'], "Bye! Hope to see you again soon!"),
            (STATES['finish_sale'], INTENTS['goodbye']): (STATES['goodbye'], "Bye! Hope to see you again soon!"),
            (STATES['sales_query'], INTENTS['goodbye']): (STATES['goodbye'], "WHY SIA"),
            (STATES['goodbye'], INTENTS['goodbye']): (STATES['goodbye'],"You already said bye")
        }

        return 


# Try to have stateful changes
class Chat:
    def __init__(self,customer,convo_history):
        self.customer = customer
        self.state = STATES['init']
        self.convo_history = convo_history

    def change_state(self,new_state):
        self.prev_state = self.state
        self.state = new_state

    def get_state(self):
        return self.state

    def get_prev_state(self):
        return self.prev_state

    def set_selection(self,selection):
        self.selection = selection
    
    def get_selection(self,selection):
        return self.selection

    def clear_selection(self):
        self.selection = None

    def get_previous_issues(self):
        return self.user.get_issues()

class Customer:
    def __init__(self, userID, accounts = -1, issues = -1):
        self.userID = userID
        if isinstance(issues,int): 
            self.accounts = [] 
        else: 
            self.accounts = accounts
        if isinstance(issues,int):
            self.issues_list = []
        else:
            self.issues_list = issues

    def add_issue(self, issue):
        self.issues_list.append(issue)
        # Check for duplicates?

    def get_issues(self):
        return self.issues_list

    def get_accounts(self):
        return self.accounts




if __name__ == "__main__":
    print("Initializing...")
    # load json and print
    json_data = read_json("chatbot_resource.json")
    bot = Chatbot(json_data)
    bot.start()
    while 1:
        incoming_msg = input()
        bot.new_message("MyUserId",incoming_msg)