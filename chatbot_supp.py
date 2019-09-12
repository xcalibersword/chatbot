import cbsv

DEBUG = 1


# Have a message class? Or some sort of flag for messages. Indicate state-changing messages.


PREV_STATE_F = "299 PREV_STATE"
PREV_STATE_MSG = "prev_state_msg"

# A packet that has info about state and has constructors for set states like go_back
# State Info Packet
class SIP:
    def __init__(self, state, cs = True):
        self.state = state
        self.state_change = cs
        self.backtrack = False
        self.go_back = False

    def set_backtrack(self):
        self.backtrack = True

    def set_actions(self, action, pending_act = None):
        self.action = action
        self.pending_act = pending_act

    def get_state(self):
        return self.state

    @classmethod
    def same_state(cls):
        obj = cls("same_state", cs=False)
        return obj
 
    @classmethod
    def go_back_state(cls):
        obj = cls(PREV_STATE_F, cs=False)
        obj.set_backtrack()
        obj.go_back = True
        return obj
    def is_same_state(self):
        return not self.state_change
    def is_go_back(self):
        return self.go_back == True

# A vehicle to house intent and details from the message
class Understanding:
    def __init__(self, intent, sip):
        self.intent = intent
        self.sip = sip
        self.details = None

    def parse_details(self, info):
        self.location = ""
        self.date = ""
        self.info = info

    def get_intent(self):
        return self.intent
    
    def get_sip(self):
        return self.sip

    def set_intent(self, i):
        self.intent = i

# Action that includes string for replies
class Action:
    def __init__(self):
        self.message = ""
        self.log_data_bool = False
        self.extra_info = []

    @classmethod
    def reply(cls, msg):
        act = cls()
        act.set_message(msg)
        return act
    
    @classmethod
    def go_back(cls, prev_msg):
        act = cls()
        act.message = msg
        return act
        
    def set_message(self, msg):
        self.message = msg

    def log_data(self, data):
        self.log_data_bool = True
    
    def has_data(self):
        return self.log_data_bool

    def set_details(self, d):
        self.details = d
        

# A product???
class Product:
    def __init__(self, name, info):
        self.name = name
        self.parse_info(info)

    # info is in the form of a dict
    def parse_info(self, info):
        self.price = info["price"]
        self.desc = info["desc"]

# Try to have stateful changes
# frame = (state, message)
class Chat:
    def __init__(self,customer,convo_history,initial_state):
        self.customer = customer
        self.state = initial_state
        self.convo_history = convo_history
        self.prev_messages = []
        self.frame_history = [initial_state,]
    def change_state(self,new_state):
        if DEBUG: print("changing to", new_state)
        self.frame_history.append(self.state)
        self.state = new_state
        self.first_state_pop = True

    def set_prev_msg(self, msg):
        if msg == cbsv.DEFAULT_CONFUSED():
            return
        self.prev_messages.append(msg)
        self.firstpop = True
    
    def pop_prev_msg(self):
        # TODO failsafe when empty?
        # Need to get the previous previous message
        if len(self.prev_messages) < 2:
            return self.prev_messages[-1]
        if self.firstpop: 
            self.prev_messages.pop(-1)
            self.firstpop = False
        return self.prev_messages.pop(-1)

    def get_state(self):
        return self.state

    def get_prev_state(self):
        if len(self.frame_history) < 1:
            return frame_history[-1]
        #     self.first_state_pop = False
        #     self.frame_history.pop(-1)
        return self.frame_history.pop(-1)

    def set_selection(self,selection):
        self.selection = selection
    
    def get_selection(self):
        return self.selection

    def clear_selection(self):
        self.selection = False

    def get_previous_issues(self):
        return self.user.get_issues()

    def go_back(self):
        print("going back")

    def update_chat(self, sip, selection):
        if not isinstance(selection,int):
            self.set_selection(selection)

        if sip.is_go_back():
            self.go_back()

        elif sip.is_same_state():
            return
        
        new_state = sip.get_state()
        self.change_state(new_state) 

        
        
class Customer:
    def __init__(self, userID, accounts = -1, issues = -1):
        self.userID = userID
        if isinstance(issues,int): 
            self.accounts = [] 
        else: 
            self.accounts = accounts
        if isinstance(issues,int):
            self.issues_list = []
        else:
            self.issues_list = issues

    def add_issue(self, issue):
        self.issues_list.append(issue)
        # Check for duplicates?

    def get_issues(self):
        return self.issues_list

    def get_accounts(self):
        return self.accounts