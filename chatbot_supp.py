import cbsv
import re

DEBUG = 1


# Have a message class? Or some sort of flag for messages. Indicate state-changing messages.


PREV_STATE_F = "299 PREV_STATE"
PREV_STATE_MSG = "prev_state_msg"

# A packet that has info about state and has constructors for set states like go_back
# State Info Packet
class SIP:
    def __init__(self, state, cs = True):
        self.state = state
        self.state_change = cs
        self.backtrack = False
        self.go_back = False

    def set_backtrack(self):
        self.backtrack = True

    def set_actions(self, action, pending_act = None):
        self.action = action
        self.pending_act = pending_act

    def get_state(self):
        return self.state

    @classmethod
    def same_state(cls):
        obj = cls("same_state", cs=False)
        return obj
 
    @classmethod
    def go_back_state(cls):
        obj = cls(PREV_STATE_F, cs=False)
        obj.set_backtrack()
        obj.go_back = True
        return obj

    def is_same_state(self):
        return not self.state_change

    # For cases when a state requires some intermediate step
    # Once the current stage is done, we immediately go to the pstate
    # How do we store this pstate?
    def set_pending_state(self,nstate, pstate):
        self.pstate = pstate
        self.state = nstate


    def is_go_back(self):
        return self.go_back == True

    def toString(self):
        return ("State",self.state,"cs",self.state_change,"backtrack",self.backtrack)

# A vehicle to house intent and details from the message
class Understanding:
    def __init__(self, intent, sip):
        self.intent = intent
        self.sip = sip
        self.details = {}

    def set_details(self, d):
        self.details = d
    
    def get_details(self):
        return self.details

    def get_intent(self):
        return self.intent
    
    def get_sip(self):
        return self.sip

    def set_intent(self, i):
        self.intent = i

    def printout(self):
        print("Intent",self.intent, "SIP", self.sip.toString(), "details", self.details)

# Action that includes string for replies
class Action:
    def __init__(self):
        self.message = ""
        self.log_data_bool = False
        self.data = []

    @classmethod
    def reply(cls, msg):
        act = cls()
        act.set_message(msg)
        return act
    
    @classmethod
    def go_back(cls, prev_msg):
        act = cls()
        act.message = msg
        return act

    def set_message(self, msg):
        self.message = msg

    def log_data(self, data):
        self.data = data
        self.log_data_bool = True
    
    def has_data(self):
        return self.log_data_bool

    def set_details(self, d):
        self.details = d
        

# A product???
class Product:
    def __init__(self, name, info):
        self.name = name
        self.parse_info(info)

    # info is in the form of a dict
    def parse_info(self, info):
        self.price = info["price"]
        self.desc = info["desc"]

# Try to have stateful changes
# frame = (state, message)
class Chat:
    def __init__(self,customer,convo_history,initial_state):
        self.customer = customer
        self.state = initial_state
        self.convo_history = convo_history
        self.prev_messages = []
        self.frame_history = [initial_state,]
        self.info = {}
        self._has_info = False
        self.bool_expecting_detail = False

    ## Commonly called methods
    # Updates chat info
    def update_chat(self, sip, selection):
        if not isinstance(selection,int):
            self.set_selection(selection)

        if sip.is_go_back():
            self.go_back()

        elif sip.is_same_state():
            return
        
        new_state = sip.get_state()
        self.change_state(new_state)

    def pop_prev_msg(self):
        # TODO failsafe when empty?
        # Need to get the previous previous message
        if len(self.prev_messages) < 2:
            return self.prev_messages[-1]
        if self.firstpop: 
            self.prev_messages.pop(-1)
            self.firstpop = False
        return self.prev_messages.pop(-1)
    
    # Internal methods
    def change_state(self,new_state):
        if DEBUG: print("changing to", new_state)
        self.frame_history.append(self.state)
        self.state = new_state
        self.first_state_pop = True

    def set_prev_msg(self, msg):
        if msg == cbsv.DEFAULT_CONFUSED():
            return
        self.prev_messages.append(msg)
        self.firstpop = True
    
    def get_state(self):
        return self.state

    def get_prev_state(self):
        if len(self.frame_history) < 1:
            return frame_history[-1]
        #     self.first_state_pop = False
        #     self.frame_history.pop(-1)
        return self.frame_history.pop(-1)

    # Check if info dict has this key
    def has_info(self, key):
        return key in self.info
    
    def get_info(self, key):
        return self.info[key]

    ## Detail stuff
    # Bool
    def is_expecting_detail(self):
        return self.bool_expecting_detail

    # Set the key to listen out for
    def set_expect_detail(self, detail):
        self.bool_expecting_detail = True
        self.req_detail = detail
    
    def clear_expect_detail(self):
        self.bool_expecting_detail = False
        self.req_detail = ""

    # Getter
    def get_req_detail(self):
        return self.req_detail

    # Add info to the current db
    def log_detail(self, info):
        rd = self.get_req_detail()
        if rd in info:
            deet = info[rd]
            if len(deet) > 0:
                self.info[rd] = info[rd]
                self.clear_expect_detail()
                return True
        return False

    ## Database interaction?
    def get_previous_issues(self):
        return self.user.get_issues()

    def record_to_database(self):
        # write info
        
        # write issues

        return

    def go_back(self):
        print("going back")
 

    # Pending State
    def set_pending_state(self, state):
        self.pending_state = state

class Policy():
    def __init__(self, g_intents, s_intents = []):
        # self.state_name = state_name
        self.g_intents = g_intents
        self.s_intents = s_intents

    def get_g_intents(self):
        return self.g_intents
    def get_s_intents(self):
        print("s_intents", s_intents)
        return self.s_intents

    def get_policies(self):
        return [self.s_intents, self.g_intents]

CITIES = cbsv.CHINA_CITIES()
class Customer:
    def __init__(self, userID, accounts = -1, issues = -1):
        self.userID = userID
        self.city = ""
        self.start_date = ""
        if isinstance(issues,int): 
            self.accounts = [] 
        else: 
            self.accounts = accounts
        if isinstance(issues,int):
            self.issues_list = []
        else:
            self.issues_list = issues
        
    def record_city(self,city):
        assert city in CITIES
        self.city = city

    def add_issue(self, issue):
        self.issues_list.append(issue)
        # Check for duplicates?

    def get_issues(self):
        return self.issues_list

    def get_accounts(self):
        return self.accounts

# Takes in a message and returns some info (if any)
class Info_Parser():
    cities = ["上海","北京","深圳","杭州","广州", "上海", "成都", "shanghai", "beijing"]
    digits = "[零一二三四五六七八九十|0-9]"
    def __init__(self):
        self.ctlist = self.list_to_reList(self.cities)

    # Returns a dict of info
    def parse(self, text):
        empty = {"city":"", "dates":""}
        city = self.parse_city(text)
        date = self.parse_date(text)
        out = {"city":city, "dates":date}
        if not out == empty: print(out)
        return out

    def list_to_reList(self, lst):
        re_list = ""
        for e in lst:
            re_list = re_list + e + "|"
        re_list = re_list[:-1] # Remove last char

        return re_list

    def parse_date(self, text):
        # Returns a "" if not found
        def date_re_search(keyword):
            result = ""
            # "[^ ]+(?=日)"
            search_terms = self.digits + "+(?=" + keyword + ")"
            m = re.search(search_terms,text)
            if m:
                result = m.group(0)
            return result
        
        day = date_re_search("日")
        mth = date_re_search("月")
        yr = date_re_search("年")

        out = (day, mth, yr)
        return out

    def parse_city(self, text):
        out = ""
        m_city = re.search(self.ctlist,text)
        if m_city:
            out = m_city.group(0)

    #     for i in range(len(text)):
    #         substring = text[i:i+1]
    #         if substring in cities:
    #             return substring
        return out

    def cn_to_integer(self, digit):
        SHI = "十"
        zw_num = ['零','一','二','三','四','五','六','七','八','九']
        conv = digit
        for i in range(len(zw_num)):
            conv.replace(zw_num,i)
        if SHI in digit:
            return digit.index(SHI)
        return conv