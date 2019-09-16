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
        self.state = cbsv.INITAL_STATE()
        self.chat = chat
        self.iparser = iparser
        self.pkeeper = pkeeper
        self.replygen = replygen
        self.GATED_STATES = gated_states

        # Internal properties
        self.state_history = []
        self.clear_expect_detail()

    # Big method.
    # Takes in a message, returns a text reply.
    def respond_to_message(self, msg):
        # Parse the message and get an understanding
        full_uds = self._parse_message_overall(msg)

        # Digest and internalize the new info
        final_uds = self._digest_uds(full_uds)

        # Request a reply text
        reply = self._fetch_reply(final_uds)

        if DEBUG:
            print("Intent is:{0}, Next state is {1}".format(final_uds.intent, final_uds.sip.get_state()))
    
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

    # Ask replygen for a reply
    def _fetch_reply(self,uds):
        curr_state = self._get_state()
        intent = uds.get_intent()
        next_state = uds.get_sip().get_state()
        return self.replygen.get_reply(curr_state, next_state, intent)

    def _parse_message_details(self, msg):
        # Adds details
        details = self.iparser.parse(msg)
        return details

    def _pending_detail_outcome(self):
        requirement = self.get_req_detail()
        if self.chat.has_info(requirement):
            return SIP(self.pending_state)
        else:
            return SIP.same_state()

    # Returns the next uds. Final
    def _gatekeep_sip(self, sip):
        if self.is_expecting_detail():
            return self._pending_detail_outcome()
            
        proposed_next = sip.get_state()
        
        # Check gate
        if proposed_next in self.GATED_STATES:
            requirement = self.GATED_STATES[proposed_next]

            # Req not satisfied
            if True:
                return SIP.same_state()

        # If nothing wrong, return the original
        return sip 

    # Process, gatekeep then internalize changes
    # Results in change in chat details and change in state
    def _digest_uds(self, uds):
        deets = uds.get_details()
        sip = uds.get_sip()

        # Update details
        if self.is_expecting_detail():
            self.push_detail_to_chat(deets)

        # Update State (may depend on details so this is 2nd)

        if sip.is_go_back():
            self.go_back()
            return

        elif sip.is_same_state():
            return
        
        # Modify if needed
        new_sip = self._gatekeep_sip(sip)
        self._update_state_from_sip(new_sip)

        # Copy of original
        final_uds = uds.copy_swap_sip(new_sip)
        return final_uds

    def _update_state_from_sip(self, sip):
        new_state = sip.get_state()
        self._change_state(new_state)
        return

    ## Internal State management
    def set_pending_state(self, pstate):
        self.pending_state = pstate

    def _change_state(self,new_state):
        if DEBUG: print("changing to", new_state)
        if self.state == new_state:
            print("Eh why same state", new_state)
        self.state_history.append(self.state)
        self.state = new_state

    def go_back_a_state(self):
        prev_state = self.state_history.pop(-1)
        chat.set_state(prev_state)

    def _get_state(self):
        return self.state

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
        return self.chat.log_details(d)


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
        
        uds = uds_from_policies(curr_state,msg)

        return uds

# Generates reply text based on current state info
class ReplyGenerator:
    def __init__(self, replyDB, rkey_dbs):
        self.replyDB = replyDB
        self.rkey_dbs = rkey_dbs

    # OVERALL METHOD
    def get_reply(self, curr_state, next_state, intent, info = -1):
        rkey = self.getreplykey(curr_state, intent, next_state)
        reply = self.generate_reply_message(rkey, info)
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
            r_list = self.replyDB[r_key]["text"]
            replytext = rand_response(r_list)
            return replytext
        return r_key

    # Generates a pure reply
    def generate_reply_message(self, reply_key, info):
        reply_template = self.fetch_reply_text(reply_key)
        final_msg = reply_template
        if isinstance(info, dict):
            print("current info",info)
            final_msg = reply_template.format(info)

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
    

    # Check if info dict has this key
    def has_info(self, key):
        return key in self.info
    
    def get_info(self, key):
        return self.info[key]

    # Add info to the current dict
    def log_details(self, info):
        for d in info:
            deet = info[d]
            if len(deet) > 0:
                self.info[rd] = info[rd]
                return True
        return False

    ## Database interaction?
    def get_previous_issues(self):
        return self.user.get_issues()

    # Writes to a file eventually
    def record_to_database(self):
        # filepath = dir + UNIQUE_ID
        # write info
        
        # write issues

        return