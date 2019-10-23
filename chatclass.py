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
        self.threadIDstack = [] # A stack of threadIDs
        self.threadmap = {}
        self.state_changed = True
        self.spawn_thread(default_state, threadID = "BASE") # Spawn base thread

    def get_curr_threadID(self):
        return self.threadIDstack[-1]

    def get_curr_thread(self):
        key = self.get_curr_threadID()
        thrd = self.threadmap[key]
        return thrd

    def _get_threadID(self, state):
        return state["thread"]

    # UNUSED intentionally. KIV.
    def state_never_change(self):
        return not self.state_changed

    def _thread_same_state(self, nstate):
        # print("new vs old", nstate, self.get_curr_thread_state())
        if DEBUG: print("StateThreader samestate:",self.get_curr_thread()._is_same_state(nstate))
        return self.get_curr_thread()._is_same_state(nstate)

    def _thread_same_id(self, tid):
        tid == self.get_curr_threadID()
    
    def spawn_thread(self, start_state = -1, threadID = "DEFAULT"):
        if isinstance(start_state, int):
            raise Exception("Tried to spawn thread but no start state provided")
        newthread = ConvoThread(start_state)
        self.threadIDstack.append(threadID)
        self.threadmap[threadID] = newthread
    
    def get_curr_thread_state(self):
        state = self.get_curr_thread().get_curr_state()
        if isinstance(state, SIP):
            raise Exception("SIP DETECTED{}".format(state.toString()))
        return state

    def kill_curr_thread(self):
        if len(self.threadIDstack) > 1:
            deadthreadID = self.threadIDstack.pop(-1)
            self.threadmap.pop(deadthreadID)

            new_headID = self.threadIDstack[-1]
            if DEBUG or 1: print("KILLING THREAD:",deadthreadID,"NEW HEAD:",new_headID)

    def switch_thread_to(self, threadID):
        # Push to front of stack
        self.threadIDstack.remove(threadID)
        self.threadIDstack.append(threadID)
        return

    def update_thread_state(self, new_state):
        def _is_terminal_state(state):
            return state["terminal_state"]

        def need_switch_thread(threadID):
            return not (threadID == "NONE" or self._thread_same_id(threadID))

        ns_threadID = self._get_threadID(new_state)
        UPDATE_STATE_BOOL = True
        curr_state = self.get_curr_thread_state()

        if _is_terminal_state(curr_state):
            UPDATE_STATE_BOOL = not self._thread_same_state(new_state)
            self.kill_curr_thread()
        
        if need_switch_thread(ns_threadID):
            if ns_threadID in self.threadmap:
                self.switch_thread_to(ns_threadID)
            else:
                self.spawn_thread(new_state, ns_threadID)
        
        if UPDATE_STATE_BOOL:
            self.get_curr_thread().update_state(new_state)

        if DEBUG: print("Statestack", self.threadIDstack)

        return UPDATE_STATE_BOOL

    # Assigns the pending state to the current thread
    def set_thread_pending(self, hs, ps):
        self.get_curr_thread().set_pending_state(hs,ps)

    # If has pending, returns pending
    # If nothing pending, returns given_next_state
    def move_forward(self, given_next_state):
        if self.get_curr_thread().has_pending_state():
            if DEBUG: print("Unlocking...")
            self.get_curr_thread().unlock_pending_state()
            self.state_changed = True
        else:
            self.state_changed = self.update_thread_state(given_next_state)
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
        notsamestate = not self._is_same_state(new_state)
        if notsamestate:
            self.state_history.append(self.curr_state)
            self.curr_state = new_state
        return notsamestate

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
        if DEBUG: print("Initial UDS:")
        if DEBUG: uds.printout()
        self.gatekeeper.scan_SIP(uds.get_sip())

        # Try to mine message details. 
        # This is after gatekeep because gatekeep sets the slots.
        self._parse_message_details(msg)

        return uds
    
    # Process, gatekeep then internalize changes
    # Results in change in chat details and change in state
    def _digest_uds(self, uds):
        sip = uds.get_sip()

        # FEATURE NOT IMPLEMENTED
        # if sip.is_go_back():
        #     self.go_back_a_state()
        #     return final_intent

        if sip.is_same_state():
            if DEBUG: print("SAME STATE FLAGGED")
            self.samestateflag = True
            state = self._get_curr_state()
        else:
            self.samestateflag = False
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
            self._move_forward_state(nextstate)

        else:
            # Didnt pass
            constructed_sip = self._make_info_sip(required_slots)
            infostate = constructed_sip.get_state_obj()
            self._set_thread_pending(infostate, nextstate)
           

    # REMOVAL
    def _make_info_sip(self, req_info):
        con_sip = self.pkeeper.make_info_req_sip(req_info)
        return con_sip

    def _set_thread_pending(self, hs, ps):
         self.statethreader.set_thread_pending(hs, ps)

    def _move_forward_state(self, state):
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
        # samestateflag = self.statethreader.state_never_change()
        samestateflag = self.samestateflag
        print("curr_state", curr_state['key'], "samestate",samestateflag)
        return self.replygen.get_reply(curr_state, intent, samestateflag, information)

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
        # prev_info = self.dbr.fetch_user_info(chatID)
        # self.chat_prov_info.update(prev_info)

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
    def __init__(self, formattingDB):
        self.formatDB = formattingDB
        self.formatter = string.Formatter()

    # OVERALL METHOD
    def get_reply(self, curr_state, intent, ss, info = -1):
        rdb = self.getreplydb(intent, curr_state, ss)
        infoplus = self._enhance_info(curr_state, info)
        reply = self.generate_reply_message(rdb, infoplus)
        return reply

    # Formats txts and calculates
    # Big function
    def _enhance_info(self,curr_state,info):
        enhanced = info.copy()
        if DEBUG: print("initial info", enhanced)
        rep_ext = {}
        l_calc_ext = {}

        cskey = curr_state["key"]
        state_calcs = False

        formatDB = self.formatDB["msg_formats"]
        calcDB = self.formatDB["calcs"]

        def add_enh(key, value, ext_dict,overall_key):
            print("Enhancing!{}:{}".format(key,value))
            if key in ext_dict:
                ext_dict[key] = ext_dict[key] + value
            else:
                ext_dict[key] = value
            
            # MODIFYING ORIGINAL DICT
            if not overall_key in enhanced: enhanced[overall_key] = {} 
            enhanced[overall_key].update(ext_dict)

        def add_txt_enh(key, rawstr):
            wstr = rawstr.format(**enhanced)
            enhstr = cbsv.conv_numstr(wstr)
            return add_enh(key,enhstr,rep_ext,"rep_ext")
        
        def add_calc_enh(key, rawstr):
            flt = float(rawstr)
            print("Calculated {}:{}".format(key,flt))
            return add_enh(key,flt,l_calc_ext,"calc_ext")

        def needs_txt_enh(tmp,csk):
            states = tmp["states"]
            return csk in states

        def needs_calc(state):
            return "calcs" in state

        def fcondition_met(f):
            # This assumes all conditions are linked by AND
            conds = f["conditions"]
            for cond in conds:
                k, v = cond
                if not k in enhanced:
                    print("ERROR {} not in info".format(k))
                    return False
                
                met = (enhanced[k] == v) # Simple match
                if not met:
                    return False
            return True

        # Useful
        # Recursively looks in dicts for nested dicts until finds values.
        def dive_for_values(c_list, c_dir, failzero = False):
                out = {}
                for valname in c_list:
                    if isinstance(valname, list):
                        nextdirname, nestlist = valname
                        if not nextdirname in c_dir:
                            print("ERROR! Cannot find subdict<{}> in {}".format(nextdirname,c_dir))
                            return {}
                        nextdir = c_dir[nextdirname]
                        out.update(dive_for_values(nestlist,nextdir))
                    else:
                        if valname in c_dir:
                            rawval = c_dir[valname]
                            out[valname] = rawval
                        elif failzero:
                            # Returns 0
                            return {valname:0}
                        else:
                            print("ERROR! Cannot find variable<{}> in {}".format(valname,c_dir))
                            
                return out

        def resolve_formula(f):
            reqvars = "req_vars"
            dz_rv = "dz_req_vars"
            def op_on_all(vnames, op, vdic):
                def operate(a,b,op):
                    print("a,b", a, b)
                    return op(a,b)
                out = None
                for vname in vnames:
                    isnumbr = cbsv.is_number(vname)
                    rel_val = vname if isnumbr else vdic[vname]
                    if out == None:
                        out = rel_val
                    else:
                        out = operate(out,rel_val,op)
                return out
                    
            instr = f["steps"]
            steps = list(instr.keys())
            steps = list(map(lambda x: (x.split(","), instr[x]),steps))
            steps.sort(key=lambda t: float(t[0][0])) # If no conversion it sorts as string
            if DEBUG: print("aft sort",steps)
            req_vars = f[reqvars]
            vd = dive_for_values(req_vars,enhanced)
            if dz_rv in f:
                dz_vals = dive_for_values(f[dz_rv], enhanced,failzero = True)
                vd.update(dz_vals)

            if DEBUG: print("vd",vd)

            #CALCULATIONS 
            vd["OUTCOME"] = 0
            for stp in steps:
                (NA, opname),(valnames,tkey)  = stp
                opname.replace(" ","")
                if not tkey in vd:
                    vd[tkey] = 0

                if opname == "add":
                    opr = lambda a,b: a+b
                elif opname == "multi":
                    opr = lambda a,b: a*b
                elif opname == "sub":
                    opr = lambda a,b: a-b
                elif opname == "div":
                    opr = lambda a,b: a/b
                elif opname == "issame":
                    opr = lambda a,b: (1 if a == b else 0)
                elif opname == "isgreater":
                    opr = lambda a,b: (1 if a > b else 0)
                else:
                    opr = lambda a,b: a
                vd[tkey] = op_on_all(valnames,opr,vd)
            return vd["OUTCOME"]

        ### MAIN FUNCTION ###
        # Calculations
        if needs_calc(curr_state):
            state_calcs = curr_state["calcs"]
            for fname in state_calcs:
                print("performing",fname)
                if not fname in calcDB:
                    print("ERROR! No such formula:{}".format(fname))
                else:
                    formula = calcDB[fname]
                    if fcondition_met(formula):
                        target_key = formula["writeto"]
                        result = resolve_formula(formula)
                        add_calc_enh(target_key,result)
        else:
            print("No calculation performed")

        if DEBUG: print("postcalc enh",enhanced)

        # Message extensions and formatting
        # Template in format database
        for tmp in formatDB:
            if needs_txt_enh(tmp,cskey):
                target_key = tmp["writeto"]
                lookout = tmp["lookfor"].copy()
                vd = dive_for_values(lookout, enhanced)
                # vks = list(vd.keys())
                
                print("TMP",tmp)
                # assert ("if_present" in tmp)
                # assert ("if value" in tmp)

                if "if_present" in tmp:
                    ifpr = tmp["if_present"]
                    for deet in list(ifpr.keys()):
                        enstr = ifpr[deet]
                        add_txt_enh(target_key,enstr)
                
                if "if_value" in tmp:
                    ifvl = tmp["if_value"]
                    for deet in list(ifvl.keys()):
                        formatmap = ifvl[deet]
                        if isinstance(vd[deet],list):
                            # E.g. reqinfo is a list
                            contents = vd[deet]
                        else:
                            contents = [vd[deet]]

                        for deetval in contents:
                            dstr = str(cbsv.conv_numstr(deetval,wantint=1)) # Because json keys can only be str
                            enstr = formatmap[dstr]
                            add_txt_enh(target_key,enstr)
        
        # info.update(enhanced) # Write to info
        return enhanced


    def getreplydb(self, intent, curr_state, issamestate):
        def get_replylist(obj):
            # print("get replies from obj",obj)
            return obj["replies"]
    
        LOCALDEBUG = 0 or DEBUG
        

        if LOCALDEBUG: print("csk", curr_state["key"],curr_state["thread"])

        # Decides priority of lookup. 
        # If same state flagged, look at intents first
        # Else look at state based replies
        lookups = [intent, curr_state] if issamestate else [curr_state, intent]

        rdb = []
        for obj in lookups:
            if obj == cbsv.NO_INTENT():
                # This is for when no intent
                continue

            if rdb == []:
                rdb = get_replylist(obj)
            else:
                break
        
        if LOCALDEBUG: print("rdb:",rdb)

        if rdb == []:
            # call the NLP AI here.
            rdb = cbsv.DEFAULT_CONFUSED() # TODO fix bad OOP

        return rdb

    # Generates a pure reply
    def generate_reply_message(self, rdb, info):
        def rand_response(response_list):
            return random.choice(response_list)

        reply_template = rand_response(rdb)
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
        if self.convo_index < 2:
            return
        return self.curr_chatlog[self.convo_index - 2]
    

    ## Database interaction?
    def get_previous_issues(self):
        pass
        # return self.user.get_issues()

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