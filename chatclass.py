# All Chat related Classes
import re
import random
import cbsv
from chatbot_supp import *

# The problem of gated states.
# Some states need certain things in order to proceed. E.g.
# Quotation: Needs location
# Payment: Needs payment details?

# Controls state and details
# Gatekeeps for states
# STATE MANAGER
class ChatManager:
    def __init__(self, chat, iparser, pkeeper, replygen, gated_states):
        self.chat = chat
        self.iparser = iparser
        self.pkeeper = pkeeper
        self.replygen = replygen
        self.GATED_STATES = gated_states
        self.state_history = []

    # Big method.
    # Takes in a message, returns a text reply.
    def respond_to_message(self, msg):

        uds = self.parse_message_overall(msg)


        if DEBUG:
            print("Intent is:{0}, Next state is {1}".format(uds.intent, uds.sip.get_state()))
    
    # Takes in message text, returns 
    def parse_message_overal(self,msg):

        # Inital understanding
        uds = self.fetch_understanding(msg)

        # Add mined details
        deets = self.parse_message_details(msg)
        uds.set_details(deets)

        return uds

    def parse_message_details(self, msg):
        # Adds details
        details = self.iparser.parse(msg)
        return details

    # Returns the next state. Final
    def decide_next_state(self, uds):
        if pending_req_satisfied():
            return self.pending_state

        if self.is_expecting_detail():
            pass

        next_state = self.fetch_next_policy_state()
        # Check gate
        if next_state in self.GATED_STATES:
            requirement = self.GATED_STATES[next_state]

        return next_state

    # Gets the next state according to policy
    def fetch_understanding(self,msg):
        curr_state = self.chat.get_state()
        return self.pkeeper.get_understanding(curr_state, msg)

     # Updates chat info
    def update_chat_state(self, sip):
        if sip.is_go_back():
            self.go_back()

        elif sip.is_same_state():
            return
        
        new_state = sip.get_state()
        self.change_state(new_state)

    ## Internal State management
    def set_pending_state(self, pstate):
        self.pending_state = pstate

    def change_state(self,new_state):
        if DEBUG: print("changing to", new_state)
        self.state_history.append(self.state)
        self.state = new_state
        self.first_state_pop = True

    def go_back_a_state(self):
        prev_state = state_history.pop(-1)
        chat.set_state(prev_state)


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
    
    def push_detail_to_chat(self, d):
        return self.chat.log_detail(d)



# Keeps policies
# Also deciphers messages
class PolicyKeeper:
    def __init__(self, policy_rules, intent_table):
        self.POLICY_RULES = policy_rules
        self.INTENT_LOOKUP_TABLE = intent_table

    def get_understanding(self, curr_state, msg):
        uds = self.decipher_message(curr_state, msg)

        return uds

    def decipher_message(self,curr_state,msg):
        # Returns an Understanding minus details
        def uds_from_policies(state, msg):
            policy = self.POLICY_RULES[state]
            for in_lst in policy.get_intents():
                for pair in in_lst:
                    intent, next_sip = pair
                    assert isinstance(next_sip, SIP)
                    keyword_db = self.INTENT_LOOKUP_TABLE[intent]
                    if cbsv.check_input_against_db(msg, keyword_db):
                        return Understanding(intent, next_sip)
            return Understanding(False, SIP.same_state())
        
        f_msg = format_text(msg)
        uds = uds_from_policies(curr_state,f_msg)

        return uds

# Generates reply text based on current state info
class ReplyGenerator:
    def __init__(self, replyDB, rkey_dbs):
        self.replyDB = replyDB
        self.rkey_dbs = rkey_db

    # OVERALL METHOD
    def get_reply(self, curr_state, intent, next_state, info = -1):
        rkey = self.getreplykey(curr_state, intent, next_state)
        reply = generate_reply_message(rkey, info)
        return reply

    def getreplykey(self,curr_state, intent, next_state):
        def dict_lookup(key, dictionary):
            if key in dictionary:
                return dictionary[key]
            return False

        context = (curr_state, next_state)
        print("cstate, nstate",context)
        
        # Specific state to state
        rkey = dict_lookup(context, self.rkey_dbs["s2s"])
        
        # Single state
        if not rkey:
            rkey = dict_lookup(next_state, self.rkey_dbs["ss"])
        
        # Intent
        if not rkey:
            rkey = dict_lookup(intent, self.rkey_dbs["intent"])

        return rkey

    def fetch_reply_text(self,r_key):
        def rand_response(response_list):
            return random.choice(response_list)

        if not r_key:
            return cbsv.DEFAULT_CONFUSED()
        if r_key in self.replyDB:
            r_list = self.replyDB[r_key]
            replytext = rand_response(r_list)
            return replytext
        return r_key

    # Generates a pure reply
    def generate_reply_message(self, reply_key, info):
        reply_template = self.lookup_reply_DB(reply_key)
        final_msg = reply_template
        if isinstance(info, dict):
            print("current info",info)
            final_msg = reply_template.format(info)

        return final_msg


# Deals only with text and info (city, date)
class Chat:
    def __init__(self,customer,convo_history,initial_state):
        self.customer = customer
        self.state = initial_state
        self.chatlog = []
        self.convo_history = convo_history
        self.prev_messages = []
        self.frame_history = [initial_state,]
        self.info = {}
        self._has_info = False
        self.bool_expecting_detail = False

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
        # filepath = dir + UNIQUE_ID
        # write info
        
        # write issues

        return