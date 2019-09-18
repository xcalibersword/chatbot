# All Chat related Classes
import re
import random
import cbsv
import string
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
        self.state = cbsv.INITAL_STATE()
        self.chat = chat
        self.iparser = iparser
        self.pkeeper = pkeeper
        self.replygen = replygen
        self.GATED_STATES = gated_states

        # Internal properties
        self.state_history = [self.state,]
        # self.clear_expect_detail()
        self._clear_pending_state()

    # Big method.
    # Takes in a message, returns a text reply.
    def respond_to_message(self, msg):
        # Parse the message and get an understanding
        full_uds = self._parse_message_overall(msg)

        full_uds.printout()
        # Digest and internalize the new info
        final_uds = self._digest_uds(full_uds)

        # Request a reply text
        reply = self._fetch_reply(final_uds)

        if DEBUG:
            final_uds.printout()
    
        return reply

    # Takes in message text, returns a full understanding
    def _parse_message_overall(self,msg):
        # Inital understanding
        uds = self._fetch_understanding(msg)

        # Add mined details
        deets = self._parse_message_details(msg)
        uds.set_details(deets)

        return uds

    # Gets the next state according to policy
    def _fetch_understanding(self, msg):
        curr_state = self._get_state()
        return self.pkeeper.get_understanding(curr_state, msg)

    def _parse_message_details(self, msg):
        # Adds details
        details = self.iparser.parse(msg)
        return details
    
    # Process, gatekeep then internalize changes
    # Results in change in chat details and change in state
    def _digest_uds(self, uds):
        deets = uds.get_details()
        sip = uds.get_sip()

        # Update details
        self.push_detail_to_chat(deets)

        # Update State (may depend on details so this is 2nd)
        if sip.is_go_back():
            self.go_back_a_state()
            return uds

  
        
        # Modify if needed
        new_sip = self._gatekeep_sip(sip)

        self._update_state_from_sip(new_sip)

        if new_sip.is_same_state():
            return uds

        # Modified copy of original
        final_uds = uds.copy_swap_sip(new_sip)
        return final_uds

    # Ask replygen for a reply
    def _fetch_reply(self,uds):
        information = self.chat.get_all_info()
        curr_state = self._get_state()
        intent = uds.get_intent()
        prev_state = self.get_prev_state()
        return self.replygen.get_reply(prev_state, curr_state, intent, information)

    # Returns the next uds. Final
    def _gatekeep_sip(self, sip):
        curr_info = self.chat.check_info_keys()
        passed, next_sip = sip.try_gate(curr_info)
        if passed:
            return self.move_state_forward(sip)

        else:
            self.set_pending_state(sip)
            return next_sip   # Return the custom made info state

    def _has_pending_state(self):
        return not self.pending_state == ""

    def _clear_pending_state(self):
        self.pending_state = ""

    def set_pending_state(self, pstate):
        self.pending_state = pstate

    def move_state_forward(self, sip):
        # If pending, return pending state
        if self._has_pending_state():
            sipval = self.pending_state
            self._clear_pending_state()
            return sipval
        return sip

    ## Internal State management
    def _change_state(self,new_state):
        if DEBUG: print("changing to", new_state)
        if self.state == new_state:
            print("Eh why same state", new_state)
        self.state_history.append(self.state)
        self.state = new_state

    def _update_state_from_sip(self, sip):
        new_state = sip.get_state_key()
        self._change_state(new_state)
        
        print("Updating from this sip",sip.toString())
        required_info = {"requested_info":sip.get_requirements()}
        self.push_detail_to_chat(required_info)
        return

    def go_back_a_state(self):
        prev_state = self.state_history.pop(-1)
        
    def _get_state(self):
        return self.state

    def get_prev_state(self):
        return self.state_history[-1]

    ## Detail stuff
    # Bool
    def push_detail_to_chat(self, d):
        return self.chat.log_details(d,1)

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
            return Understanding.make_null()
        
        uds = uds_from_policies(curr_state,msg)

        return uds

# Generates reply text based on current state info
class ReplyGenerator:
    def __init__(self, replyDB, rkey_dbs):
        self.replyDB = replyDB
        self.rkey_dbs = rkey_dbs
        self.formatter = string.Formatter()

    # OVERALL METHOD
    def get_reply(self, prev_state, curr_state, intent, info = -1):
        rkey = self.getreplykey(prev_state, intent, curr_state)
        reply = self.generate_reply_message(rkey, info)
        return reply

    def getreplykey(self,prev_state, intent, curr_state):
        def dict_lookup(key, dictionary):
            if key in dictionary:
                return dictionary[key]
            return False

        context = (prev_state, curr_state)
        print("prev state, nxt state",context)
        
        # Specific state to state
        rkey = dict_lookup(context, self.rkey_dbs["s2s"])
        if rkey:
            print("found in s2s")
            return rkey

        # Single state
        if not rkey:
            print("found in 1s")
            rkey = dict_lookup(curr_state, self.rkey_dbs["ss"])
        
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
            r_list = self.replyDB[r_key]["text"]
            replytext = rand_response(r_list)
            return replytext
        return r_key

    # Generates a pure reply
    def generate_reply_message(self, reply_key, info):
        reply_template = self.fetch_reply_text(reply_key)
        print("template",reply_template)
        final_msg = reply_template
        if isinstance(info, dict):
            print("current info",info)
            ikeys = list(info.keys())
            # final_msg = self.formatter.vformat(reply_template, ikeys, info)
            # final_msg = reply_template%(info)
            final_msg = reply_template.format(**info)

        return final_msg


# Deals only with text and info (city, date)
# Does not deal with state
class Chat:
    def __init__(self,customer, convo_history = {}):
        self.customer = customer
        self.curr_chatlog = []
        self.convo_history = convo_history
        self.info = {}

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
    
    # Returns a list of keys from the info dict
    def check_info_keys(self):
        return list(self.info.keys())

    # Check if info dict has this key
    def has_info(self, key):
        return key in self.info
    
    def get_all_info(self):
        return self.info

    # Add info to the current dict
    def log_details(self, new_info, DEBUG = 0):
        if DEBUG: print("Logging", new_info)
        for d in new_info:
            deet = new_info[d]
            # Check to make sure its not empty
            if len(deet) > 0:
                self.info[d] = new_info[d]
            
        return

    ## Database interaction?
    def get_previous_issues(self):
        return self.user.get_issues()

    # Writes to a file eventually
    def record_to_database(self):
        # filepath = dir + UNIQUE_ID
        # write info
        
        # write issues

        return