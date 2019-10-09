# All Chat related Classes

import re
import random
import cbsv
import string
import os
from datetime import datetime
from chatbot_supp import *

DEBUG = 1

# A conversation thread manager using stack and dict
class StateThreader():
    def __init__(self, default_state):
        self.default_state = default_state
        self.threadstack = [] # A stack of threads
        self.threadmap = {}
        self.curr_threadID = ""
        self.curr_thread = ""
        self.spawn_thread(default_state, threadID = "BASE") # Spawn base thread

    def _get_thread(self, state):
        return state["thread"]
    
    def spawn_thread(self, start_state = -1, threadID = "DEFAULT"):
        if isinstance(start_state, int):
            raise Exception("Tried to spawn thread but no start state provided")
        newthread = ConvoThread(start_state)
        self.threadstack.append(newthread)
        self.threadmap[threadID] = newthread
        self.curr_threadID = threadID
        self.curr_thread = self.threadstack[-1]
    
    def get_curr_thread_state(self):
        state = self.curr_thread.get_curr_state()
        if isinstance(state, SIP):
            raise Exception("SIP DETECTED{}".format(state.toString()))
        return state

    def exit_thread(self):
        if len(self.threadstack) > 1:
            self.threadstack.pop(-1)
            self.curr_thread = self.threadstack[-1]

    def switch_thread_to(self, threadID):
        switcher = self.threadmap[threadID]
        self.curr_threadID = threadID
        self.threadstack.remove(switcher)
        self.threadstack.append(switcher)
        return

    def update_state(self, new_state):
        def need_switch_thread(threadID):
            return not (threadID == "NONE" or threadID == self.curr_threadID)
        
        # How to decide if spawn a new thread? or kill old one?
        ns_threadID = self._get_thread(new_state)

        if need_switch_thread(ns_threadID):
            if ns_threadID in self.threadmap:
                self.switch_thread_to(ns_threadID)
            else:
                self.spawn_thread(new_state, ns_threadID)
        
        self.curr_thread.update_state(new_state)

    def set_thread_pending(self, hs, ps):
        self.curr_thread.set_pending_state(hs,ps)

    # If has pending, returns pending
    # If nothing pending, returns given_next_state
    def move_forward(self, given_next_state):
        print("Moving forward...")
        if self.curr_thread.has_pending_state():
            self.curr_thread.unlock_pending_state()
        else:
            self.update_state(given_next_state)
        return self.get_curr_thread_state()

# A conversation thread
# Tracks state
class ConvoThread:
    def __init__(self, initial_state):
        self.curr_state = initial_state
        self.pend_state = None
        self.state_history = [self.curr_state]
        self.required_info = []

    def _is_same_state(self, ns):
        return ns == self.curr_state

    def update_state(self, new_state):
        if not self._is_same_state(new_state):
            self.state_history.append(self.curr_state)
            self.curr_state = new_state
        return

    def get_prev_state(self):
        return self.state_history[-1]

    def get_curr_state(self):
        return self.curr_state

    def has_pending_state(self):
        return not self.pend_state == None
    
    def get_pending_state(self):
        return self.pend_state
    
    def _clear_pending(self):
        self.pend_state = None

    def set_pending_state(self, holdstate, pstate):
        if self.has_pending_state():
            if DEBUG: print("ConvoThread already has pending:{} new:{}".format(self.get_pending_state(), pstate))
            return
        if DEBUG: print("Setting pending state:",pstate)
        self.pend_state = pstate
        self.update_state(holdstate)
        return

    def unlock_pending_state(self):
        if not self.has_pending_state():
            # raise Exception("No pending to unlock!")
            return
        self.update_state(self.get_pending_state())
        self._clear_pending()
        return

# Coordinates everything about a chat
class ChatManager:
    def __init__(self, chat, iparser, pkeeper, replygen, dmanager):
        # Internal properties
        self.chat = chat
        self.chatID = self.chat.getID()
        self.samestateflag = False

        # Helper classes
        self.iparser = iparser
        self.pkeeper = pkeeper
        self.replygen = replygen
        self.dmanager = dmanager.clone(self.chatID)
        self.gatekeeper = ReqGatekeeper()
        self.statethreader = StateThreader(pkeeper.GET_INITIAL_STATE())

    def _get_curr_state(self):
        return self.statethreader.get_curr_thread_state()

    def _get_curr_state_key(self):
        return cbsv.getstatekey(self._get_curr_state())
    
    ############### PRIMARY METHOD ###############
    # Takes in a message, returns a text reply.
    def respond_to_message(self, msg):
        print("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~") # For clarity in terminal
        # Parse the message and get an understanding
        full_uds = self._parse_message_overall(msg)

        # Digest and internalize the new info
        self._digest_uds(full_uds)

        # Request a reply text
        intent = full_uds.get_intent()
        reply = self._fetch_reply(intent)

        self._record_messages_in_chat(msg,reply)
        return reply

    # Takes in message text, returns a full understanding
    def _parse_message_overall(self,msg):
        # Inital understanding
        uds = self._fetch_understanding(msg)
        print("Initial UDS:")
        uds.printout()
        self.gatekeeper.scan_SIP(uds.get_sip())

        # Try to mine message details. 
        # This is after gatekeep because gatekeep sets the slots.
        self._parse_message_details(msg)

        return uds
    
    # Process, gatekeep then internalize changes
    # Results in change in chat details and change in state
    def _digest_uds(self, uds):
        sip = uds.get_sip()
        self.samestateflag = False

        # FEATURE NOT IMPLEMENTED
        # if sip.is_go_back():
        #     self.go_back_a_state()
        #     return final_intent

        if sip.is_same_state():
            self.samestateflag = True
            if DEBUG: print("SAME STATE FLAGGED")
            state = self._get_curr_state()
        else:
            state = sip.get_state_obj()
        
        self._gatekeep_state(state)

        return

    # Updates state according to outcome
    def _gatekeep_state(self, nextstate):
        curr_info = self._get_current_info()
        # print("Current info:",curr_info)
        required_slots = self.gatekeeper.try_gate(curr_info)

        passed = (required_slots == []) #TODO fix bad SE

        # Update DM
        self.push_req_slots_to_dm(required_slots)

        # print("sip", sip.toString(), "nextsip", constructed_sip.toString())
        if DEBUG: print("Gate passed:",passed)
        if passed:
            self.move_forward_state(nextstate)

        else:
            # Didnt pass
            constructed_sip = self._make_info_sip(required_slots)
            infostate = constructed_sip.get_state_obj()
            self.statethreader.set_thread_pending(infostate, nextstate)

    # REMOVAL
    def _make_info_sip(self, req_info):
        con_sip = self.pkeeper.make_info_req_sip(req_info)
        return con_sip

    def move_forward_state(self, state):
        self.statethreader.move_forward(state)

    def push_req_slots_to_dm(self, required_slots):
        if len(required_slots) > 0:
            required_info = list(map(lambda x: x[0],required_slots)) # First element
            print("pushinfotodm Reqinfo",required_info)
            info_entry = {"requested_info": required_info}
            self.push_detail_to_dm(info_entry)

    ### Ask Helpers
    # Ask replygen for a reply
    def _fetch_reply(self,intent):
        information = self._get_current_info()
        curr_state = self._get_curr_state()
        ss = self.samestateflag
        print("curr_state", curr_state, "samestate",ss)
        return self.replygen.get_reply(curr_state, intent, ss, information)

    # Asks dmanager for info
    def _get_current_info(self):
        return self.dmanager.fetch_info()

     # Gets the next state according to policy
    def _fetch_understanding(self, msg):
        curr_state_key = self._get_curr_state_key()
        return self.pkeeper.get_understanding(curr_state_key, msg)

    # Asks iparser to parse the message
    def _parse_message_details(self, msg):
        slots = self.gatekeeper.get_slots() # Best is to only look out for what is needed
        details = self.iparser.parse(msg, slots)
        self.push_detail_to_dm(details)
        return

    ### Detail logging
    def push_detail_to_dm(self, d):
        return self.dmanager.log_detail(d)

    ### Chat logging
    def _record_messages_in_chat(self,recv, sent):
        self.chat.record_messages(recv,sent)
    
    def backup_chat(self):
        self.chat.record_to_database()

# Keeps policies
# Also deciphers messages
class PolicyKeeper:
    def __init__(self, policy_rules, intent_dict, state_lib):
        self.POLICY_RULES = policy_rules
        self.INTENT_DICT = intent_dict
        self.STATE_DICT = state_lib

    def GET_INITIAL_STATE(self):
        initstate = self.STATE_DICT['init']
        return initstate

    def make_info_req_sip(self, req_info):
        def set_info(state, info):
            # Alters the state
            assert state["gated"]
            state["req_info"] = req_info

        if len(req_info) < 1:
            raise Exception("Tried to construct reqinfo SIP but required info is empty!")

        ig_state = self.STATE_DICT["TMP_recv_info"].copy()
        set_info(ig_state, req_info)
        out = SIP(ig_state, cs=False)
        return out

    # FUNCTION NOT USED BY ANYONE
    def _get_state_replies(self, statekey):
        if not statekey in self.STATE_DICT:
            raise Exception("No such state as {}".format(statekey))
            return False
        state = self.STATE_DICT[statekey]
        replies = state["replies"]
        return replies

    # Right now just a wrapper for decipher message
    def get_understanding(self, curr_state, msg):
        uds = self.decipher_message(curr_state, msg)
        return uds

    def decipher_message(self,curr_state,msg):
        def get_intent_matchdb(intent):
            if not "matchdb" in intent:
                raise Exception("intent missing matchdb, {}".format(intent))
            return intent["matchdb"]

        # Returns an Understanding minus details
        def uds_from_policies(state, msg):
            print("uds from state:",state)
            policy = self.POLICY_RULES[state]
            # print("policy list intents", policy.get_intents())
            for intent_lst in policy.get_intents():
                for pair in intent_lst:
                    intent, next_sip = pair
                    assert isinstance(next_sip, SIP)
                    keyword_db = get_intent_matchdb(intent)
                    if cbsv.check_input_against_db(msg, keyword_db):
                        return Understanding(intent, next_sip)
            return Understanding.make_null()
        
        uds = uds_from_policies(curr_state,msg)

        return uds

# MANAGES DETAILS (previously held by Chat)
# TODO: Differentiate between contextual chat info and user info?
class DetailManager:
    def __init__(self, info_vault):
        self.vault = info_vault
        self.chat_prov_info = {}
        self.dbr = {"dummy"}
        self.dbrset = False
        self.chatID = "PLACEHOLDER_USERID"

    def set_runner(self, runner):
        self.dbr = runner
        self.dbrset = True

    def _set_chatID(self, chatID):
        self.chatID = chatID

    def log_detail(self, new_info, DEBUG = 0):
        if DEBUG: print("Logging", new_info)
        for d in new_info:
            deet = new_info[d]
            # Check to make sure its not empty
            if not deet == "":
                self.chat_prov_info[d] = new_info[d]

        self.write_info_to_db() #TESTING
        return

    # Info without vault
    def get_user_info(self):
        not_user_info = ["requested_info", "paile","拍了"] #TODO find a proper way to store this info in JSON
        dic = self.chat_prov_info.copy()
        for i in not_user_info:
            if i in dic: 
                dic.pop(i)
        return dic

    # Called to get chat info + vault info
    def fetch_info(self):
        out = {}
        out.update(self.chat_prov_info)

        # Add City info lookup
        if cbsv.CITY() in self.chat_prov_info:
            cityname = self.chat_prov_info[cbsv.CITY()]
            out["city_info"] = self.vault.lookup_city(cityname)
        
        return out

    def check_info_keys(self, k):
        return k in list(self.chat_info.keys())

    def clone(self, chatID):
        # This is called during the creation of a new chat
        if not self.dbrset:
            raise Exception("DatabaseRunner not initalized for DetailManager!")
        clonetrooper = DetailManager(self.vault)
        clonetrooper._set_chatID(chatID)
        clonetrooper.set_runner(self.dbr)
        prev_info = self.dbr.fetch_user_info(chatID)
        clonetrooper.log_detail(prev_info)
        return clonetrooper

    def write_info_to_db(self):
        if not self.dbrset:
            raise Exception("DatabaseRunner not initalized for DetailManager!")
        chatid = self.chatID
        self.dbr.write_to_db(chatid, self.get_user_info())

# Generates reply text based on current state info
class ReplyGenerator:
    def __init__(self, replyDB):
        self.replyDB = replyDB
        self.formatter = string.Formatter()

    # OVERALL METHOD
    def get_reply(self, curr_state, intent, ss, info = -1):
        rdb = self.getreplydb(intent, curr_state, ss)
        infoplus = self._enhance_info(info)
        reply = self.generate_reply_message(rdb, infoplus)
        return reply

    # Formats txts and calculates
    def _enhance_info(self,info):
        enhanced = info.copy()
        if "requested_info" in enhanced:
            rlist = enhanced["requested_info"]
            
            # Crafted message for info gathering
            crafted_msg = ""
            # TODO Have a proper mapping for thisa
            if "city" in rlist:
                crafted_msg = crafted_msg + "您是哪个城市呢？"
            if "首次" in rlist:
                crafted_msg = crafted_msg + "是首次吗？"
            if "拍了" in rlist:
                crafted_msg = crafted_msg + "拍好了吗？"

            enhanced["requested_info"] = crafted_msg
            
            # Message extensions
            if "首次" in enhanced and "city_info" in enhanced:
                # Calculations
                bool_shouci = (enhanced["首次"] == "是首次")
                bool_gongjijin = False
                ci = enhanced["city_info"]
                total = 0
                payment_base = ci["payment"]
                total += payment_base
                calcstr = "{} 应缴纳".format(payment_base)
                svc_fee = ci["svc_fee"]
                total += svc_fee
                calcstr = calcstr + " + " + "{} 服务费".format(svc_fee)
                if bool_shouci:
                    shouci_fee = ci["shouci_fee"]
                    total += shouci_fee
                    calcstr = calcstr + " + " + "{} 开户费".format(shouci_fee)
                if bool_gongjijin:
                    total += 10000

                ci["total_amt"] = total # Hopefully this is a pointer and not a copy

                calcstr = calcstr + " = " + "{}块".format(total)
                ci["calc_str"] = calcstr

                if bool_shouci:
                    ci["首次ext"] = "首次参保额外收取{city_info[shouci_fee]}元开户费".format(**enhanced)
                else:
                    ci["首次ext"] = ""
            
        return enhanced


    def getreplydb(self,intent, curr_state, issamestate):
        def dict_lookup(key, dictionary):
            if key in dictionary:
                return dictionary[key]
            return False

        def get_replylist(obj):
            # print("get replies from obj",obj)
            return obj["replies"]
    
        LOCALDEBUG = 0
        DEBUG = 1 if LOCALDEBUG else 0

        if DEBUG: print("csk", curr_state["key"],curr_state["thread"])

        # <Specific state to state goes here> if needed

        # Decides priority of lookup. 
        # If same state flagged, look at intents first
        # Else look at state based replies
        lookups = [intent, curr_state] if issamestate else [curr_state, intent]

        # Single state
        rdb = []
        for obj in lookups:
            if not obj:
                # This is for when no intent
                continue

            if len(rdb) < 1:
                rdb = get_replylist(obj)
        
        # if DEBUG: print("SS rdb:",rdb)

        if DEBUG: print("rdb:",rdb)

        if LOCALDEBUG: DEBUG = 0
        if len(rdb) < 1:
            rdb = [cbsv.DEFAULT_CONFUSED()] # TODO fix bad OOP

        return rdb

    # Generates a pure reply
    def generate_reply_message(self, rdb, info):
        def rand_response(response_list):
            return random.choice(response_list)

        reply_template = random.choice(rdb)
        if DEBUG: print("template",reply_template)
        final_msg = reply_template
        if isinstance(info, dict):
            if DEBUG: print("Enhanced info:",info)
            
            # Uses kwargs to fill this space
            final_msg = reply_template.format(**info)

        return final_msg

# Deals only with text
# Does not deal with state or information
class Chat:
    def __init__(self,chatID, convo_history = {}):
        self.chatID = chatID
        self.curr_chatlog = {}
        self.convo_history = convo_history
        self.convo_index = 0
        # self.info = {}

    def getID(self):
        return self.chatID

    # Records conversation
    def record_messages(self, recieved, sent):
        dt = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        username = "用户"
        humanify = lambda user, m: dt+ " > " + user + ": " + m
        robotify = lambda x: dt + " > " + "机器人: " + x
        self.curr_chatlog[self.convo_index] = humanify(username, recieved)
        self.curr_chatlog[self.convo_index+1] = robotify(sent)
        self.convo_index = self.convo_index + 2

    ## Commonly called methods
    def pop_prev_msg(self):
        # TODO failsafe when empty?
        # Need to get the previous previous message
        if len(self.prev_messages) < 2:
            return self.prev_messages[-1]
        if self.firstpop: 
            self.prev_messages.pop(-1)
            self.firstpop = False
        return self.prev_messages.pop(-1)

    def set_prev_msg(self, msg):
        if msg == cbsv.DEFAULT_CONFUSED():
            return
        self.prev_messages.append(msg)
        self.firstpop = True
    
    # def recv_info_dump(self, new_info):
    #     print("Recieved info dump...",new_info)
    #     self.info.update(new_info)

    ## Database interaction?
    def get_previous_issues(self):
        return self.user.get_issues()

    # Writes to a file eventually
    def record_to_database(self):
        direct = os.getcwd()
        if not os.path.isdir(os.path.join(direct,"chatlogs")):
            if DEBUG: print("Creating chatlogs folder...")
            os.mkdir(os.path.join(direct,"chatlogs")) # If no folder, make a folder
        filepath = os.path.join(direct,"chatlogs/" + self.chatID + ".json")
      
        # write chatlog
        cbsv.dump_to_json(filepath,self.get_chatlog(),1)
        return

    def get_chatlog(self):
        return self.curr_chatlog