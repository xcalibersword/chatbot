#decide the state and action to be taken using all factors

policy = {
    # "Example":
    # {
    #     "context":
    #     {
    #         "slot":{
    #             "country.in":"",
    #             "country.of":"",
    #             "fee.for":"",
    #             "fee.due":"",
    #             "others":""
    #             },                
    #         "policy":[]
    #     }
    # },
    "user.greet":
    {
        "default":
        {
            "slot":{},                
            "action":"bot.greet.informal"
        }
    },
    "clarify":[],
    "bye":[],
    "yes":[],
    "no":[],
    "others":[]
}


POLICY_RULES = {
    (INIT, "order") : (CHOOSE_COFFEE, "ok, Columbian or Kenyan?"),
    (CHOOSE_COFFEE, "specify_coffee"): (ORDERED, "perfect, the beans are on their way!"),
    (INIT, "none"): (INIT, "I'm sorry - I'm not sure how to help you"),
    (CHOOSE_COFFEE, "none"): (CHOOSE_COFFEE, "I'm sorry - would you like Colombian or Kenyan?"),
}

INIT = 0
IFHASACC = 1
hasACC = 2
noACC = 3

ANSWERED = 4

CHANGE_TOPIC = 5

TROLL = -2
END = -1


request_fee_policy = {
    (INIT,"user.request.fee"):(IFHASACC,"bot.request.hasAcc"),
    (INIT,"none"):(),
    (IFHASACC,"user.affirm"):(hasACC,),
    (IFHASACC,"user.deny"):(noACC,),
}
    
slot_filling_policy = {

}
    
fallback_policy ={

}


class POLICY():
    def __init__(self):
        self.policy = policy
    def get_action(self,intent,context,slot):
        slot_fill_dict = self.policy[intent]["default"]["slot"]



def send_message(state,intent):
    if state == INIT:
        new_state = START
        response = "bot.greet.formal"
    new_state,response = POLICY_RULES[state, intent]
    return new_state,response

if __name__ == "__main__":
    intent = input()
    state,response = send_message(state,intent)
