# All Chat related Classes

import cbsv
import copy
import os
import re
import random
import string

import chatbot_be
from datetime import datetime
from chatbot_supp import *
from chatbot_utils import dive_for_dot_values, dive_for_values, cbround, dotpop


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
        tid = state.get("thread","")
        if tid == "":
            print("<GET THREADID> State has no thread", state)
            raise Exception("THREAD ID EXCEPTION")
        return tid

    # UNUSED. KIV.
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
        self.zkey = "zones"

    def _add_zone(self, z, val):
        # if z in self.zones:
        #     if DEBUG: print("<ADD ZONE> Existing zone {}:{}. Did not write {}.".format(z,self.zones[z],val))
        #     return
        self.zones[z] = val

    # Fetches info from the dm
    def update_zones_from_dm(self, dm):
        all_info = dm.fetch_info()
        if self.zkey in all_info:
            zone_dic = all_info[self.zkey]
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
        self.active = True

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

    def deactivate(self):
        self.active = False

    def is_inactive(self):
        return not self.active
    
    ############### PRIMARY METHOD ###############
    # Takes in a message, returns (text reply, intent breakdown, current info)
    def respond_to_message(self, msg):
        if self.is_inactive():
            no_reply = ""
            return (no_reply, {}, self._get_current_info())

        print("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~&") # For clarity in terminal     
        print("Message recieved:",msg)
        uds, NLP_bd, nums = self._policykeeper_parse(msg)
        
        self.goto_next_state(uds, msg, nums)
        
        calc_ext_dict = self._calculate()
        reply, topup = self._fetch_reply(uds,calc_ext_dict)

        self._record_messages_in_chat(msg,reply)

        self._post_process(uds, topup)

        curr_info = self._get_current_info()
        return (reply, NLP_bd, curr_info)

    def goto_next_state(self, understanding, msg, nums):
        sip = understanding.get_sip()
        d_state_obj = self._sip_to_stateobj(sip)
        intent = understanding.get_orig_intent()

        trigger_repeat = False
        gate_repeat = False
        count = 0
        while True:
            print("<GOTO NEXT STATE> stateobj:", d_state_obj.get("key"))
            # Gatekeeper reqs
            self._get_slots_from_state(d_state_obj)
            # Parse for slots
            self._parse_message_details(msg, intent, nums)
            # Preprocess to fill slots with default vals
            self._gatekeeper_preprocess()
            # Try gate and CHANGE STATE
            pass_gate = self._advance_to_new_state(d_state_obj)
            # Calculate (for crossroads)
            self._calculate() 

            # FINAL state change
            crossroad_traverse, d_state_obj = self._traverse_crossroads(d_state_obj)

            if not pass_gate and not gate_repeat: 
                gate_repeat = True
                trigger_repeat = True

            trigger_repeat = crossroad_traverse or trigger_repeat
            if trigger_repeat and count < 10:
                trigger_repeat = False
                print("<GOTO NEXT STATE> REPEATING", d_state_obj, "count", count)
                count += 1
                continue
            break
        return

    def _traverse_crossroads(self, state):
        ow_flag, next_state = self._xroad_policy_overwrite(state)
        if SUPER_DEBUG: print("<TRAVERSE CROSSROADS> OW flag:", ow_flag, "Next state:", next_state["key"])
        return (ow_flag, next_state)

    def old_respond_to_message(self, msg):
        pass

        if self.is_inactive():
            no_reply = ""
            return (no_reply, {}, self._get_current_info())

        print("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~&") # For clarity in terminal     
        firstpass = True
        pg_fail = False
        for rc in range(0, 5):
            # Parse the message and get an understanding
            full_uds, bd = self._parse_message_overall(msg)
            true_sip = full_uds.get_sip()

            if firstpass:
                firstpass = False
                sip = true_sip # This is to prevent intents (eg affirm) applying more than once
            else:
                sip = sip.same_state()

            # Calls the calculator. Crunch numbers for state change
            if SUPER_DEBUG: print("########################################## LOOP CALCULATOR ##########################################")
            self._calculate()

            state_bef = self._get_curr_state()
            # Digest and internalize the new info
            zone_overwrite, pg = self.react_to_sip(sip) #STATE CHANGE
            state_aft = self._get_curr_state()

            if DEBUG: print("<RTM LOOP> Repeats", rc,"Curr SIP", sip.toString(), "True SIP", true_sip.toString(),"Zone Overwrite",zone_overwrite,"Pass gate:",pg)

            if not pg and not pg_fail:
                pg_fail = True
                continue

            # Breaks
            case1 = (not true_sip.is_trans_state() and not sip.is_same_state()) 
            case2 = state_bef == state_aft
            if case1 or case2:
                if case1 and DEBUG: print("<RTM LOOP> Not trans state, breaking")
                if case2 and DEBUG: print("<RTM LOOP> Same state before and after, breaking")
                break

        # Calls calculator. Crunch numbers for replying
        if SUPER_DEBUG: print("########################################## REPLY CALCULATOR ##########################################")
        calc_ext = self._calculate(double=True)
    
        reply, topup = self._fetch_reply(full_uds, calc_ext)
        
        # Clean up. 
        self._post_process(full_uds, topup)

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
        og_int = uds.get_orig_intent()
        self._parse_message_details(msg, og_int, nums)

        # Preprocess to fill slots with default vals
        self._gatekeeper_preprocess()

        return uds, bd
    
    # Also converts samestate SIP to a state obj
    def _sip_to_stateobj(self, sip):
        if sip.is_same_state():
            if DEBUG: print("<REACTION> SAME STATE FLAGGED")
            self.samestateflag = True
            stateobj = self._get_curr_state()
        else:
            self.samestateflag = False
            stateobj = sip.get_state_obj()
        return stateobj

    # Calculate, zonecheck, gatekeep then internalize changes
    # Converts same_state_obj to the current state.
    # Checks if the state is crossroad and needs to be overwritten
    # Gatekeeper gets requirements from state again in case it changed.
    # Results in change in chat details and change in state
    # Returns boolean indicating whether or not the state was overwritten.
    def react_to_sip(self, sip):
        if sip.is_deactivate():
            self.deactivate()

        stateobj = self._sip_to_stateobj(sip)
        
        if DEBUG: print("<REACTION> Curr state", self._get_curr_state()["key"], "Nxt stateobj", stateobj["key"])
        
        # Check if current target state is in a zone_policy crossroad 
        ow_flag, stateobj = self._xroad_policy_overwrite(stateobj)

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
        pf, rs = self.gatekeeper.try_gate(curr_info)
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
    def _xroad_policy_overwrite(self, og_nxt_state):
        csk = self._get_csk()
        info = self._get_current_info()
        overwrite_flag, ow_state = self.pkeeper.xroad_policy_overwrite(csk,info)
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
    def _fetch_reply(self,uds, calc_ext):
        intent = uds.get_intent()
        info = self._get_current_info()
        info["calc_ext"] = calc_ext #Add calc ext to the info to be passed in

        curr_state = self._get_curr_state()
        if DEBUG: print("<Fetch Reply> Current State",curr_state.get("key","unknown"))
        ssflag = self.samestateflag
        return self.replygen.get_reply(curr_state, intent, ssflag, info)

    # Asks dmanager for info
    def _get_current_info(self):
        return self.dmanager.fetch_info()

     # Gets the next state according to policy
    def _policykeeper_parse(self, msg):
        csk = self._get_csk()
        return self.pkeeper.get_understanding(msg, csk)

    # Asks iparser to parse the message
    def _parse_message_details(self, msg, intent, nums):
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
    def _calculate(self,double=False):
        if SUPER_DEBUG: print("<CALCULATE> CALCULATION CALLED")
        info = self._get_current_info()
        curr_state = self._get_curr_state()
        if SUPER_DEBUG: print("<CALCULATE> Info bef calc", info)
        topup, calc_ext = self.calculator.calculate(curr_state, info)
        if SUPER_DEBUG: print("<CALCULATE> DM TOPUP",topup)
        self.push_detail_to_dm(topup) # Adds persist values to info

        return calc_ext

    # Clears up values based on state information
    def _post_process(self, uds, topup):
        self.push_detail_to_dm(topup)

        sip = uds.get_sip()
        clearlist = sip.get_clears()
        self.push_detail_to_clear(clearlist)
        return 

    ### Detail logging
    def push_detail_to_dm(self, d, ow=1):
        self.dmanager.log_detail(d, OVERWRITE=1)
        self.ztracker.update_zones_from_dm(self.dmanager)
        return 

    # Takes a list of details and asks dmanager to clear them
    def push_detail_to_clear(self, d):
        self.dmanager.clear_details(d)
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
    def __init__(self, policy_rules, crossroad_policies, intent_dict, state_lib,pp):
        self.POLICY_RULES = policy_rules
        self.XROAD_POLICIES = crossroad_policies
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

    def _create_state_obj(self, skey):
        if not skey in self.STATE_DICT:
            raise Exception("<PolicyKeeper> Illegal state:{}".format(skey))
        state_obj = self.STATE_DICT[skey]
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

    def xroad_policy_overwrite(self, csk, info):
        def check_zonepolicies(state_key):
            return state_key in self.XROAD_POLICIES

        def determine_subsequent_sip(curr_info, zpd):
            detail_name, paths = zpd
            # Zone policy
            if detail_name in curr_info:
                z_val = str(curr_info[detail_name]) # Force value to string
                if isinstance(z_val, list):
                    # Subtree
                    return determine_subsequent_sip(curr_info, z_val)
                else:
                    if z_val in paths:
                        target = paths[z_val]
                    else:
                        if SUPER_DEBUG: print("<XROAD POL OVERWRITE> Detail:", detail_name,"Value:", z_val)
                        target = paths.get("DEFAULT")
                    next_sip = self._create_state_obj(target)
                    if DEBUG: print("<XROAD POL OVERWRITE> new SIP:",next_sip)
                    return (True, next_sip)
            if DEBUG: print("<XROAD POL OVERWRITE> Detail {} not in curr_info: {}".format(detail_name, curr_info))
            return (False, "")

        if 1: print("<ZPOLXROAD POL OVERWRITE> curr state key:",csk)

        if check_zonepolicies(csk):
            zpd = self.XROAD_POLICIES[csk]
            return determine_subsequent_sip(info,zpd)
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

    # Adds a zone dict to the supplied dict
    # E.g. "zones":{"city":"shanghai"}
    def _update_zones_local(self):
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
                ds = [d] # list
                self.clear_details(ds)
                
        self._add_secondary_slots()

        self._update_server_state_info()

        self.write_info_to_db()

        self._update_zones_local()
        return

    # Given a list of values, clears it
    def clear_details(self, detail_list):
        for d in detail_list:
            if d in self.chat_prov_info:
                print("<CLEAR DETAIL> Removing empty",d)
                self.chat_prov_info.pop(d)
        return

    # Info without vault
    def get_user_info(self):
        relevant_user_info = {
            "city", "city_district", "要社保", "要公积金", 
            "首次","shebao_jishu", "gjj_jishu", 
            "svc_fee_total", "shebao_basic_total",
            "made_purchase", "苏州区", "北京农城"
        } # HARDCODED
        not_user_info = [
            "requested_info", "ctx_slots", "zones", "chosen_fee", "work_hrs_flag", 
            "flag_sb_gjj", 'w_shebao_payment', 'shebao_jiaona_total', 
            'target_month', 'given_amount','city_info', "ss_purchase_cmi_flag",
             "exclude_svc_fee", "w_fee_type_flag", "w_normal_cmi_flag",
             "bill_settled_flag", "w_spec_component_value", "ss_jishu_amount", 
        ] #TODO find a proper way to store this info in JSON # HARDCODED
        dic = {}
        chat_info = self.chat_prov_info
        for key, contents in chat_info.items():
            if key in relevant_user_info: 
                dic[key] = contents
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
        def mini_calc(branch, info):
            # Mini calcualtions
            a_loc, opr, b_loc, dp = branch
            opr = opr.replace(" ","")
            raw_a = dive_for_dot_values(a_loc,info, DEBUG=SUPER_DEBUG, as_val = 1)
            if isinstance(b_loc, float) or isinstance(b_loc, int):
                raw_b = b_loc
            else:
                raw_b = dive_for_dot_values(b_loc,info, DEBUG=SUPER_DEBUG, as_val = 1)
            bv = float(raw_b)
            av = float(raw_a)

            if opr == "-":
                final = av - bv
            elif opr == "+":
                final = av + bv
            else:
                print("<SECONDARY SLOT GETV> unknown opr {}".format(opr))
                final = av
            final = cbround(final, dp) # Round to specified dp
            if SUPER_DEBUG: print("<SS MINI CALC>", av, opr,bv,"=",final)
            return final 

        def get_value(branch, info):
            if isinstance(branch,list):
                minicalc_bool = len(branch) > 1
                
                if minicalc_bool:
                    final = mini_calc(branch, info)
                else:
                    final = dive_for_dot_values(branch, info, DEBUG=SUPER_DEBUG, as_val = 1)
                
                if final == {}:
                    if DEBUG: print("<SECONDARY SLOT GETV> {} not found in info".format(branch))
                    final = ""
                return final

            # If not, is a raw value
            return branch

        def search_through_tree(tree, info, multi):
            def tree_search(tree, t_info):
                any_val_key = "_ANY"
                for slotname, sub_dict in list(tree.items()):
                    curr_d = t_info
                    # If finds something, returns. If not, breaks.
                    while True:
                        dive_dir = dive_for_dot_values(slotname, curr_d) # As dict
                        if dive_dir == {}:
                            # IF not found
                            # if SUPER_DEBUG: print("<SS TREE> ERROR {} not found".format(str(slotname)))
                            slot_val = ""
                            break

                        loc, slot_val = list(dive_dir.items())[0]
                        slot_val = str(slot_val) # To convert ints to strings. I.e. for hours
                        
                        # if SUPER_DEBUG: print("<SS TREE> Current slot:", loc, "| val:", slot_val)
                        # Check if key is in the subdict
                        if slot_val in sub_dict:
                            ss_branch = sub_dict[slot_val]
                            if isinstance(ss_branch, dict):
                                # Is a subtree
                                # if SUPER_DEBUG: print("<SS TREE> Found a subtree",ss_branch, "in",sub_dict)
                                slotname, sub_dict = list(ss_branch.items())[0]
                                continue

                            else:
                                # Is a leaf
                                out = get_value(ss_branch, t_info)
                                # Cut from info
                                pp = cu.dotpop(loc, curr_d)
                                # if SUPER_DEBUG: print("<SS TREE> pop leaf",pp)
                                return (True, out)
                        else:
                            # Fallback and look for _ANY match
                            a_branch = sub_dict.get(any_val_key,-1)
                            if not a_branch:
                                # Search failed
                                # if SUPER_DEBUG: print("<SS TREE> Val:", slot_val, "not found in:", sub_dict)
                                break

                            if isinstance(a_branch, dict):
                                # Is a _ANY branch
                                slotname, sub_dict = list(a_branch.items())[0]
                                continue

                            else:
                                # Is a _ANY leaf
                                out = get_value(a_branch, t_info)
                                # Cut from info
                                pp = cu.dotpop(loc, curr_d)
                                # if SUPER_DEBUG: print("<SS TREE> pop _ANY leaf",pp)
                                return (True, out)
                    
                # if SUPER_DEBUG: print("<SECONDARY SLOT> TREE SEARCH FAILED",tree)
                return (False, "")

            tree_info = copy.deepcopy(info)
            if multi:
                # Multiple slot
                collect = []
                while True:
                    result, val = tree_search(tree, tree_info)
                    if not result: break # Once cannot find, break
                    collect.append(val)
                found = not (collect == [])
                return found, collect
            else:
                return tree_search(tree, tree_info)
            
        curr_info = self.fetch_info()
        ss_default_flag = "DEFAULT" # HARDCODED
        entries = {}
        for secondslot in self.second_slots:
            target = secondslot["writeto"]
            tree = secondslot["search_tree"]
            multi_flag = secondslot.get("multi", False)

            f_flag, val = search_through_tree(tree, curr_info, multi_flag)
            if f_flag:
                entries[target] = val
            elif ss_default_flag in secondslot:
                defval = get_value(secondslot[ss_default_flag], curr_info)
                if defval == "":
                    continue
                else:
                    entries[target] = defval
        
        if SUPER_DEBUG: print("<SS TREE SEARCH> Entries:",entries)
        self.chat_prov_info.update(entries)
        return 

    # Called to get chat info + vault info
    def fetch_info(self):
        out = {}
        out.update(self.chat_prov_info)
        self.vault.add_vault_info(out)
        # if SUPER_DEBUG: print("<FETCH INFO> CTX SLOTS", out.get("ctx_slots","")) #DEBUG
        return out

    def _check_db_init(self):
        if not self.dbrunnerset:
            raise Exception("DatabaseRunner not initalized for DetailManager!")
        return True

    # Checks with DB Runner for if the User is a laoke. Writes to the laokehu_flag
    def check_database_for_user(self, userID):
        found, prev_info = self.dbrunner.fetch_user_info(userID)
        lkh_val = "yes" if found else "no" # HARDCODED!!
        prev_info["laokehu_flag"] = lkh_val # HARDCODED!!
        self.log_detail(prev_info)
        return 

    # This is called during the creation of a new chat
    def clone(self, chatID):   
        self._check_db_init()
        clonetrooper = DetailManager(self.vault, self.second_slots, self.zonelist)
        clonetrooper._set_chatID(chatID)
        clonetrooper.set_runner(self.dbrunner)
        clonetrooper.check_database_for_user(chatID)
        return clonetrooper

    def write_info_to_db(self):
        self._check_db_init()
        chatid = self.chatID
        info_to_write = self.get_user_info()
        self.dbrunner.write_to_db(chatid, info_to_write)
        return

# Generates reply text based on current state info
class ReplyGenerator:
    def __init__(self, formattingDB, humanizer, announcer, def_confused):
        self.formatDB = formattingDB
        self.formatter = string.Formatter()
        self.humanizer = humanizer
        self.announcer = announcer
        self.hflag = True
        self.default_confused = def_confused
        
    # OVERALL METHOD
    def get_reply(self, curr_state, intent, secondslot, info = -1):
        if DEBUG: print("<GET_REPLY> INFO calc_ext:",info.get("calc_ext", {}), "rep_ext", info.get("rep_ext", {}))
        rdb = self.getreplydb(intent, curr_state, secondslot)
        infoplus = self._enhance_info(curr_state, info)
        reply, topup = self.generate_reply_message(rdb, curr_state, infoplus)
        return reply, topup

    def _enhance_info(self,curr_state,info):
        RF_DEBUG = 0 or SUPER_DEBUG # DEBUG FLAG
        cskey = curr_state["key"]
        rep_ext = {}
        enhanced = copy.deepcopy(info)

        formatDB = self.formatDB["msg_formats"]

        def add_txt_enh(key, rawstr):
            wstr = rawstr.format(**enhanced)
            enhstr = cbsv.conv_numstr(wstr)
            if RF_DEBUG: print("Writing {} to {}".format(rawstr, key))
            cu.add_enh(key,enhstr,rep_ext,"rep_ext",{},enhanced, persist = False)
            return 
        
        def curr_state_needs_txt_enh(tmp,curr_state_key):
            states = tmp["states"]
            return curr_state_key in states

        def get_reply_template(pulled):
            if isinstance(pulled, list):
                return random.choice(pulled)
            return pulled

        def enhance_if_vals(vd, ifvl, tkey):   
            # Recursive function
            def if_val_tree_enh(t_info, name_tree, tkey):
                def enhance_end_branch(branch):
                    if isinstance(branch, str):
                        # ivtree is a leaf
                        add_txt_enh(tkey,branch) # Enhance
                        return

                    if isinstance(branch, list):
                        # ivtree is a leaf list
                        enhstr = get_reply_template(branch)
                        add_txt_enh(tkey,enhstr) # Enhance chosen string
                        return
                def search_tree_and_enhance(cases, valname):
                    case_keys = list(cases.keys())
                    info_val_value = t_info.get(valname)

                    if isinstance(info_val_value, dict):
                        subtree = info_val_value
                        if RF_DEBUG: print("<ENHANCE IF VAL> Subdict found", subtree)
                        return if_val_tree_enh(t_info, subtree, tkey) # RECURSIVE CALL

                    if not isinstance(info_val_value, list):
                        info_val_value = [info_val_value]

                    # Go through curr_info values
                    for iv in info_val_value:
                        str_iv = str(cbsv.conv_numstr(iv,wantint=True)) # Convert info value to string because json keys are strings
                        if RF_DEBUG: print("<ENHANCE IF VAL> Val:{} Looking for {} in cases: {}".format(valname, str_iv, case_keys))
                        matched = False
                        # Try to match curr_info values with tree cases
                        if str_iv in case_keys:
                            matched = True
                            subtree = cases.get(str_iv)
                            if_val_tree_enh(t_info, subtree, tkey)

                    if not matched:
                        if RF_DEBUG: print("<ENHANCE IF VAL> No match for",info_val_value,"in cases:",case_keys)
                        
                        default_branch = cases.get("DEFAULT", None)

                        # Check this way because DEFAULT can be blank
                        if not default_branch == None:
                            if RF_DEBUG: print("<ENHANCE IF VAL> Returning default value")
                            return if_val_tree_enh(t_info, default_branch, tkey)
                        raise Exception("<ENHANCE IF VAL> No value to write to {}".format(tkey))
                    else:
                        return

                if not isinstance(name_tree, dict):
                    # Break case
                    enhance_end_branch(name_tree)
                else:
                    # Search case
                    if RF_DEBUG: print('<ENHANCE IF VAL> Nametree',name_tree)
                    iv_trees = list(name_tree.items())
                    for valname, cases in iv_trees:
                        # Get all the limbs of the tree
                        if valname in t_info:
                            # If specified value is present
                            search_tree_and_enhance(cases, valname)
                        else:
                            raise Exception("<ENHANCE IF VAL> Error {} not in {}".format(valname,t_info))

                    return
            
            if RF_DEBUG: print("<ENHANCE IF VAL> Write to:", tkey)
            if_val_tree_enh(vd, ifvl, tkey)
                    
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
        
        if RF_DEBUG: print("<ENH POST> Enhanced:", enhanced)
        return enhanced

    # Returns the a reply database either from intent or from state
    def getreplydb(self, intent, curr_state, issamestate):
        def get_hflag(obj):
            # Default is true
            hflag = obj.get("humanify", True) # HARDCODED
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

        if rdb == []: rdb = self.default_confused # In case really no answer. Not to be confused with intentionally blank answers.

        return rdb

    # Generates a reply. Purely a string
    def generate_reply_message(self, rdb, curr_state, info):
        def rand_response(response_list):
            return random.choice(response_list)
        def _humanify(msg):
            if not self.hflag:
                # Do nothing
                return msg 
            return self.humanizer.humanify(msg,info)
        def _announceify(msg):
            return self.announcer.add_announcements(msg,curr_state,info)

        reply_template = rand_response(rdb)
        if DEBUG: print("<GEN REPLY> Template:",reply_template)
        if SUPER_DEBUG: print("<GEN REPLY> Enhanced info:",info)
        
        # Pre-enhancement additions to base template
        reply_template, topup = _announceify(reply_template)

        # Uses kwargs to fill the reply slots
        final_msg = reply_template.format(**info)

        # Post-enhancement message additions
        final_msg = _humanify(final_msg)
        
        return final_msg, topup

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

    # Calls chatbot_be to write the conversation messages to a json
    def record_to_database(self):
        if self.save_chat_logs:
            log = self.get_chatlog()
            chatid = self.chatID
            print("WRITING TO DB:", log)
            chatbot_be.record_chatlog_to_json(chatid, log)
            self.clear_chatlot()
        return

    def get_chatlog(self):
        return self.curr_chatlog

    def clear_chatlot(self):
        self.curr_chatlog = self.blank_chatlot.copy()
        return