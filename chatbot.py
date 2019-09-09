import random
import re

STATES = {
    'init':20, 
    'sales_query':211, 
    'payment_query':212,
    'gen_query':213,
    'confirm_query': 218,
    'record_issue':251,
    'recommend':271,
    'init_sale':280,
    'choose_plan':281,
    'confirm_plan':282,
    'payment':283,
    'finish_sale':289,
    'goodbye': 299
}

INTENTS = {
    'greet':10,
    'affirm':191,
    'indicate_plan':181,
    'deny':192,
    'sales_query':111,
    'payment_query':112,
    'gen_query':113,
    'report_issue':151,
    'purchase':180,
    'goodbye':199
}

pattern = "你还记得(.*)吗？"

name = {
    "你的名字是什么？": [
        "我是回音机器人",
        "他们叫我王俊杰！",
        "我名回音，姓机器人"
    ],
}

SALES_PITCH = "您好，欢迎光临唯洛社保，很高兴为您服务。本店现在可以代缴上海、北京、长沙、广州、苏州、杭州、成都的五险一金。请问需要代缴哪个城市的呢？需要从几月份开始代缴呢？注意：社保局要求已怀孕的客户（代缴后再怀孕的客户不受影响）和重大疾病或者慢性病状态客户，我司不能为其代缴社保，如有隐瞒恶意代缴的责任自负！请注意参保手续开始办理后，无法退款。"

weather = {
    "今天天气怎样？":"今天{}"
}

db_affirm = [
    "yes","好","好的","可以","是的","有","没问题","确定","ok"
]

db_deny = ["不好","不可以","不是","没有","没问题","不确定","no","not ok"]

db_greetings = [
    '你好','hello',"你好早","早安","下午好","午安","晚上好","您好", "hi"
]

db_gen_query = [
    '请问','想问','问一下','ask'
]

db_purchase = [
    'buy', '我要买'
]

db_indicate_plan = [
    'plana', 'planb', 'plan a', 'plan b'
]

db_goodbye = [
    '再见','bye','goodbye'
]

r_greetings = [
    '你好！','你好!!!!','Hello！',
]

r_query = [
    'YOu have enquired!','Our products costs very little!','YAY'
]

r_goodbye = [
    '再见!!','Byebye!','Hope to see you again! :)'
]

random_chat = [
    "多说一点！",
    "为什么你那么认为？"
]

SUB_LIST = [
    ".",
    ",",
    "!",
    " ",
    "，",
    "。",
    "！",
]

weather_today = "乌云密布"

DEFAULT_CONFUSED = "不好意思，我听不懂"

REPLY_DATABASE = {
    'greet':   r_greetings,
    'sale_query': r_query,
    'goodbye': r_goodbye,
}

UNIVERSAL_INTENTS = {
    INTENTS['greet']: 'greet'
}

MASTER_INTENT_LIST = [
    (INTENTS['greet'],db_greetings),
    (INTENTS['affirm'],db_affirm),
    (INTENTS['deny'],db_deny),
    (INTENTS['indicate_plan'],db_indicate_plan),
    (INTENTS['purchase'],db_purchase),
    (INTENTS['gen_query'],db_gen_query),
    (INTENTS['goodbye'],db_goodbye),
]


### POLICIES ###
POLICY_RULES = {
    (STATES['init'], INTENTS['greet']): (STATES['confirm_query'], SALES_PITCH),
    (STATES['init'], INTENTS['gen_query']) : (STATES['confirm_query'], "您要问什么呢？"),
    (STATES['init'], INTENTS['sales_query']) : (STATES['sales_query'], "好的，那么我就跟亲介绍一下"),
    (STATES['init'], INTENTS['purchase']): (STATES['init_sale'], "Ok. Would you like to see our plans?"),
    (STATES['init'], INTENTS['payment_query']): (STATES['payment_query'], "好的，那么"),
    (STATES['init'], INTENTS['goodbye']): (STATES['goodbye'], "BYE BYE"),
    (STATES['sales_query'], INTENTS['purchase']): (STATES['payment_query'], "好的，那么"),
    (STATES['sales_query'], INTENTS['goodbye']): (STATES['goodbye'], "WHY SIA"),
    (STATES['init_sale'], INTENTS['affirm']): (STATES['choose_plan'], "Please choose a plan: Plan A or Plan B"),
    (STATES['choose_plan'], INTENTS['affirm']): (STATES['choose_plan'], "Great! But you still have to choose a plan."),
    (STATES['choose_plan'], INTENTS['indicate_plan']): (STATES['confirm_plan'], "Just to confirm, your plan is XXX."),
    (STATES['confirm_plan'], INTENTS['affirm']): (STATES['payment'], "That will be $100!"),
    (STATES['payment'], INTENTS['affirm']): (STATES['finish_sale'], "Success! Thank you for using SHEBAO!"),
    (STATES['finish_sale'], INTENTS['goodbye']): (STATES['goodbye'], "Bye! Hope to see you again soon!"),
    (STATES['sales_query'], INTENTS['goodbye']): (STATES['goodbye'], "WHY SIA"),
    (STATES['goodbye'], INTENTS['goodbye']): (STATES['goodbye'],"You already said bye")
}

# Returns state and reply key
def check_policies(curr_state, intent):
    key = (curr_state,intent)
    if key in POLICY_RULES:
        return POLICY_RULES[key]
    if intent in UNIVERSAL_INTENTS:
        rep_key = UNIVERSAL_INTENTS[intent]
        return (curr_state,rep_key)
    return False

### GENERAL ###
# Removes characters
def format_text(text):
    text = text.lower()
    for character in SUB_LIST:
        text = text.replace(character,"")
    return text

# Returns an intent
def get_intent(msg):
    for intent_db in MASTER_INTENT_LIST:
        intent = intent_db[0]
        regex_db = intent_db[1]
        if check_input_db(msg,regex_db):
            return intent
    return False

# Overall function
def message_to_intent(msg):
    p_msg = format_text(msg)
    # print("pmsg: <"+p_msg+">")
    intent = get_intent(p_msg)
    return intent

### INTENT ###
# Checks message for db keywords
def check_input_db(msg, db):
    match = False
    for keyword in db:
        match = re.search(keyword,msg)
        if match:
            break
    return match


### REPLIES ###
# Wrapper first. Add functions later
def intent_to_reply(state, intent):
    s_r = check_policies(state,intent)
    if not s_r:
        return (state, False)

    return s_r


def rand_response(response_list):
    return random.choice(response_list)

def get_reply_list(rkey):
    reply_list = REPLY_DATABASE[rkey]
    return reply_list

def generate_reply(reply_key):
    if not reply_key:
        return DEFAULT_CONFUSED

    # Temporary
    return reply_key

    r_list = get_reply_list(reply_key)
    replytext = rand_response(r_list)
    return replytext

class Chat:
    def __init__(self,user,convo_history):
        self.user = user
        self.state = STATES['init']
        self.convo_history = convo_history

    def change_state(self,new_state):
        self.state = new_state

    def get_state(self):
        return self.state

    def reply_to_msg(self, msg):
        intent = message_to_intent(msg)
        # print("intent",intent)
        new_state, reply_key = intent_to_reply(self.state, intent)
        reply = generate_reply(reply_key)
        # reply = reply_key
        self.change_state(new_state)
        return reply

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


def initiate_bot():
    thischat = Chat("Me", {})
    print("Hello, I am a bot!")
    while True:
        msg = input()
        reply = thischat.reply_to_msg(msg)
        print(reply)

if __name__ == "__main__":
    print("Initializing...")
    initiate_bot()