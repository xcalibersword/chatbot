import cbsv
import re
import chatbot_utils as cu

DEBUG = 1

# Have a message class? Or some sort of flag for messages. Indicate state-changing messages.
PREV_STATE_F = {"key":"299 PREV_STATE", "gated": False}
# PENDING_STATE_F = {"key":"PENDING_STATE", "gated": False}
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
        self.state_obj = state.copy() # states are dicts
        self.state_key = self.state_obj["key"]
        self.gated_bool = self.state_obj["gated"]
        self.state_slots = self.state_obj["req_info"] if self.state_obj["gated"] else []
        self.pending_state = ""

    def set_actions(self, action, pending_act = None):
        self.action = action
        self.pending_act = pending_act

    def get_state_key(self):
        return self.state_key
    
    def get_state_obj(self):
        return self.state_obj

    def is_gated(self):
        return self.gated_bool

    # Returns a list of lists [name, type]
    def get_slots(self):
        return self.state_slots.copy()

    def get_reqs(self):
        return ReqGatekeeper.slots_to_reqs(self.state_slots)    

    @classmethod
    def same_state(cls):
        obj = cls(SAME_STATE_F, cs=False)
        return obj
    
    @classmethod
    def exit_pocket(cls):
        # TODO this
        obj = cls(PREV_STATE_F, cs=False)
        return obj

    def is_same_state(self):
        return not self.state_change

    def is_pocket_state(self):
        return self.pocket_state

    def is_go_back(self):
        return self.go_back == True

    def toString(self):
        return ("State key",self.state_key,"cs",self.state_change, "slots",self.state_slots)

# A vehicle to house SIP and intent.
class Understanding:
    def __init__(self, intent, sip):
        self.intent = intent
        self.sip = sip
        self.details = {}

    @classmethod
    def make_null(cls):
        n = cls(cbsv.NO_INTENT(), SIP.same_state())
        return n

    def get_intent(self):
        return self.intent

    def get_sip(self):
        return self.sip
    
    def get_sip_slots(self):
        return self.sip.get_slots()

    def printout(self):
        print("UNDERSTANDING PRINTOUT: Intent: ", self.intent, " SIP: ", self.sip.toString())

class ReqGatekeeper:
    def __init__(self, conds):
        self.requirements = []
        self.slots = []
        self.gate_closed = False
        self.conds = conds

    def open_gate(self):
        self.gate_closed = False
        self.slots = []
        self.requirements = []

    def close_gate(self):
        self.gate_closed = True

    def get_slots(self):        
        return self.slots.copy()

    def is_gated(self):
        return self.gate_closed

    def _add_cond_reqs(self, info):
        # Additional reqs
        for detail, conditions in self.conds.items():
            fetch = cu.dive_for_values([detail,],info,DEBUG=1)
            if len(fetch) > 0:
                for c in conditions:
                    val, slots_list = c
                    fetched = list(fetch.values())
                    print("f,fval,val",fetch, fetched,val) 
                    if fetched[0] == val:
                        for slot in slots_list:
                            if not slot[0] in list(map(lambda x: x[0],self.slots)):
                                print("Updating slots...", slot)
                                self.slots.append(slot)
                        break

    @classmethod
    def slots_to_reqs(cls, slots):
        def getname(s):
            return s[0]
        reqlist = []
        for slot in slots.copy():
            reqlist.append(getname(slot))
        if DEBUG: print("get_requirements returning", reqlist)
        return reqlist  

    def get_requirements(self):
        return self.requirements.copy()

    def scan_state_obj(self, state_obj):
        if "gated" not in state_obj:
            return

        slots = state_obj['req_info']
        if not state_obj["gated"] or len(slots) < 1:
            return
       
        self.close_gate()
        self.slots = slots
        print("slots from scanning obj:",slots)
        self.requirements = ReqGatekeeper.slots_to_reqs(self.slots)    

    # Unused
    # def scan_SIP(self, sip):
    #     if sip.is_gated():
    #         self.close_gate()
    #         self.slots = sip.get_slots()
    #         self.requirements = ReqGatekeeper.slots_to_reqs(self.slots)    

    # If pass, returns True, (Pending state)
    # If fail, returns False, (Next state)
    def try_gate(self, info):
        if not self.gate_closed:
            return (True, [])

        self._add_cond_reqs(info)
        unfilled_slots = self.get_slots()

        print("Trying gate with info:",info, "required:",self.get_requirements())
        # for catgry in list(info.keys()):
        for s in unfilled_slots.copy():
            detail = s[0]
            if detail in info:
                unfilled_slots.remove(s)
        
        if DEBUG: print("unfilled_slots:",unfilled_slots)
        if len(unfilled_slots) == 0:
            self.open_gate()

        passed = (len(unfilled_slots) == 0)
        return (passed, unfilled_slots)

class Humanizer():
    def __init__(self,human_dict):
        self.hd = human_dict.items()
    
    def humanify(self, msg, info):
        human_msg = msg
        for key, d in self.hd:
            if key in info:
                if info[key] == d["value"]:
                    pos = d["location"]
                    txt = d["text"]
                    if pos == "START":
                        human_msg = txt + human_msg
                    elif pos == "END":
                        human_msg = human_msg + txt
        return human_msg
        

class Policy():
    def __init__(self, g_intents, s_intents = []):
        # self.state_name = state_name
        self.g_intents = g_intents
        self.s_intents = s_intents

    def get_g_intents(self):
        return self.g_intents

    def get_s_intents(self):
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
        if q in self.city_keys:
            return self.lookup_city(q)
        if q in self.other_keys:
            return self.lookup_other(q)
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
        self.digits = cbsv.DIGITS()

        self.regexDB = {}
        self.perm_slots = json_dict["permanent_slots"]
        slots = json_dict["slots"]
        self.zonelist = json_dict["zones"]
        self._build_slots_DB(slots)

    def _build_slots_DB(self, jdata):
        for catkey in list(jdata.keys()):
            self.regexDB[catkey] = {}
            category = jdata[catkey]
            for value in list(category.keys()):
                termlist = category[value]
                regexlist = self.list_to_regexList(termlist)
                self.regexDB[catkey][value] = regexlist

    def _real_parse(self, text, slot, d):
        slotname, catgry = slot
        value = self.get_category_value(text, catgry)
        if len(value) > 0:
            entry = {slotname: value}
            d.update(entry)

    # Returns a dict of info
    def _default_parse(self, text):
        # Default parser
        out = {}
        for ps in self.perm_slots:
            self._real_parse(text, ps, out)
        return out

    # Get the value in the text related to the specified category
    # Enumerated by dictionary key
    # Returns a pure value
    def get_category_value(self, text, category):
        if not category in self.regexDB:
            print("No such category:{}".format(category))
            return {category: ""}
        catDB = self.regexDB[category]
        value = ""
        found = False
        vals = list(catDB.keys())
        for v in vals:
            reDB = catDB[v]
            m = re.search(reDB, text)
            if m:
                if found:
                    print("Double value. Prev:", value, ", Current:",v)
                # token = m.group(0)
                value = v
                found = True
                print("Found a ", category, ":", v)
        
        return value

    # Returns a dict of values
    def parse(self, text, slots):
        out = {}
        out = self._default_parse(text)

        # slotted parse        
        for slot in slots:
            self._real_parse(text, slot, out)

        # Adds on a zone dict to the returned dict
        # E.g. "zones":{"city":"shanghai"}
        for zone in self.zonelist:
            zones_d = {}
            if zone in out:
                zones_d[zone] = out[zone]
        if not zones_d == {}: out["zones"] = zones_d

        return out

    # Converts a python array to a string delimited by the '|' character
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

    @classmethod
    def cn_to_integer(self, msg):
        SHI = "十"
        zw_num = ['零','一','二','三','四','五','六','七','八','九']
        def get_decimal(haoma):
            return str(zw_num.index(haoma))
        output = msg
        j = 0
        for i in range(len(msg)):
            if msg[i] == SHI:
                # Tens digit
                rest = output[j+1:] if j+1 < len(output) else ""
                output = output[:j] + "0" + rest
                
                if not msg[i-1] in zw_num:
                    # If standalone
                    rest = output[j:]
                    output = output[:j] + "1" + rest
                    j+=1
                
                if i+1 < len(msg):
                    # If have ones digit, replace zerp with ones digit
                    if msg[i+1] in zw_num:
                        rest = output[j+1:] if j+1 < len(output) else ""
                        output = output[:j] + rest
            j += 1
        # Mass replace digits
        for haoma in zw_num:
            output = output.replace(haoma, get_decimal(haoma))

        return output

# 八十一

if __name__ == "__main__":
    print("Number Converter On!")
    while 1:
        test = input()
        print("converted:",InfoParser.cn_to_integer(test))