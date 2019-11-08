# All Chat related Classes

import re
import random
import cbsv
import string
import os
from datetime import datetime
from chatbot_supp import *
from chatbot_utils import dive_for_values

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
            if DEBUG : print("KILLING THREAD:",deadthreadID,"NEW HEAD:",new_headID)

    def switch_thread_to(self, threadID):
        # Push to front of stack
        self.threadIDstack.remove(threadID)
        self.threadIDstack.append(threadID)
        return

    def update_thread_state(self, new_state_obj):
        def _is_terminal_state(state):
            return state["terminal_state"]

        def need_switch_thread(threadID):
            return not (threadID == "NONE" or self._thread_same_id(threadID))

        ns_threadID = self._get_threadID(new_state_obj)
        UPDATE_STATE_BOOL = True
        curr_state = self.get_curr_thread_state()

        if _is_terminal_state(curr_state):
            UPDATE_STATE_BOOL = not self._thread_same_state(new_state_obj)
            self.kill_curr_thread()
        
        if need_switch_thread(ns_threadID):
            if ns_threadID in self.threadmap:
                self.switch_thread_to(ns_threadID)
            else:
                self.spawn_thread(new_state_obj, ns_threadID)
        
        if UPDATE_STATE_BOOL:
            self.get_curr_thread().update_state(new_state_obj)

        if DEBUG: print("<STATETHREADER>Statestack", self.threadIDstack)

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
            if DEBUG: print("<ConvoThread> Existing pend state:{} new:{}".format(self.get_pending_state(), pstate))
            return
        if DEBUG: print("<ConvoThread> Setting pending state:",pstate)
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

# Keeps track of zones like city
class ZoneTracker:
    def __init__(self):
        self.zones = {}

    def _add_zone(self, z, val):
        if z in self.zones:
            print("<ADD_ZONE> Existing zone {}:{}. Did not write {}.".format(z,self.zones[z],val))
            return
        self.zones[z] = val

    def update_zones_from_d(self, deets):
        zkey = "zones"
        if zkey in deets:
            zone_d = deets[zkey]
            for z, val in zone_d.items():
                self._add_zone(z, val)

    def get_zones(self):
        return self.zones.copy()

    def get_zone_val(self, z):
        if not z in self.zones:
            return None
        return self.zones[z]

# Coordinates everything about a chat
class ChatManager:
    def __init__(self, chat, iparser, pkeeper, replygen, dmanager, gkeeper):
        # Internal properties
        self.chat = chat
        self.chatID = self.chat.getID()
        self.samestateflag = False

        # Helper classes
        self.iparser = iparser
        self.pkeeper = pkeeper
        self.replygen = replygen
        self.dmanager = dmanager.clone(self.chatID)
        self.gatekeeper = gkeeper
        self.statethreader = StateThreader(pkeeper.GET_INITIAL_STATE())
        self.ztracker = ZoneTracker()

    def _get_curr_state(self):
        return self.statethreader.get_curr_thread_state()

    def _get_csk(self):
        return cbsv.getstatekey(self._get_curr_state())

    def _get_zones(self):
        return self.ztracker.get_zones()
    
    ############### PRIMARY METHOD ###############
    # Takes in a message, returns (text reply, intent breakdown, current info)
    def respond_to_message(self, msg):
        print("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~") # For clarity in terminal
        rcount = 0
        repeat = True
        while repeat:
            # Parse the message and get an understanding
            full_uds, bd = self._parse_message_overall(msg)

            # Digest and internalize the new info
            sip = full_uds.get_sip()
            repeat = self._digest_sip(sip)

            if repeat and DEBUG: print("REPEATING",rcount)

            rcount += 1
            if rcount > 5: break

        # Request a reply text
        intent = full_uds.get_intent()
        reply = self._fetch_reply(intent)

        curr_info = self._get_current_info()

        self._record_messages_in_chat(msg,reply)
        return (reply, bd, curr_info)

    # Takes in message text, returns (understanding object, nlp breakdown)
    def _parse_message_overall(self,msg):
        # Inital understanding
        uds, bd = self._fetch_understanding(msg)
        if DEBUG: print("Initial UDS:")
        if DEBUG: uds.printout()
        # self.gatekeeper.scan_SIP(uds.get_sip()) # TODO CHECK IF THIS IS USEFUL

        # Mine message details. 
        # This is after gatekeep because gatekeep sets the slots.
        self._parse_message_details(msg)

        return uds, bd
    
    # Process, gatekeep then internalize changes
    # Results in change in chat details and change in state
    # Returns boolean indicating whether or not the state was overwritten.
    def _digest_sip(self, sip):
        
        if sip.is_same_state():
            if DEBUG: print("SAME STATE FLAGGED")
            self.samestateflag = True
            stateobj = self._get_curr_state()
        else:
            self.samestateflag = False
            stateobj = sip.get_state_obj()

        # Check if current target state is in a zone_policy crossroad 
        ow_flag, stateobj = self._zone_policy_overwrite(stateobj)

        # Gatekeeper gets the requirements from the state
        self._get_slots_from_state(stateobj)
        # Gatekeeper tries the gate
        self._advance_to_new_state(stateobj)

        return ow_flag

    def _move_forward_state(self, state):
        self.statethreader.move_forward(state)

    def _get_slots_from_state(self, stateobj):
        self.gatekeeper.scan_state_obj(stateobj)

    # CHANGES STATE
    # Updates state according to outcome
    def _advance_to_new_state(self, nextstate):
        def _make_info_sip(req_info):
            con_sip = self.pkeeper.make_info_req_sip(req_info)
            return con_sip

        def _set_thread_pending(hs, ps):
            self.statethreader.set_thread_pending(hs, ps)
        
        curr_info = self._get_current_info()
        print("Current info:",curr_info)
        passed, required_slots = self.gatekeeper.try_gate(curr_info)


        if DEBUG: print("Gate passed:",passed)

        if passed:
            self._move_forward_state(nextstate)
        else:
            # Update DetailManager
            self.push_req_slots_to_dm(required_slots)

            # Didnt pass gate
            constructed_sip = _make_info_sip(required_slots)
            infostate = constructed_sip.get_state_obj()
            _set_thread_pending(infostate, nextstate)

    # Overwrites state if in zone policy
    def _zone_policy_overwrite(self, og_nxt_state):
        csk = og_nxt_state["key"]
        zones = self._get_zones()
        overwrite_flag, ow_state = self.pkeeper.zone_policy_overwrite(csk,zones)
        print("ZONE POLICY",overwrite_flag,ow_state)
        if overwrite_flag:
            return (True, ow_state)
        else:
            return (False, og_nxt_state)

    def push_req_slots_to_dm(self, required_slots):
        if len(required_slots) > 0:
            required_info = list(map(lambda x: x[0],required_slots)) # First element
            print("pushslotstodm Reqinfo",required_info)
            info_entry = {"requested_info": required_info}
            self.push_detail_to_dm(info_entry)
        return

    ### Ask Helpers
    # Ask replygen for a reply
    def _fetch_reply(self,intent):
        information = self._get_current_info()
        curr_state = self._get_curr_state()
        if DEBUG: print("Current State",curr_state)
        # samestateflag = self.statethreader.state_never_change()
        samestateflag = self.samestateflag
        # print("curr_state", curr_state['key'], "samestate",samestateflag)
        return self.replygen.get_reply(curr_state, intent, samestateflag, information)

    # Asks dmanager for info
    def _get_current_info(self):
        return self.dmanager.fetch_info()

     # Gets the next state according to policy
    def _fetch_understanding(self, msg):
        csk = self._get_csk()
        return self.pkeeper.get_understanding(msg, csk)

    # Asks iparser to parse the message
    def _parse_message_details(self, msg):
        slots = self.gatekeeper.get_slots() # Only look out for what is needed
        details = self.iparser.parse(msg, slots)
        self.ztracker.update_zones_from_d(details)
        self.push_detail_to_dm(details)
        return

    ### Detail logging
    def push_detail_to_dm(self, d):
        return self.dmanager.log_detail(d)

    ### Chat logging
    def _record_messages_in_chat(self,recv, sent):
        self.chat.record_messages(recv,sent)
        return
    
    def backup_chat(self):
        self.chat.record_to_database()
        return

# Keeps policies
# Also deciphers messages
class PolicyKeeper:
    def __init__(self, policy_rules, zone_policies, intent_dict, state_lib,pp):
        self.POLICY_RULES = policy_rules
        self.ZONE_POLICIES = zone_policies
        self.INTENT_DICT = intent_dict
        self.STATE_DICT = state_lib
        self.predictor = pp

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

    def _NLP_predict(self,msg):
        pack = self.predictor.predict(msg)
        intent = pack["prediction"]
        breakdown = pack["breakdown"]
        return intent, breakdown

    # MAIN METHOD
    # Returns an understanding and NLP breakdown
    def get_understanding(self, msg, curr_state):
        # Call NLP Model predict
        intent, breakdown = self._NLP_predict(msg)
        print("NLP intent:",intent)
        # Check intent against background info
        uds = self.intent_to_next_state(curr_state, intent)
        return uds, breakdown

    def _create_state_obj(self, sk):
        if not sk in self.STATE_DICT:
            print("<PolicyKeeper> Illegal state:",sk)
            return SIP.same_state().get_state_key() # Bad.
        state_obj = self.STATE_DICT[sk]
        return state_obj

    # METHOD FOR NLP
    def intent_to_next_state(self, csk, intent):
        if intent in self.INTENT_DICT:
            intent_obj = self.INTENT_DICT[intent]
        else:
            intent_obj = False

        policy = self.POLICY_RULES[csk]
        default_null_int = self.INTENT_DICT["no_intent"]
        uds = Understanding(default_null_int,SIP.same_state())
        for intent_lst in policy.get_intents():
            print("intent_list",list(map(lambda x: x[0],intent_lst)))
            for pair in intent_lst:
                c_int, next_sip = pair
                if intent == c_int:
                    print("MATCH",intent)
                    uds = Understanding(intent_obj, next_sip)
                    return uds
        return uds

    def zone_policy_overwrite(self, csk, chat_zones):
        def check_zonepolicies(state_key):
            return state_key in self.ZONE_POLICIES

        # Zone policy
        if check_zonepolicies(csk):
            z, paths = self.ZONE_POLICIES[csk]
        
            if z in chat_zones:
                z_val = chat_zones[z]
                if DEBUG: print("zonepolicy",chat_zones, z, z_val)
                if z_val in paths:
                    target = paths[z_val]
                else:
                    target = paths["DEFAULT"]
                next_sip = self._create_state_obj(target)
                return (True, next_sip)

        return (False, "")

    # OLD METHOD USING SEARCH. NOT USED
    # def decipher_message(self,curr_state,msg):
    #     def get_intent_matchdb(intent):
    #         if not "matchdb" in intent:
    #             raise Exception("intent missing matchdb, {}".format(intent))
    #         return intent["matchdb"]

    #     # Returns an Understanding minus details
    #     def uds_from_policies(state, msg):
    #         if DEBUG: print("uds from state:",state)
    #         policy = self.POLICY_RULES[state]
    #         # print("policy list intents", policy.get_intents())
    #         for intent_lst in policy.get_intents():
    #             for pair in intent_lst:
    #                 intent, next_sip = pair
    #                 assert isinstance(next_sip, SIP)
    #                 keyword_db = get_intent_matchdb(intent)
    #                 if cbsv.check_input_against_db(msg, keyword_db):
    #                     return Understanding(intent, next_sip)
    #         return Understanding.make_null()
        
    #     uds = uds_from_policies(curr_state,msg)

    #     return uds

# MANAGES DETAILS (previously held by Chat)
# TODO: Differentiate between contextual chat info and user info?
class DetailManager:
    def __init__(self, info_vault,secondary_slots):
        self.vault = info_vault
        self.inital_dict = {"s_slots":{}}
        self.chat_prov_info = self.inital_dict
        self.dbr = {"dummy"}
        self.dbrset = False
        self.chatID = "PLACEHOLDER_USERID"
        self.second_slots = secondary_slots

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

        self._add_secondary_slots(self.fetch_info())

        self.write_info_to_db()
        return

    # Info without vault
    def get_user_info(self):
        not_user_info = ["requested_info", "paile","拍了"] #TODO find a proper way to store this info in JSON
        dic = self.chat_prov_info.copy()
        for i in not_user_info:
            if i in dic: 
                dic.pop(i)
        return dic
    
    def _add_secondary_slots(self, curr_info):
        def tree_search(tree, info):
            slot, sub_dict = list(tree.items())[0]
            # default_val = tree["DEFAULT_VALUE"]
            while slot in info:
                slot_val = info[slot]
                if slot_val in sub_dict:
                    ss_branch = sub_dict[slot_val]
                    if isinstance(ss_branch, dict):
                        slot, sub_dict = list(ss_branch.items())[0]
                    else:
                        return (True, ss_branch)
                else:
                    if DEBUG: print("<SECONDARY SLOT> Val not found:", slot_val)
                    break
            return (False, "")

        entries = {}
        for ss in self.second_slots:
            target = ss["writeto"]
            tree = ss["search_tree"]
            f, val = tree_search(tree, curr_info)
            if f: entries[target] = val
        
        self.chat_prov_info["s_slots"].update(entries)
        return 

    # Called to get chat info + vault info
    def fetch_info(self):
        out = {}
        out.update(self.chat_prov_info)

        # Add City info lookup
        if cbsv.CITY() in self.chat_prov_info:
            cityname = self.chat_prov_info[cbsv.CITY()]
            out["city_info"] = self.vault.lookup_city(cityname)
        
        return out
    # This is called during the creation of a new chat
    def clone(self, chatID):   
        if not self.dbrset:
            raise Exception("DatabaseRunner not initalized for DetailManager!")
        clonetrooper = DetailManager(self.vault, self.second_slots)
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
    def __init__(self, formattingDB, humanizer):
        self.formatDB = formattingDB
        self.formatter = string.Formatter()
        self.humanizer = humanizer
        self.hflag = True
        
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

        def add_enh(key, value, ext_dict,overall_key, overwrite = False):
            if 0: print("Enhancing!{}:{}".format(key,value))
            if key in ext_dict and not overwrite:
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
            flt = round(float(rawstr),2)
            return add_enh(key,flt,l_calc_ext,"calc_ext",overwrite = True)

        def needs_txt_enh(tmp,csk):
            states = tmp["states"]
            return csk in states

        def needs_calc(state):
            return "calcs" in state

        def add_conditional_vars(f,vd):
            ret = {}
            # This assumes all conditions are joined by AND
            conds = f["conditions"]
            for cond in conds:
                k, v, setval = cond
                if not k in vd:
                    print("ERROR {} not in info".format(k))
                    return False
                
                met = (vd[k] == v) # Simple match
                vkey, tval, fval = setval
                ret[vkey] = tval if met else fval

            vd.update(ret)
            return

        # Big method.
        # Takes in a formula (dict)
        # Returns a value of the result
        def resolve_formula(f):
            reqvars = "req_vars"
            def op_on_all(vnames, op, vdic):
                def operate(a,b,op):
                    if 0: print("a,b", a, b)
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
            
            # Conditional values
            add_conditional_vars(f,vd)
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

        ### MAIN METHOD LOGIC ###
        # Calculations
        if needs_calc(curr_state):
            state_calcs = curr_state["calcs"]
            for fname in state_calcs:
                print("performing",fname)
                if not fname in calcDB:
                    print("ERROR! No such formula:{}".format(fname))
                else:
                    formula = calcDB[fname]
                    target_key = formula["writeto"]
                    result = resolve_formula(formula)
                    add_calc_enh(target_key,result)
                if 1: print("<Intermediate> enh",enhanced)

        else:
            if DEBUG: print("No calculation performed")

        if DEBUG: print("postcalc enh",enhanced)

        # Message extensions and formatting
        # Template in format database
        for tmp in formatDB:
            if needs_txt_enh(tmp,cskey):
                target_key = tmp["writeto"]
                lookout = tmp["lookfor"].copy()
                vd = dive_for_values(lookout, enhanced)
                
                print("TMP",tmp)

                if "if_present" in tmp:
                    ifpr = tmp["if_present"]
                    for deet in list(ifpr.keys()):
                        enstr = ifpr[deet]
                        add_txt_enh(target_key,enstr)
                
                if "if_value" in tmp:
                    ifvl = tmp["if_value"]
                    for deet in list(ifvl.keys()):
                        if not deet in vd:
                            continue
                        formatmap = ifvl[deet]
                        if isinstance(vd[deet],list):
                            # E.g. reqinfo is a list
                            contents = vd[deet]
                        else:
                            contents = [vd[deet]]

                        for deetval in contents:
                            dstr = str(cbsv.conv_numstr(deetval,wantint=1)) # Because json keys can only be str
                            if dstr in formatmap:
                                enstr = formatmap[dstr]
                            else:
                                enstr = formatmap["DEFAULT"]
                            add_txt_enh(target_key,enstr)
        
        # info.update(enhanced) # Write to info
        return enhanced

    # Returns the a reply database either from intent or from state
    def getreplydb(self, intent, curr_state, issamestate):
        def get_hflag(obj):
            # Default is true
            hflag = True

            if "humanify" in obj:
                hflag = obj["humanify"]

            return hflag

        def get_replylist(obj):
            if DEBUG: print("<replydb> Pulling reply from:", obj["key"])
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
                self.hflag = get_hflag(obj)
            else:
                break
        
        if LOCALDEBUG: print("rdb:",rdb)

        if rdb == []:
            rdb = cbsv.DEFAULT_CONFUSED() # TODO fix bad OOP

        return rdb

    # Generates a pure reply
    def generate_reply_message(self, rdb, info):
        def rand_response(response_list):
            return random.choice(response_list)
        def _humanify(msg, i):
            return self.humanizer.humanify(msg,i)

        reply_template = rand_response(rdb)
        if DEBUG: print("template",reply_template)
        final_msg = reply_template
        if isinstance(info, dict):
            if DEBUG: print("Enhanced info:",info)
            
            # Uses kwargs to fill this space
            final_msg = reply_template.format(**info)

        if self.hflag: final_msg = _humanify(final_msg, info)
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

    def pop_prev_msg(self):
        # TODO failsafe when empty?
        # Need to get the previous previous message
        if self.convo_index < 2:
            return
        return self.curr_chatlog[self.convo_index - 2]
    

    ## TODO Database interaction?
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