import cbsv
import re
import copy
import chatbot_utils as cu

SUPER_DEBUG = 0
DEBUG = 1
CALCULATOR_DEBUG = 0

DEBUG = DEBUG or SUPER_DEBUG

# Have a message class? Or some sort of flag for messages. Indicate state-changing messages.
PREV_STATE_F = {"key":"299 PREV_STATE", "gated": False} # HARDCODED
SAME_STATE_F_OBJ = {"key":"same_state","gated":False} # HARDCODED

# SIP = State Info Packet
# A packet that has info about state and has constructors for set states like go_back
class SIP:
    trans_state_flag = "transition_state" # HARDCODED
    def __init__(self, state, cs = True):
        self.parse_state(state)
        self.state_change = cs
        self.backtrack = False
        self.go_back = False

    def parse_state(self, state):
        self.state_obj = state.copy() # Prevent unintended side effects. States are dicts
        self.state_key = self.state_obj["key"]
        self.gated_bool = self.state_obj.get("gated",False)
        self.transition_state = self.state_obj.get(self.trans_state_flag,False)
        self.state_slots = self.state_obj["req_info"] if self.gated_bool else []
        self.state_clears = self.state_obj.get("clear_info",[])
        self.pending_state = ""
        self.deactivate = self.state_obj.get("deactivate_state", False) # HARDCODED

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

    def get_clears(self):
        return self.state_clears.copy()

    @classmethod
    def same_state(cls):
        obj = cls(SAME_STATE_F_OBJ, cs=False)
        return obj
    
    @classmethod
    def exit_pocket(cls):
        # TODO this
        obj = cls(PREV_STATE_F, cs=False)
        return obj

    def is_same_state(self):
        return not self.state_change

    def is_trans_state(self):
        return self.transition_state

    def is_deactivate(self):
        return self.deactivate

    def toString(self):
        return ("State key",self.state_key,"cs",self.state_change, "slots",self.state_slots)

# A vehicle to house SIP and intent.
class Understanding:
    def __init__(self, original_intent_obj, intent_obj, sip):
        self.og_intent = original_intent_obj
        self.intent = intent_obj
        self.sip = sip
        self.details = {}

    def get_intent(self):
        return self.intent

    def get_orig_intent(self):
        return self.og_intent

    def get_sip(self):
        return self.sip
    
    def get_sip_slots(self):
        return self.sip.get_slots()

    def printout(self):
        print("UNDERSTANDING OBJ PRINTOUT Intent: ", self.intent, " SIP: ", self.sip.toString())

class ReqGatekeeper:
    def __init__(self, conds, default_slot_vals):
        self.requirements = []
        self.slots = []
        self.gate_closed = False
        self.conds = conds
        self.default_slot_vals = default_slot_vals
        self.def_slot_flag = "DEFAULT_SV" # HARDCODED

    def open_gate(self):
        self.gate_closed = False
        self.slots = []
        self.requirements = []

    def close_gate(self):
        self.gate_closed = True

    def get_slots(self):        
        return self.slots.copy()

    def _get_slots_name_list(self, sl):
        return list(map(lambda x: x[0],sl))

    def get_slot_names(self):
        return self._get_slots_name_list(self.get_slots())

    def get_default_slots(self):
        slots = self.get_slots()
        out = list(filter(lambda x: x[1] == self.def_slot_flag,slots))
        return out

    def get_def_slot_names(self):
        return self._get_slots_name_list(self.get_default_slots())

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
                    if SUPER_DEBUG: print("<CONDITIONAL REQS>f,fval,val",fetch, fetched,val) 
                    if fetched[0] == val:
                        for slot in slots_list:
                            if not slot[0] in self.get_slot_names():
                                if DEBUG: print("<CONDITIONAL REQS> Update COND slots: ", slot)
                                self.slots.append(slot)
                        break

    @classmethod
    def slots_to_reqs(cls, slots):
        def getname(s):
            return s[0]
        reqlist = []
        for slot in slots.copy():
            reqlist.append(getname(slot))
        if DEBUG: print("<slots_to_reqs> return:", reqlist)
        return reqlist  

    def get_requirements(self):
        return self.requirements.copy()

    def scan_SIP(self, sip):
        so = sip.get_state_obj()
        return self.scan_state_obj(so)

    def scan_state_obj(self, state_obj):
        if "gated" not in state_obj:
            return

        slots = state_obj.get('req_info',[])
        if not state_obj["gated"] or len(slots) < 1:
            return
       
        self.close_gate()
        self.slots = slots
        if DEBUG: print("<SCAN STATE OBJ> slots:",slots)
        self.requirements = ReqGatekeeper.slots_to_reqs(self.slots)      

    def _get_unfilled_slots(self, info):
        slots = self.get_slots()
        uf_slots = slots.copy()
        for s in uf_slots.copy():
            detail = s[0]
            if detail in info:
                uf_slots.remove(s)
        return uf_slots

    # If pass, returns True, (Pending state)
    # If fail, returns False, (Next state)
    def try_gate(self, info):
        def is_passed(us):
            return (len(us) == 0)

        if not self.gate_closed:
            # If the gate is open
            passed = True
            unfilled_slots = []

        else:
            self._add_cond_reqs(info)

            if SUPER_DEBUG: print("<TRY GATE> Trying with info:",info, "required:",self.get_requirements())
            # for catgry in list(info.keys()):
            unfilled_slots = self._get_unfilled_slots(info)

            if DEBUG: print("<TRY GATE> Unfilled_slots:",unfilled_slots)
            if len(unfilled_slots) == 0:
                self.open_gate()

            passed = is_passed(unfilled_slots)
        
        return (passed, unfilled_slots)

    # For now this fills default slots with their default values.
    def preprocess(self, curr_info):
        unfilled_slots = self._get_unfilled_slots(curr_info)
        topup = self.assign_default_values(unfilled_slots)[1]
        return topup

    def assign_default_values(self, unfilled):
        def is_default(s):
            return s[1] == self.def_slot_flag

        post_unfilled = unfilled.copy()
        info_topup = {}
        for slot in unfilled.copy():
            if SUPER_DEBUG: print("<DEFAULT VALS> curr slot",slot,"is def:", is_default(slot))
            if is_default(slot):
                slotname, slot_type_UNUSED = slot
                if slotname in self.default_slot_vals:
                    val = self.default_slot_vals[slotname]
                    info_topup[slotname] = val
                    post_unfilled.remove(slot)
                    if DEBUG: print("<DEFAULT VALS> {} assigned default value: {}".format(slotname, val))
        if DEBUG: print("<DEFAULT VALS> post top up", info_topup)
        return (post_unfilled, info_topup)

class Humanizer():
    def __init__(self,human_dict):
        self.hd = human_dict.items()
    
    def humanify(self, msg, info):
        def add_humanlike_text(iv, d, in_msg):
            specific_dict = d[iv]
            pos = specific_dict["location"]
            txt = specific_dict["text"]
            if pos == "START":
                return txt + in_msg
            elif pos == "END":
                return in_msg + txt
            return in_msg

        human_msg = msg
        ctx_key = InfoParser.CTX_SLOT_KEY()
        ctx_info = info.get(ctx_key,{})
        for key, dic in self.hd:
            inf_val = ctx_info.get(key,"")
            if inf_val in dic:
                human_msg = add_humanlike_text(inf_val, dic, human_msg)
            
        return human_msg

class Announcer():
    def __init__(self,announce_list):
        self.al = announce_list
        self.subdict_key = "announce_flags"

    def get_announce_subdict(self, inf):
        sdk = self.subdict_key
        return inf.get(sdk,{})
    
    def get_announce_list(self, cstate, cinfo):
        def get_flag(a):
            ak = a["key"]
            sd = self.get_announce_subdict(cinfo)
            return sd.get(ak,0)

        def _make_entry(ann):
            repeat = ann.get("repeat",True)
            flagged = get_flag(ann)
            entry = {}
            make = False
            if repeat or not flagged:
                # Only fail is no repeat + flagged
                entry["key"] = ann["key"]
                entry["text"] = ann["text"]
                entry["pos"] = ann["position"]
                make = True
            return make, entry

        def _check_condition(an):
            csk = cstate["key"]
            curr_info = cinfo
            t_slots = an["trigger_slots"]
            t_states = an["trigger_states"]
            
          
            trigger_states = t_states
            correct_state = "_ANY" in trigger_states or csk in trigger_states
            
            if correct_state:
                slots_satisfied = False
                for ts in t_slots:
                    slot_is_AND = (ts.get("eval","AND") == "AND") # Default is AND
                    sn = ts.get("slotname","")
                    ex_val = ts["value"]
                    info_vd = cu.dive_for_dot_values(sn, curr_info)
                    if len(info_vd) == 0:
                        if SUPER_DEBUG: print("<ANNOUNCE> Slot",sn,"not found in info")
                    info_val = info_vd.get(sn,"")
                
                    if info_val == ex_val:
                        slots_satisfied = True
                    elif slot_is_AND:
                        # ALL slot values must be satisfied
                        return False # One fail all fail
                        
                        
                
                return slots_satisfied
            return False
            
        anns_to_make = []
        for ann in self.al:
            make_a = _check_condition(ann)
            if make_a:
                mf, entry = _make_entry(ann)
                if mf: anns_to_make.append(entry)
        return anns_to_make
    
    def add_announcements(self, msg, state, info):
        sdk = self.subdict_key
        sd = self.get_announce_subdict(info)

        def flag_annoucement(a):
            ak = a["key"]
            sd[ak] = 1

        def make_topup():
            # Create topup subdict
            tup = {}
            tup[sdk] = sd
            return tup

        def add_announcement_text(in_msg, ann):
            pos = ann["pos"]
            ann_text = ann["text"]
                
            if pos == 0:
                return ann_text + " " + in_msg
            elif pos == 1:
                return in_msg + " " + ann_text
            return in_msg
        alist = self.get_announce_list(state, info)
        
        out_msg = msg

        if SUPER_DEBUG: print("<ANNOUNCE>",out_msg, "| announcement list", alist)
        for announcement in alist:
            out_msg = add_announcement_text(out_msg, announcement)
            flag_annoucement(announcement)

        topup = make_topup()
        return out_msg, topup

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
        self.vault_info = json_data["vault_info"]
        self.general_info = self.vault_info["general_info"]
        self.lookup_info = self.vault_info["lookup_info"]
        self.db_protocol = self.vault_info.get("database_protocol")
        self.slot_list = list(self.lookup_info.keys())
    
    # Modifies the dict directly
    def add_vault_info(self, chatinf):
        self._add_lookup_info(chatinf)
        self._add_general_info(chatinf)
        return

    def _add_lookup_info(self, chatinfo):
        def add_entry(s):
            chatval = chatinfo[s] # Chat provided value
            v_subdict = self.lookup_info[s]
            t_key = v_subdict["writeto"]
            if chatval in v_subdict:
                v_info = v_subdict[chatval]
                entry = {t_key:v_info}
                # if DEBUG: print("<ADD VAULT INFO> entry",entry,t_key,":",v_info)
                chatinfo.update(entry)
        # if DEBUG: print("<ADD VAULT INFO> list:",self.slot_list)
        for s in self.slot_list:
            if s in chatinfo:
                add_entry(s)
                
        return

    def _add_general_info(self, ci):
        gen_info = {"general_info":self.general_info}
        ci.update(gen_info)
        return
        
    def _get_db_protocol(self):
        return self.db_protocol
        
# Takes in a message and returns some info (if any)
# Note: thing about re.search is that only the first match is pulled.
class InfoParser():
    def __init__(self, json_dict):
        self.digits = cbsv.DIGITS()
        self.ctxsk = self.CTX_SLOT_KEY()
        self.regexDB = {}
        self.perm_slots = json_dict["permanent_slots"]
        self.ctx_slots = json_dict["contextual_slots"]
        self.pos_slots = json_dict["pos_slots"]
        slots = json_dict["slots"]
        self._build_slots_DB(slots)

    @classmethod
    def CTX_SLOT_KEY(cls):
        return "ctx_slots" # HARDCODED

    def _build_slots_DB(self, jdata):
        for catkey in list(jdata.keys()):
            obj = jdata[catkey]
            cached_slot = {}
            # Multi flag
            cached_slot["multi"] = obj.get("multi",False) # False by default
            
            # Get category regex
            category = obj.get("map", {})
            if category == {}:
                if SUPER_DEBUG: print ("<BUILD SLOTS DB> ERROR NO CATEGORY FOR {}".format(catkey))
                continue 
            cat_map = {}
            for value in list(category.keys()):
                termlist = category[value]
                regexlist = self.list_to_regexList(termlist)
                cat_map[value] = regexlist
            cached_slot["map"] = cat_map

            self.regexDB[catkey] = cached_slot

    def _parse_pos_slots(self, text, out):
        def pos_regex(pattern, grp_num):
            match = re.search(pattern, text)
            if match:
                val = match.group(grp_num)
            else:
                val = ""
            return val

        vsl = self.pos_slots
        out_dict = {}
        for vs in vsl:
            pattern = vs.get("map")
            grp_num = vs.get("group_pos")
            pv = pos_regex(pattern, grp_num)
            if not pv == "":
                print("<VAL SLOTS> PV", pv)
                wk = vs.get("key")
                out_dict[wk] = pv

        out.update(out_dict)

    # Updates dict directly
    def _match_slot(self, text, slot, d, PDB = True):
        slotname, catgry = slot
        value = self.get_category_value(text, catgry, PDB)
        if len(value) > 0:
            if SUPER_DEBUG: print("<MATCH SLOT> Found a {} for {} Value: {}".format(catgry, slotname,value))
            entry = {slotname: value}
            d.update(entry)

    def _parse_function(self, text, d, slots, PDB = True):
        for s in slots:
            self._match_slot(text, s, d, PDB)
        
    # Searches in permanent aka default slots
    def _default_parse(self, text, d, PDB = True):
        self._parse_function(text, d, self.perm_slots, PDB)
        return

    # Searches in contextual slots
    def _contextual_parse(self, text, d):
        if not self.ctxsk in d:
            d[self.ctxsk] = {}
        ctx_d = d[self.ctxsk]
        self._parse_function(text,ctx_d,self.ctx_slots)
        return

    def _no_match_val(self, catDB):
        keyword = "NO_MATCH" # HARDCODED
        defval = ""
        if keyword in catDB:
            defval = catDB[keyword]
        
        return defval

    # Get slot value from intent
    def _intent_blanket_slotfill(self, intent, slots, d):
        int_slotpairs = intent.get("slotfills",[])
        out = {}
        for fillslotname, slottype in slots:
            if slottype in int_slotpairs:
                filval = int_slotpairs[slottype]
                out[fillslotname] = filval
        d.update(out)
        return

    # Get the value in the text related to the specified category
    # Enumerated by dictionary key
    # Returns a pure value
    def get_category_value(self, text, category, PDB = True):
        if not category in self.regexDB:
            if "DEFAULT" in category:
                return ""

            if PDB and DEBUG: print("<GET CAT VAL> No such category:{}".format(category))
            return ""
        slot_obj = self.regexDB[category]
        mf = slot_obj["multi"]
        add_to_val = lambda v, token: v.append(token) if mf else (v.insert(0,token))
        catDB = slot_obj["map"]
        match_list = [self._no_match_val(catDB)]

        found = False
        vals = list(catDB.keys())
        for v in vals:
            reDB = catDB[v]
            m = re.search(reDB, text)
            if m:
                if PDB and SUPER_DEBUG: print("<GET CAT VAL> Matched {} value:{} at {}".format(category,v,m))
                if found:
                    if PDB: print("<GET CAT VAL> Double value. Prev:", match_list, ", Current:",v)
                    if mf:
                        add_to_val(match_list, v)
                    continue
                else:
                    match_list.pop(0) # Remove default value
                    add_to_val(match_list, v)
                    found = True
                    # if DEBUG: print("<PARSER> Found a ", category, ":", v)
        
        if not mf:
            value = match_list[0]
        else:
            if found:
                value = match_list
            else:
                value = ""
        return value

    ### MAIN FUNCTION ### 
    # Returns a dict of primary lookup_info including zones.
    def parse(self, text, slots, intent):
        if not isinstance(intent, dict):
            return {}
        out = {}
        # Intent slotfill
        self._intent_blanket_slotfill(intent, slots, out)
        # State Slot parse
        self._parse_function(text, out, slots)
        # Permanent slot parse (overwrites existing slots)
        self._default_parse(text,out)
        # Positional slots
        self._parse_pos_slots(text,out)
        # Contextual parse
        self._contextual_parse(text, out)
        # if DEBUG: print("<PARSE> Final details:",out)
        return out

    def parse_chat_history(self, history):
        out = {}
        in_order_history = history.copy()
        in_order_history.reverse()
        
        # Permanent slot parse (overwrites existing slots)
        for msg in in_order_history:
            self._default_parse(msg, out, PDB = False)
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

class Calculator():
    def __init__(self, formulae):
        self.DEBUG = CALCULATOR_DEBUG
        self.SUPER_DEBUG = SUPER_DEBUG

        self.req_var_key = "req_vars"
        self.outputs_key = "writeto"
        self.pv_key = "persist_value"
        self.std_output_key = "OUTCOME"

        self.formula_db = formulae
        self.build_output_db(self.formula_db)
        self.feedback_count = 0
        return

    # Resets all local/working values used for calculation
    def reset_calc_cache(self):
        self._reset_precalc_list()
        self.l_calc_ext = {}
        self.calc_topup = {}

    def _reset_precalc_list(self):
        self.precalc_list = []
        
    def add_precalc(self, calcname):
        self.precalc_list.append(calcname)
    
    def check_precalc_skip(self, calcname):
        return calcname in self.precalc_list

    # Builds a lookup table of Output -> Formula Key (name)
    def build_output_db(self, fdb):
        def _make_key(fname, pv):
            ext = "calc_ext." #Extension for non persist values
            if pv:
                return fname
            else:
                return ext + fname

        def insert_entry(deet_key, pv, fname, d):
            op_key = _make_key(deet_key, pv)
            d[op_key] = fname
        
        def extract_dkey(opline):
            return opline[0]

        table = {}
        for fname, formula in list(fdb.items()):
            outputs = self._get_writeto(formula)
            pv = self._get_persist_value(formula)
            if not isinstance(outputs,list):
                deet_key = outputs
                insert_entry(deet_key, pv, fname, table)
            else:
                for op in outputs:
                    deet_key = extract_dkey(op)
                    insert_entry(deet_key, pv, fname, table)

        self.outputs_lookup = table
        print("OUTPUT DB", table)
        return

    # Main Callable function #
    # Returns the topup dict and the calc_extension dict
    def calculate(self, curr_state, curr_info):
        self.feedback_count = 0
        self.reset_calc_cache()
        self._do_all_calculations(curr_state, curr_info)
        return (self.calc_topup, self.l_calc_ext)
    
    # Looks through the formula table to get a list of formulas that must be executed before proceeding
    def trace_req_vars(self, req_vars):
        fkey_queue = []
        formula_set = {}
        for rq_v in req_vars:
            if rq_v in self.outputs_lookup:
                fkey = self.outputs_lookup[rq_v]
                if not fkey in formula_set:
                    # Prevent repeat of same formulas
                    formula_set[fkey] = 1
                    fkey_queue.append(fkey)
        return fkey_queue

    def _get_req_vars(self, f):
        rvs = f.get(self.req_var_key, [])
        return rvs

    def _get_persist_value(self,f):
        return f.get(self.pv_key,False)
        
    def _get_writeto(self, f):
        return f.get(self.outputs_key, [])
    
    def _get_calcs(self, state):
        return state.get("calcs", [])

    # Get formula obj from dict
    def _get_formula_obj(self, fname):
        frm = self.formula_db.get(fname, "")
        if frm == "":
            err = "<RESOLVE FORMULA> ERROR! No such formula:{}".format(fname)
            cu.log_error(err)
            raise Exception("RESOLVE FORMULA ERROR")
        return frm

    # Traces required variables and executes whatever produces the variables
    def precalculate(self, f, info):
        rvs = self._get_req_vars(f)
        fkey_list = self.trace_req_vars(rvs)
        self.debug_print("<PRECALCULATING>" + str(fkey_list))
        for fkey in fkey_list:
            if not self.check_precalc_skip(fkey):
                self.add_precalc(fkey)
                self.new_resolve_formula(fkey, info) # This calls precalculate
                
        return

    # Performs calculations and formats text message replies 
    ############## Major function ##############
    def _do_all_calculations(self, curr_state, info):
        CALC_DEBUG = self.DEBUG
        CALC_SUPER_DEBUG = self.SUPER_DEBUG
        enhanced = info.copy()
        
        ### MAIN METHOD LOGIC ###
        # Calculations
        state_calcs = self._get_calcs(curr_state)
        for fname in state_calcs:
            self.new_resolve_formula(fname, enhanced)
            # if CALC_DEBUG: print("<RESOLVE FORMULA> Intermediate enh",enhanced)
        
        if CALC_SUPER_DEBUG: print("<RESOLVE FORMULA> Postcalc enh",enhanced)
        if state_calcs == [] and CALC_DEBUG: print("<RESOLVE FORMULA> No calculation performed")
        
        return
        
    def detect_inf_feedback(self):
        limit = 10
        self.feedback_count += 1
        return self.feedback_count > limit
    
    def _assign_outputs(self, result_dict, formula, enhanced):
        self.debug_print("<ASSIGN OUTPUTS>"+str(result_dict))
        target_key = self._get_writeto(formula)
        pv_flag = self._get_persist_value(formula)
        
        # Auto includes l_calc_ext and calc_topup
        def add_calc_enh(key, rawstr, rnd = 2, _pv = False):
            local_calc_ext = self.l_calc_ext
            calc_topup = self.calc_topup

            flt = cu.cbround(rawstr,rnd)
            if SUPER_DEBUG: print("<ENHANCE> Adding to Calc Ext {}:{}".format(key,rawstr))
            return cu.add_enh(key,flt,local_calc_ext, "calc_ext", calc_topup, enhanced, persist = _pv, overwrite = True)

        def assign_multiple_outputs(tk_list):
            # Forumala Multi output
            for item in tk_list:
                tk = item[0]
                vdk = item[1]
                result = result_dict.get(vdk,"")
                if not result == "":
                    if len(item) == 3:
                        # Round to specified DP
                        dp = item[2] 
                        add_calc_enh(tk,result, rnd = dp, _pv = pv_flag)
                    else:
                        add_calc_enh(tk,result, _pv = pv_flag)

                else:
                    print("<RESOLVE FORMULA> ERROR {} not found in formula".format(vdk))
            return 

        if isinstance(target_key, list):
            assign_multiple_outputs(target_key)
        else:
            # Single string. Default key is OUTCOME
            result = result_dict[self.std_output_key]
            add_calc_enh(target_key,result, _pv = pv_flag)
        return

    # Calculates, then assigns values to relevant keys
    def new_resolve_formula(self, fkey, info):
        if self.detect_inf_feedback():
            cu.log_error("<NEW RESOLVE FORMULA> Infinite Precalc Feedback Loop")

        form = self._get_formula_obj(fkey)
        self.precalculate(form, info) # This calls new_resolve_formula. Beware of infinite feedback loops
        self.debug_print("<NEW RESOLVE FORMULA> Performing: "+fkey)
        if SUPER_DEBUG: print("<NEW RESOLVE FORMULA> Current info:",info)
        vd = self._core_resolve_formula(form, info)
        self._assign_outputs(vd, form, info)
        return

    def _core_resolve_formula(self, f, enh):
        is_a_tree = isinstance(f.get("search_tree", "NONE"), dict)
        if is_a_tree:
            # Is a tree
            treeval = self.resolve_tree(f, enh)
            writeto = self._get_writeto(f) # Assuming only 1 writeto
            if isinstance(writeto, list):
                print("<CORE RESOLVE FORMULA> ERROR expected str but got", writeto)
                raise Exception("Tree writeto exception")
            return {self.std_output_key:treeval}
        else:
            # Is a formula
            return self.resolve_calculation(f,enh)
    
    # Tree search
    # Can only return 1 value. For multi values, use multiple trees.
    def resolve_tree(self, f, enh):
        def search_through_tree(tree, info, multi):
            any_val_key = "_ANY"

            def get_leaf_value(branch, info):
                if isinstance(branch,list):
                    final = cu.dive_for_dot_values(branch, info, DEBUG=SUPER_DEBUG, as_val = 1)
                    
                    if final == {}:
                        if DEBUG: print("<SECONDARY SLOT GETV> {} not found in info".format(branch))
                        final = ""
                    return final

                # If not, is a raw value
                return branch

            def tree_search(tree, t_info):
                for slotname, sub_dict in list(tree.items()):
                    dive_dict = cu.dive_for_dot_values(slotname, t_info) # As dict
                    if dive_dict == {}:
                        # IF not found
                        if SUPER_DEBUG: print("<TREE> ERROR {} not found".format(str(slotname)))
                        slot_val = ""
                        break

                    loc, slot_val = list(dive_dict.items())[0]
                    slot_val = str(slot_val) # Convert to strings because json keys are strings. I.e. for hours
                    
                    if SUPER_DEBUG: print("<TREE> Current slot:", loc, "| val:", slot_val)
                    
                    # Check if curr_info detail's value is in the subdict
                    if slot_val in sub_dict:
                        matched_branch = sub_dict[slot_val]
                        if isinstance(matched_branch, dict):
                            # Is a subtree
                            sub_tree = matched_branch
                            if SUPER_DEBUG: print("<TREE> Subtree found. Searching:",str(sub_dict))
                            found, returned = tree_search(sub_tree,t_info)
                            if found:
                                return (found, returned)
                            continue

                        else:
                            # Is a leaf
                            out = get_leaf_value(matched_branch, t_info)
                            pp = cu.dotpop(loc, t_info) # Cut from info
                            if SUPER_DEBUG: print("<TREE> pop leaf",pp)
                            return (True, out)
                    else:
                        # Fallback and look for _ANY match
                        a_branch = sub_dict.get(any_val_key,-1)
                        if not a_branch:
                            # Search failed
                            if SUPER_DEBUG: print("<TREE> Val:", slot_val, "not found in:", sub_dict)
                            break

                        if isinstance(a_branch, dict):
                            # Is a _ANY branch
                            slotname, sub_tree = list(a_branch.items())[0]
                            found, returned = tree_search(sub_tree,t_info)
                            if found:
                                return (found, returned)
                            continue

                        else:
                            # Is a _ANY leaf
                            out = get_leaf_value(a_branch, t_info)
                            # Cut from info
                            pp = cu.dotpop(loc, t_info)
                            if SUPER_DEBUG: print("<TREE> pop _ANY leaf",pp)
                            return (True, out)
                    
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
        
        # PRECALCULATE

        tree = f.get("search_tree", {})
        found_flag, val = search_through_tree(tree, enh, False)
        if not found_flag and SUPER_DEBUG: print("<SECONDARY SLOT> TREE SEARCH FAILED",tree)
        return val

    # Big method.
    # Takes in a formula (dict)
    # Returns a value of the result
    def resolve_calculation(self, f, enh):
        def get_steps(f):
            instr = f.get("steps",[])
            if instr == []:
                emsg = "<RESOLVE FORMULA> Error fetching steps {}".format(str(f))
                cu.log_error(emsg)
                raise Exception(emsg)
                
            stps = list(instr.keys())
            stps = list(map(lambda x: (x.split(","), instr[x]),stps))
            stps.sort(key=lambda t: float(t[0][0])) # If no conversion it sorts as string
            return stps

        # Given variables, an operator and a dictionary,
        # Returns a result value 
        def op_on_all(varnames, op, vdic):
            def operate(a,b,op):
                try:
                    a = float(a) # Force every variable involved to float
                    b = float(b)
                    return op(a,b)
                except:
                    emsg = "<FORMULA OPERATION> ERROR Could not convert to float:a<{}>,b<{}>".format(a,b)
                    cu.log_error(emsg)
                    exit()
            out = None
            for vname in varnames:
                isnumbr = cbsv.is_number(vname)
                rel_val = vname if isnumbr else vdic.get(vname) # variables can be real numbers or variable names
                if rel_val == "":
                    print("<FORMULA OPERATION> ERROR no value for {} in {}".format(vname, varnames))
                    rel_val = 0

                if out == None:
                    out = rel_val
                else:
                    out = operate(out,rel_val,op)
            return out

        def get_operator(opname):
            opname = opname.replace(" ","") #Spacing messes up the recognition of logical operators
            if opname == "add":
                opr = lambda a,b: a+b
            elif opname == "multi":
                opr = lambda a,b: a*b
            elif opname == "sub":
                opr = lambda a,b: a-b
            elif opname == "div":
                opr = lambda a,b: a/b
            elif opname == "equals":
                opr = lambda a,b: (1 if a == b else 0)
            elif opname == "isgreater":
                opr = lambda a,b: (1 if a > b else 0)
            elif opname == "OR":
                opr = lambda a,b: (1 if (a > 0 or b > 0) else 0)
            else:
                emsg = "<RESOLVE FORMULA> ERROR Unknown operator:"+opname
                print(emsg)
                raise Exception(emsg)
                # opr = lambda a,b: a # Unknown operator just returns a
            return opr

        def get_variables(f, enh):
            def add_formula_conditional_vars(f,vd):
                ret = {}
                # This assumes all conditions are joined by AND
                conds = f.get("conditions",[])
                for cond in conds:
                    k, v, setval = cond
                    vkey, tval, fval = setval

                    if not k in vd:
                        print("<COND VALS> WARNING {} not in info".format(k))
                        met = False
                    else:
                        if isinstance(v, list):
                            for val in v:
                                met = (vd[k] == val)
                                if met: break
                        else:
                            met = (vd[k] == v) # Simple match

                    ret[vkey] = tval if met else fval

                vd.update(ret)
                return

            # Fetch mandatory values
            reqvar_key = "req_vars"
            opvar_key = "optional_vars"
            req_vars = f.get(reqvar_key,[])
            vd = cu.dive_for_dot_values(req_vars,enh)

            # Fetch optional values
            op_vars = f.get(opvar_key, []) # If not found, value = 0
            op_vars_d = cu.dive_for_dot_values(op_vars, enh,failzero=True)
            vd.update(op_vars_d)

            # Fetch conditional values
            add_formula_conditional_vars(f,vd)
            if self.SUPER_DEBUG: print("<RESOLVE FORMULA> Value Dict",vd)
            return vd

        
        steps = get_steps(f)
        vd = get_variables(f, enh)

        # Perform calculation steps 
        vd["OUTCOME"] = 0
        for stp in steps:
            (NA, opname),(valnames,targetkey) = stp
            if not targetkey in vd:
                vd[targetkey] = 0
            opr = get_operator(opname)
            vd[targetkey] = op_on_all(valnames,opr,vd)
        return vd

    def debug_print(self, msg):
        if self.DEBUG: print(msg)
        return

if __name__ == "__main__":
    print("Number Converter On!")
    while 1:
        test = input()
        print("converted:",InfoParser.cn_to_integer(test))