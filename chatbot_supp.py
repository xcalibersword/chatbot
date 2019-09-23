import cbsv
import re

DEBUG = 1


# Have a message class? Or some sort of flag for messages. Indicate state-changing messages.
PREV_STATE_F = {"key":"299 PREV_STATE", "gated": False}
PENDING_STATE_F = {"key":"PENDING_STATE", "gated": False}
SAME_STATE_F = {"key":"same_state","gated":False}

# SIP = State Info Packet
# A packet that has info about state and has constructors for set states like go_back
class SIP:
    def __init__(self, state, cs = True, pocket_state = False):
        self.parse_state(state)
        self.state_change = cs
        self.backtrack = False
        self.go_back = False
        self.pocket_state = pocket_state

    def parse_state(self, state):
        self.state_obj = state
        self.state_key = state["key"]
        self.gated_bool = state["gated"]
        self.state_reqs = ""
        if state["gated"]: self.state_reqs = state["req_info"]
        self.pending_state = ""

    def set_backtrack(self):
        self.backtrack = True

    def set_actions(self, action, pending_act = None):
        self.action = action
        self.pending_act = pending_act

    def get_state_key(self):
        return self.state_key
    
    def get_state_obj(self):
        return self.state_obj

    def is_gated(self):
        return self.gated_bool

    # Returns a list of requirements
    def get_requirements(self):
        return self.state_reqs

    # If pass, returns True, (Pending state)
    # If fail, returns False, (Next state)
    def try_gate(self, info):
        print("Trying gate with info:",info, "required:",self.state_reqs)
        if not self.is_gated():
            return (True, SIP.goto_pending_state())

        failed_reqs = self.state_reqs
        for i in info:
            if i in failed_reqs:
                failed_reqs.remove(i)
        
        if DEBUG: print("failed gate reqs:",failed_reqs)
        if len(failed_reqs) > 0:
            collect_SIP = self.build_info_SIP(failed_reqs)
            return (False, collect_SIP)

        return (True, SIP.goto_pending_state())

    @classmethod
    def same_state(cls):
        obj = cls(SAME_STATE_F, cs=False)
        return obj
 
    @classmethod
    def go_back_state(cls):
        obj = cls(PREV_STATE_F, cs=False)
        obj.set_backtrack()
        obj.go_back = True
        return obj
    
    @classmethod
    def goto_pending_state(cls):
         obj = cls(PENDING_STATE_F, cs=False)
         return obj

    def is_same_state(self):
        return not self.state_change

    def is_pocket_state(self):
        return self.pocket_state

    # For cases when a state requires some intermediate step
    # Once the current stage is done, we immediately go to the pstate
    # How do we store this pstate?
    @classmethod
    def build_info_SIP(cls, info):
        info_gather_state = {
            "key": cbsv.INFO_GATHER_STATE_KEY(),
            "gated": True,
            "req_info": info
        }
        o = cls(info_gather_state, cs=False)
        return o

    def is_go_back(self):
        return self.go_back == True

    def toString(self):
        return ("State obj",self.state_obj,"cs",self.state_change,"backtrack ",self.backtrack," reqs ",self.state_reqs)

# A vehicle to house SIP, intent and details.
# TODO: Clean up usages of Understanding
class Understanding:
    def __init__(self, intent, sip):
        self.intent = intent
        self.sip = sip
        self.details = {}

    @classmethod
    def make_null(cls):
        n = cls(False, SIP.same_state())
        return n

    def set_details(self, d):
        self.details = d
    
    def get_details(self):
        return self.details

    def get_intent(self):
        return self.intent

    def copy_swap_sip(self,new_sip):
        new = Understanding(self.intent, new_sip)
        new.set_details(self.get_details())
        return new

    def get_sip(self):
        return self.sip

    def set_intent(self, i):
        self.intent = i

    def printout(self):
        print("UNDERSTANDING PRINTOUT: Intent: ",self.intent, " SIP: ", self.sip.toString(), " details: ", self.details)

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

    def get_intents(self):
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

# Globally accessed object. Singleton but not really cuz it needs to be initalized
class InfoVault():
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

# Takes in a message and returns some info (if any)
# Thing to note about re.search is that only the first match is pulled.
class InfoParser():
    def __init__(self, json_dict):
        self.cities = json_dict["cities"]
        self.payments = json_dict["payments"]
        self.digits = cbsv.DIGITS()

        self.ctlist = self.list_to_regexList(self.cities)
        self.paymnt_list = self.list_to_regexList(self.payments)

    # Returns a dict of info
    def parse(self, text):
        out = {}
        city = {"city":self.parse_city(text)}
        date = {"dates":self.parse_date(text)}
        payment = {"payment_method":self.parse_payment(text)}
        out.update(city)
        out.update(date)
        out.update(payment)

        return out

    def list_to_regexList(self, lst):
        re_list = ""
        for e in lst:
            re_list = re_list + e + "|"
        re_list = re_list[:-1] # Remove last char "|"
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

        return out

    def parse_payment(self, text):
        out = ""
        m_pay = re.search(self.paymnt_list,text)
        if m_pay:
            out = m_pay.group(0)
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