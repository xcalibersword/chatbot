import cbsv

DEBUG = 1


# Have a message class? Or some sort of flag for messages. Indicate state-changing messages.

# A packet that has info about state and message
# State-Message Packet
PREV_STATE_F = "299 PREV_STATE"
PREV_STATE_MSG = "prev_state_msg"
class SMP:
    def __init__(self, msg, state):
        self.msg = msg
        self.state = state
        self.stateChange = True
        self.backtrack = False

    def set_backtrack(self):
        self.backtrack = True
        self.stateChange = True #?

    def set_actions(self, action, pending_act = None):
        self.action = action
        self.pending_act = pending_act

    @classmethod
    def go_back_state(cls):
        obj = cls(PREV_STATE_MSG, PREV_STATE_F)
        obj.backtrack = True
        obj.stateChange = False
        return obj

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
        # If state never change, do nothing
        if new_state == self.state or new_state == cbsv.PREV_STATE_FLAG():
            return
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