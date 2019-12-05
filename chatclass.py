# All Chat related Classes

import re
import random
import cbsv
import string
import os
import chatbot_be
from datetime import datetime
from chatbot_supp import *
from chatbot_utils import dive_for_values


SUPER_DEBUG = 0
DEBUG = 1

DEBUG = DEBUG or SUPER_DEBUG

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
            tskey = "terminal_state"
            if tskey in state:
                return state["terminal_state"]
            else:
                return False

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
        # if z in self.zones:
        #     if DEBUG: print("<ADD ZONE> Existing zone {}:{}. Did not write {}.".format(z,self.zones[z],val))
        #     return
        self.zones[z] = val

    # Fetches info from the dm
    def update_zones_from_dm(self, dm):
        all_info = dm.fetch_info()
        zkey = "zones"
        if zkey in all_info:
            zone_dic = all_info[zkey]
            for z, val in zone_dic.items():
                self._add_zone(z, val)
        return

    def get_zones(self):
        return self.zones.copy()

    def get_zone_val(self, z):
        if not z in self.zones:
            return None
        return self.zones[z]

# Coordinates everything about a chat
class ChatManager:
    def __init__(self, chat, calc, iparser, pkeeper, replygen, dmanager, gkeeper):
        # Internal properties
        self.chat = chat
        self.chatID = self.chat.getID()
        self.samestateflag = False

        # Helper classes
        self.calculator = calc
        self.iparser = iparser
        self.pkeeper = pkeeper
        self.replygen = replygen
        self.dmanager = dmanager.clone(self.chatID)
        self.gatekeeper = gkeeper
        self.statethreader = StateThreader(pkeeper.GET_INITIAL_STATE())
        self.ztracker = ZoneTracker()
        self.INFORM_INT = pkeeper.GET_INFORM_INTENT() # TODO Not very good OOP


    def _get_curr_state(self):
        return self.statethreader.get_curr_thread_state()

    def _get_csk(self):
        return cbsv.getstatekey(self._get_curr_state())

    def _get_zones(self):
        return self.ztracker.get_zones()
    
    ############### PRIMARY METHOD ###############
    # Takes in a message, returns (text reply, intent breakdown, current info)
    def respond_to_message(self, msg):
        print("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~&") # For clarity in terminal
     
        firstpass = True
        for rc in range(0, 5):
            # Parse the message and get an understanding
            full_uds, bd = self._parse_message_overall(msg)
            true_sip = full_uds.get_sip()

            if firstpass:
                firstpass = False
                sip = true_sip # This is to prevent example affirm applying more than once
            else:
                sip = sip.same_state()

            # Calls the calculator to crunch numbers for state change
            self._calculate()

            # Digest and internalize the new info
            zone_overwrite, pg = self.react_to_sip(sip)

            if DEBUG: print("<RTM LOOP> Repeats", rc,"curr sip", sip.toString(), "True SIP", true_sip.toString(),"Pass gate:",pg)

            if not true_sip.is_trans_state() and not sip.is_same_state():
                if DEBUG: print("<RTM LOOP> Not trans state or same_state, breaking")
                break

        # Calls the calculator to crunch numbers for replying
        calc_ext = self._calculate()
    
        intent = full_uds.get_intent()
        reply = self._fetch_reply(intent, calc_ext)
        
        # Clean up
        self._post_process(full_uds)

        # Records message logs
        self._record_messages_in_chat(msg,reply)

        # Return this for debugging purposes
        curr_info = self._get_current_info()
        return (reply, bd, curr_info)

    # Makes sense of message.
    # Calls policykeeper to get intent (NLP) and next state
    # Calls gatekeeper to scan requirements
    # Calls iparser to fill slots, with requirements from gatekeeper
    # Takes in message text, returns (understanding object, nlp breakdown)
    def _parse_message_overall(self,msg):
        # Inital understanding
        uds, bd, nums = self._policykeeper_parse(msg)
        if DEBUG: print("Initial UDS:")
        if DEBUG: uds.printout()
        self.gatekeeper.scan_SIP(uds.get_sip()) # Used for pre-filling slots

        # Mine message details. 
        # This is after gatekeep because gatekeep sets the slots.
        og_int = uds.get_og_intent()
        self._parse_message_details(msg, nums,og_int)

        # Preprocess to fill slots with default vals
        self._gatekeeper_preprocess()

        return uds, bd
    
    # Calculate, zonecheck, gatekeep then internalize changes
    # Converts same_state_obj to the current state.
    # Checks if the state is crossroad and needs to be overwritten
    # Gatekeeper gets requirements from state again in case it changed.
    # Results in change in chat details and change in state
    # Returns boolean indicating whether or not the state was overwritten.
    def react_to_sip(self, sip):

        if sip.is_same_state():
            if DEBUG: print("<REACTION> SAME STATE FLAGGED")
            self.samestateflag = True
            stateobj = self._get_curr_state()
        else:
            self.samestateflag = False
            stateobj = sip.get_state_obj()
        if DEBUG: print("<REACTION> Curr state", self._get_curr_state()["key"], "Nxt stateobj", stateobj["key"])
        
        # Check if current target state is in a zone_policy crossroad 
        ow_flag, stateobj = self._zone_policy_overwrite(stateobj)

        if ow_flag:
            # Gatekeeper gets the requirements from the state
            self._get_slots_from_state(stateobj)
        
        # Gatekeeper tries the gate and CHANGES STATE
        pass_gate = self._advance_to_new_state(stateobj)

        return (ow_flag, pass_gate)

    def _move_forward_state(self, state):
        self.statethreader.move_forward(state)

    def _get_slots_from_state(self, stateobj):
        self.gatekeeper.scan_state_obj(stateobj)

    def _try_gatekeeper_gate(self):
        curr_info = self._get_current_info()
        if SUPER_DEBUG: print("<CHAT MGR TRY GATE> Current info:",curr_info)
        pf, rs, info_topup = self.gatekeeper.try_gate(curr_info)
        self.push_detail_to_dm(info_topup, ow=False) # Detail update. No Overwrite
        return (pf, rs)

    # CHANGES STATE
    # Updates state according to outcome
    def _advance_to_new_state(self, nextstate):
        def _make_info_sip(req_info):
            con_sip = self.pkeeper.make_info_req_sip(req_info)
            return con_sip

        def _set_thread_pending(hs, ps):
            self.statethreader.set_thread_pending(hs, ps)
        
        passed, req_slots = self._try_gatekeeper_gate()

        if DEBUG: print("Gate passed:",passed)

        if passed:
            self._move_forward_state(nextstate)
        else:
            # Didnt pass gate
            self.push_req_slots_to_dm(req_slots)            
            constructed_sip = _make_info_sip(req_slots)
            infostate = constructed_sip.get_state_obj()
            _set_thread_pending(infostate, nextstate)

        return passed

    # Overwrites state if currently in zone policy aka crossroad
    def _zone_policy_overwrite(self, og_nxt_state):
        csk = og_nxt_state["key"]
        zones = self._get_zones()
        overwrite_flag, ow_state = self.pkeeper.zone_policy_overwrite(csk,zones)
        if DEBUG: print("<ZONE POLICY> Overwrite:",overwrite_flag,ow_state)
        if overwrite_flag:
            next_state = ow_state
        else:
            next_state = og_nxt_state

        return (overwrite_flag, next_state)

    def push_req_slots_to_dm(self, required_slots):
        if len(required_slots) > 0:
            required_info = list(map(lambda x: x[0],required_slots)) # First element
            print("pushslotstodm Reqinfo",required_info)
            info_entry = {"requested_info": required_info}
            self.push_detail_to_dm(info_entry)
        return

    ### Ask Helpers
    # Ask replygen for a reply
    def _fetch_reply(self,intent, calc_ext):
        info = self._get_current_info()
        info["calc_ext"] = calc_ext #Add calc ext to the info to be passed in

        curr_state = self._get_curr_state()
        if DEBUG: print("<Fetch Reply> Current State",curr_state)
        # samestateflag = self.statethreader.state_never_change()
        ssflag = self.samestateflag
        # print("curr_state", curr_state['key'], "samestate",samestateflag)
        return self.replygen.get_reply(curr_state, intent, ssflag, info)

    # Asks dmanager for info
    def _get_current_info(self):
        return self.dmanager.fetch_info()

     # Gets the next state according to policy
    def _policykeeper_parse(self, msg):
        csk = self._get_csk()
        return self.pkeeper.get_understanding(msg, csk)

    # Asks iparser to parse the message
    def _parse_message_details(self, msg, nums, intent):
        slots = self.gatekeeper.get_slots() # Only look out for what is needed
        details = self.iparser.parse(msg, slots, intent)

        # Append parsed number to details
        bignum = max(nums) if len(nums) > 0 else 0
        if bignum > 0:
            details["given_amount"] = bignum ## TODO: Work in PROGRESS. Gets the biggest number from the list
        
        self.push_detail_to_dm(details)
        return

    # Ask calculator to crunch numbers.
    # Updates information dict
    def _calculate(self):
        info = self._get_current_info()
        print("INFO FOR CALC", info)
        curr_state = self._get_curr_state()
        topup, calc_ext = self.calculator.calculate(curr_state, info)
        self.push_detail_to_dm(topup) # Adds persist values to info
        return calc_ext

    # Clears up values
    def _post_process(self, uds):
        pd = {}
        sip = uds.get_sip()
        clearlist = sip.get_clears()
        for to_clear in clearlist:
            pd[to_clear] = ""

        self.push_detail_to_dm(pd)
        return 

    ### Detail logging
    def push_detail_to_dm(self, d, ow=1):
        self.dmanager.log_detail(d, OVERWRITE=1)
        self.ztracker.update_zones_from_dm(self.dmanager)
        return 

    def read_chat_history(self, history_list):
        if DEBUG: print("Reading chat history")
        hist_info = self.iparser.parse_chat_history(history_list)
        self.dmanager.log_detail(hist_info, OVERWRITE=0)
        return

    # Calls the gatekeeper to get default slot values
    # Updates slot values
    def _gatekeeper_preprocess(self):
        curr_info = self._get_current_info()
        gk_topup = self.gatekeeper.preprocess(curr_info) # Fill default slot values AFTER parsing
        self.push_detail_to_dm(gk_topup, ow=0)
        return

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

    def GET_INFORM_INTENT(self):
        initstate = self.INTENT_DICT['inform']
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
        nums = pack["numbers"]
        return intent, breakdown, nums

    # MAIN METHOD
    # Returns an understanding and NLP breakdown
    def get_understanding(self, msg, curr_state):
        # Call NLP Model predict
        intent, breakdown, nums = self._NLP_predict(msg)
        print("<GET UNDERSTANDING> NLP intent:",intent)
        # Check intent against background info
        uds = self.intent_to_next_state(curr_state, intent)
        return uds, breakdown, nums

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
        uds = Understanding(intent_obj, default_null_int, SIP.same_state())
        for intent_lst in policy.get_intents():
            if 0: print("intent_list",list(map(lambda x: x[0],intent_lst)))
            for pair in intent_lst:
                c_int, next_sip = pair
                if intent == c_int:
                    if 0 and DEBUG: print("<INTENT MATCH>",intent)
                    uds = Understanding(intent_obj, intent_obj, next_sip)
                    return uds
        return uds

    def zone_policy_overwrite(self, csk, curr_zones):
        def check_zonepolicies(state_key):
            return state_key in self.ZONE_POLICIES

        def determine_subsequent_sip(curr_zones, zpd):
            z_name, paths = zpd
            # Zone policy
            if z_name in curr_zones:
                z_val = curr_zones[z_name]
                if isinstance(z_val, list):
                    return determine_subsequent_sip(curr_zones, z_val)

                else:
                    if z_val in paths:
                        target = paths[z_val]
                    else:
                        target = paths.get("DEFAULT", "")
                    next_sip = self._create_state_obj(target)
                    if DEBUG: print("<ZPOL OVERWRITE> new SIP:",next_sip)
                    return (True, next_sip)
            if DEBUG: print("<ZPOL OVERWRITE> Zone {} not in curr zones: {}".format(z_name, curr_zones))
            return (False, "")

        if 1: print("<ZPOL> curr state key:",csk)

        if check_zonepolicies(csk):
            zpd = self.ZONE_POLICIES[csk]
            return determine_subsequent_sip(curr_zones,zpd)
        else:
            return (False, "")
        

# MANAGES DETAILS
class DetailManager:
    def __init__(self, info_vault,secondary_slots,zonelist):
        self.vault = info_vault
        self.inital_dict = {}
        self.inital_dict["zones"] = {}
        self.chat_prov_info = self.inital_dict
        self.dbrunner = {"dummy"}
        self.dbrunnerset = False
        self.chatID = "PLACEHOLDER_USERID"
        self.zonelist = zonelist
        self.second_slots = secondary_slots

    def set_runner(self, runner):
        self.dbrunner = runner
        self.dbrunnerset = True

    def _set_chatID(self, chatID):
        self.chatID = chatID
        # prev_info = self.dbrunner.fetch_user_info(chatID)
        # self.chat_prov_info.update(prev_info)

    # Adds a zone dict to the supplied dict
    # E.g. "zones":{"city":"shanghai"}
    def _update_zones(self):
        d = self.chat_prov_info
        zones_d = {}
        for zone in self.zonelist:
            if zone in d:
                zones_d[zone] = d[zone]

        if not zones_d == {}: 
            d["zones"].update(zones_d)
        return

    def log_detail(self, new_info, OVERWRITE = 1, DEBUG = 0):
        if DEBUG: print("Logging：", new_info)
        for d in new_info:
            deet = new_info[d]
            # Check to make sure its not empty
            if not deet == "":
                if d in self.chat_prov_info and not OVERWRITE:
                    continue
                else:
                    self.chat_prov_info[d] = new_info[d]
            else:
                # Remove entry if empty
                if d in self.chat_prov_info:
                    print("<LOG DETAIL> Removing empty",d)
                    self.chat_prov_info.pop(d)
                
        self._add_secondary_slots()

        self._update_server_state_info()

        self.write_info_to_db()

        self._update_zones()
        return

    # Info without vault
    def get_user_info(self):
        not_user_info = ["requested_info", "ctx_slots", "zones", "chosen_fee", "work_hrs_flag", "flag_sb_gjj", 'w_shebao_payment', 'shebao_jiaona_total', 'target_month', 'given_amount','city_info'] #TODO find a proper way to store this info in JSON
        dic = self.chat_prov_info.copy()
        for i in not_user_info:
            if i in dic: 
                dic.pop(i)
        return dic
    
    def _update_server_state_info(self):
        dt_now = datetime.now()
        server_info = {}
        server_info["state_curr_hour"] = dt_now.hour
        server_info["state_month"] = dt_now.month
        server_info["state_curr_day"] = dt_now.day
        self.chat_prov_info.update(server_info)
        return

    def _add_secondary_slots(self):
        def mini_calc(raw, branch):
            # Mini calcualtions
            loc, opr, v = branch
            opr = opr.replace(" ","")
            raw = float(raw)
            v = float(v)
            if opr == "-":
                final = raw - v
            elif opr == "+":
                final = raw + v
            else:
                print("<SECONDARY SLOT GETV> unknown opr {}".format(opr))
                final = raw
            return final 

        def get_value(branch, info):
            if isinstance(branch,list):
                raw_vd = dive_for_values(branch,info)
                if raw_vd == {}:
                    if DEBUG: print("<SECONDARY SLOT GETV> {} not found in info".format(branch))
                    final = ""
                else:
                    raw = list(raw_vd.values())[0] # Assume dict is size 1
                    if len(branch) == 3:
                        final = mini_calc(raw, branch)
                    else:
                        final = raw

                return final

            return branch

        def search_through_tree(tree, info, multi):
            def dot_loc_to_list(sn):
                # Converts subdict notation like ctx_slots.ctx_this_month to a list
                if "." in sn:
                    loc_list = sn.split(".")
                    if SUPER_DEBUG: print("<SECONDARY SLOT> LOC LIST", loc_list)
                    slot = loc_list[0]
                else:
                    loc_list = [sn]
                
                slot = loc_list[0]
                return (slot, loc_list)

            def tree_search(t_info):
                any_val_key = "_ANY"
                for slotname, sub_dict in list(tree.items()):
                    slot, loc_list = dot_loc_to_list(slotname)
                    while slot in t_info:
                        # Gets the value from info. Handles nested vals (eg "groupname.detailname")
                        curr_d = t_info
                        for loc in loc_list:
                            infoval = curr_d.get(loc,"")
                            if infoval == "":
                                # IF not found
                                if SUPER_DEBUG: print("<TREE> ERROR {} not found".format(loc))
                                slot_val = ""
                                break
                                
                            elif isinstance(infoval, dict):
                                # If is a subdict
                                curr_d = infoval
                            else:
                                # If found value
                                slot_val = str(curr_d[loc]) # To convert ints to strings. I.e. for hours
                        
                        if SUPER_DEBUG: print("<TREE> Currently looking for:", slot, "value:", slot_val)
                        # Check if value is in the subdict and returns the value of it
                        if slot_val in sub_dict:
                            ss_branch = sub_dict[slot_val]
                            if isinstance(ss_branch, dict):
                                # Is a subtree
                                if SUPER_DEBUG: print("<TREE> Found a subtree",ss_branch, "in",sub_dict)
                                slotname, sub_dict = list(ss_branch.items())[0]
                                slot, loc_list = dot_loc_to_list(slotname)
                                continue

                            else:
                                # Is a leaf
                                out = get_value(ss_branch, t_info)
                                # Cut from info
                                pp = curr_d.pop(loc)
                                if SUPER_DEBUG: print("<TREE> pop leaf",pp)
                                return (True, out)
                        else:
                            # Fallback and look for _ANY match
                            if any_val_key in sub_dict:
                                # Is a _ANY leaf
                                a_branch = sub_dict.get(any_val_key,-1)
                                out = get_value(a_branch, t_info)
                                # Cut from info
                                pp = curr_d.pop(loc)
                                if SUPER_DEBUG: print("<TREE> pop any",pp)
                                return (True, out)

                            if SUPER_DEBUG: print("<SECONDARY SLOT> Val:", slot_val, "not found in:", sub_dict)
                            break
                    
                if SUPER_DEBUG: print("<SECONDARY SLOT> TREE SEARCH FAILED",tree)
                return (False, "")

            tree_info = info.copy()
            if multi:
                collect = []
                found = False
                result = True
                while result:
                    result, val = tree_search(tree_info)
                    if result:
                        collect.append(val)
                        found = True

                return found, collect
            else:
                return tree_search(tree_info)
            

        curr_info = self.fetch_info()
        ss_default_flag = "DEFAULT"
        entries = {}
        for secondslot in self.second_slots:
            target = secondslot["writeto"]
            tree = secondslot["search_tree"]
            multi_f = secondslot.get("multi", False)

            f, val = search_through_tree(tree, curr_info, multi_f)
            if f: 
                entries[target] = val
            elif ss_default_flag in secondslot:
                defval = get_value(secondslot[ss_default_flag], curr_info)
                entries[target] = defval
        
        self.chat_prov_info.update(entries)
        return 

    # Called to get chat info + vault info
    def fetch_info(self):
        out = {}
        out.update(self.chat_prov_info)
        self.vault.add_vault_info(out)
        return out

    def _check_db_init(self):
        if not self.dbrunnerset:
            raise Exception("DatabaseRunner not initalized for DetailManager!")
        return True

    # This is called during the creation of a new chat
    def clone(self, chatID):   
        self._check_db_init()
        clonetrooper = DetailManager(self.vault, self.second_slots, self.zonelist)
        clonetrooper._set_chatID(chatID)
        clonetrooper.set_runner(self.dbrunner)
        prev_info = self.dbrunner.fetch_user_info(chatID)
        clonetrooper.log_detail(prev_info)
        return clonetrooper

    def write_info_to_db(self):
        self._check_db_init()
        chatid = self.chatID
        info_to_write = self.get_user_info()
        self.dbrunner.write_to_db(chatid, info_to_write)
        return

# Generates reply text based on current state info
class ReplyGenerator:
    def __init__(self, formattingDB, humanizer, def_confused):
        self.formatDB = formattingDB
        self.formatter = string.Formatter()
        self.humanizer = humanizer
        self.hflag = True
        self.default_confused = def_confused
        
    # OVERALL METHOD
    def get_reply(self, curr_state, intent, secondslot, info = -1):
        print("<GET_REPLY> INFO",info)
        rdb = self.getreplydb(intent, curr_state, secondslot)
        infoplus = self._enhance_info(curr_state, info)
        reply = self.generate_reply_message(rdb, infoplus)
        return reply

    def _enhance_info(self,curr_state,info):
        RF_DEBUG = 1
        cskey = curr_state["key"]
        rep_ext = {}
        enhanced = info.copy()

        formatDB = self.formatDB["msg_formats"]

        def add_txt_enh(key, rawstr):
            wstr = rawstr.format(**enhanced)
            enhstr = cbsv.conv_numstr(wstr)
            if RF_DEBUG: print("Writing {} to {}".format(rawstr, key))
            cu.add_enh(key,enhstr,rep_ext,"rep_ext",{},enhanced, persist = False)
            if RF_DEBUG: print("<ADD ENH> Intermediate enh:", enhanced)
            return 
        
        def curr_state_needs_txt_enh(tmp,curr_state_key):
            states = tmp["states"]
            return curr_state_key in states

        def get_reply_template(pulled):
            if isinstance(pulled, list):
                return random.choice(pulled)
            return pulled

        def enhance_if_vals(vd, ifvl, tkey):
            def if_val_tree_enh(t_info, name_tree, tkey):
                if isinstance(name_tree, str):
                    # ivtree is a leaf
                    add_txt_enh(tkey,name_tree) # Enhance right away
                    return

                # Branch
                print('<ENHANCE IF VAL> Nametree',name_tree)
                print("<ENHANCE IF VAL2> < vn:", name_tree[0], "< cases:",name_tree[1])

                valname, cases = name_tree 
                case_keys = list(cases.keys())
                    
                if valname in t_info:
                    info_val_value = t_info.get(valname)
                    if isinstance(info_val_value, dict):
                        subtree = info_val_value
                        if RF_DEBUG: print("<ENHANCE IF VAL> Subdict found", subtree)
                        return if_val_tree_enh(t_info, subtree, tkey)

                    if not isinstance(info_val_value, list):
                        info_val_value = [info_val_value]

                    for iv in info_val_value:
                        str_iv = str(cbsv.conv_numstr(iv,wantint=True))
                        print("<ENHANCE IF VAL> Looking for {} in {}".format(str_iv, case_keys))
                        matched = False
                        if str_iv in case_keys:
                            matched = True
                            subtree = cases.get(str_iv)
                            if_val_tree_enh(t_info, subtree, tkey)

                    if not matched:
                        if RF_DEBUG:print ("<ENHANCE IF VAL> No match for ", info_val_value,"in",case_keys)
                        default_branch = cases.get("DEFAULT",False)
                        if default_branch:
                            return if_val_tree_enh(t_info, default_branch, tkey)
                else:
                    if not enstr: raise Exception("<ENHANCE IF VAL> Error {} not in {}".format(valname,info))

                return
            
            print("<ENHANCE IF VAL> Write to:", tkey)
            ifval_list = ifvl.items()
            for name_tree in ifval_list:
                if_val_tree_enh(vd, name_tree, tkey)
                    
            return

        # Message extensions and formatting
        # Template in format database
        for tmp in formatDB:
            if curr_state_needs_txt_enh(tmp,cskey):
                target_key = tmp["writeto"]
                lookout = tmp["lookfor"].copy()
                vd = dive_for_values(lookout, enhanced, failzero=True) # Failzero true for rep ext
                
                if RF_DEBUG: print("<ENH INFO> TMP",tmp)

                ifpr = tmp.get("if_present",{})
                for deet in list(ifpr.keys()):
                    enstr = get_reply_template(ifpr[deet])
                    add_txt_enh(target_key,enstr)
                
                ifvl = tmp.get("if_value",{})
                enhance_if_vals(vd, ifvl, target_key)
        
        print("<ENH POST> Enhanced:", enhanced)
        return enhanced

    # Returns the a reply database either from intent or from state
    def getreplydb(self, intent, curr_state, issamestate):
        def get_hflag(obj):
            # Default is true
            hflag = obj.get("humanify", True)
            return hflag

        def get_replylist(obj):
            if DEBUG: print("<replydb> Pulling reply from:", obj["key"])
            return obj["replies"]
    
        LOCALDEBUG = 0 or DEBUG
        
        if LOCALDEBUG: print("<REPLYDB> Curr State:", curr_state["key"],curr_state["thread"])

        # Decides priority of lookup. 
        # If same state flagged, look at intents first
        # Else look at state based replies
        lookups = [intent, curr_state] if issamestate else [curr_state, intent]

        rdb = []
        # Retrieves the intent object from lookup
        for obj in lookups:
            if obj == cbsv.NO_INTENT():
                # This is for when intent is prioritized before state but no intent is detected
                continue

            if rdb == []:
                rdb = get_replylist(obj) # this may be [] as well
                self.hflag = get_hflag(obj)
            else:
                break
        
        if LOCALDEBUG: print("rdb:",rdb)

        if rdb == []: rdb = self.default_confused # In case really no answer

        return rdb

    # Generates a reply. Purely a string
    def generate_reply_message(self, rdb, info):
        def rand_response(response_list):
            return random.choice(response_list)
        def _humanify(msg, i):
            return self.humanizer.humanify(msg,i)

        reply_template = rand_response(rdb)
        if DEBUG: print("<GEN REPLY> template",reply_template)
        final_msg = reply_template
        if isinstance(info, dict):
            if SUPER_DEBUG: print("<GEN REPLY> Enhanced info:",info)
            
            # Uses kwargs to fill this space
            final_msg = reply_template.format(**info)

        if self.hflag: final_msg = _humanify(final_msg, info)
        return final_msg

# Deals only with text
# Does not deal with state or information
class Chat:
    def __init__(self,chatID, convo_history = {}):
        self.chatID = chatID
        self.blank_chatlot = []
        self.curr_chatlog = self.blank_chatlot.copy()
        self.convo_history = convo_history
        self.convo_index = 0
        self.save_chat_logs = True
        # self.info = {}

    def getID(self):
        return self.chatID

    # Records conversation
    def record_messages(self, recieved, sent):
        dt = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        username = self.chatID + "(客户)"
        human_prefix = lambda user, m: dt+ " > " + user + ": " + m
        robot_prefix = lambda x: dt + " > " + "机器人: " + x
        self.curr_chatlog.append(human_prefix(username, recieved))
        self.curr_chatlog.append(robot_prefix(sent))
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

    # Calls chatbot_be to write the conversation messages to a json
    def record_to_database(self):
        if self.save_chat_logs:
            log = self.get_chatlog()
            chatid = self.chatID
            chatbot_be.record_chatlog_to_json(chatid, log)
            self.clear_chatlot()
        return

    def get_chatlog(self):
        return self.curr_chatlog

    def clear_chatlot(self):
        self.curr_chatlog = self.blank_chatlot.copy()
        return