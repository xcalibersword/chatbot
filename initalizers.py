import json
import os
from cbsv import read_json
from chatbot_supp import SIP, Policy, InfoVault, InfoParser
from chatclass import DetailManager, ReplyGenerator, PolicyKeeper

# Converts a dict of states to a dict of state keys
def state_key_dict(states):
    ks = states.keys() # These are strings
    out = {}
    for k in ks:
        out[k] = states[k]["key"]
    return out

def init_replygen(jdata):
    REPLY_DB = jdata["reply_db"]

    # Everything above is not required anymore 
    return ReplyGenerator(REPLY_DB)

def init_policykeeper(jdata, pdata):
    INTENTS = jdata["intents"]
    STATES = jdata["states"]
    STATE_KEYS = state_key_dict(jdata["states"]) # state_index: state_key

    def in_default_set(intent):
        return intent["default_set"]
    
    def default_target_state(intent):
        return intent["default_target"]

    # In: list of [current_state, destination]
    # To create the classmethod SIPs
    def create_policy_tuple(pair):
        state, destination = pair
        if len(destination) < 4:
            name = INTENTS[state]["key"]
            print("Warning! {} has bad destination: {}".format(name,destination))
            return (INTENTS[state], SIP.same_state())
        if destination == "SAME_STATE":
            target_state = SIP.same_state()
        elif destination == "GO_BACK_STATE":
            target_state = SIP.go_back_state()
        elif destination == "EXIT_POCKET_STATE":
            target_state = SIP.exit_pocket()
        else:
            target_state = SIP(STATES[destination])
        return (INTENTS[state], target_state)

    def make_default_policy_set(intents):
        iks = list(intents.keys())
        out = []
        for intname in iks:
            intnt = intents[intname]
            if in_default_set(intnt):
                target = default_target_state(intnt)
                pair = (intname, target)
                out.append(create_policy_tuple(pair))
        return out
        
    policy_rules = pdata["policy_rules"] # This is true for now. Might change
    policy_states = list(policy_rules.keys())
    policy_states.remove("default")

    default_policy_set = make_default_policy_set(INTENTS)
    # for pair in policy_rules["default"]:
    #     pol = create_policy_tuple(pair)
    #     default_policy_set.append(pol)

    make_policy = lambda s_ints: Policy(default_policy_set,s_ints)

    POLICY_RULES = {}
    for state_key in policy_states:
        tuplelist = []
        for pair in policy_rules[state_key]:
            tuplelist.append(create_policy_tuple(pair))
        POLICY_RULES[STATE_KEYS[state_key]] = make_policy(tuplelist)

    # Loop to make all policies for those without specific paths
    existing = list(POLICY_RULES.keys())
    for i in list(STATES.keys()):
        k = STATE_KEYS[i]
        # state_value = STATES[k]["key"]
        if k in existing:
            continue # Don't overwrite existing policy lookup values
        POLICY_RULES[k] = make_policy([])

    return PolicyKeeper(POLICY_RULES, INTENTS, STATES)

def init_infoparser(jdata):
    relevant = jdata["info_parser"]
    return InfoParser(relevant)

def init_detailmanager(jdata):
    vault = InfoVault(jdata)
    return DetailManager(vault)

def master_initalize(filename = ""):
    # INTENTS = jdata["intents"]
    # STATE_KEYS = jdata["state_keys"]
    # MATCH_DB = jdata["match_db"]
    direct = os.getcwd()
    if filename == "":
        filename = os.path.join(direct,"chatbot_resource.json")

    print("<master initalize> reading from ",filename)
    jdata = read_json(filename)
    pr_filepath = os.path.join(direct,jdata["policy_data_location"])
    pdata = read_json(pr_filepath)

    components = {}
    components["replygen"] = init_replygen(jdata)
    components["pkeeper"] = init_policykeeper(jdata,pdata)
    components["dmanager"] = init_detailmanager(jdata)
    components["iparser"] = init_infoparser(jdata)
    return components