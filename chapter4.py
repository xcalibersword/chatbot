#define the state
INIT = 0
CHOOSE_COFFEE = 1
ORDERED = 2
#key is the detected state and intent, value is the next state and the response suggested
POLICY_RULES = {
    (INIT, "order") : (CHOOSE_COFFEE, "ok, Columbian or Kenyan?"),
    (CHOOSE_COFFEE, "specify_coffee"): (ORDERED, "perfect, the beans are on their way!"),
    (INIT, "none"): (INIT, "I'm sorry - I'm not sure how to help you"),
    (CHOOSE_COFFEE, "none"): (CHOOSE_COFFEE, "I'm sorry - would you like Colombian or Kenyan?"),
}

#include prev suggestion and excluded list to acount for cases of "deny"
def send_message(state,intent):
    new_state,response = POLICY_RULES[state, intent]
    return new_state,response

#can include a policy function to do simple follow up questions or to acknowledege replies with "ok"
#policy return detected action and pending action


#intent obtained for the message that was pass into
#intent = ["none","order", "none","specify_coffee"]
state = INIT
while True:
    intent = input('intent: ')
    state,response = send_message(state,intent)
    print(response)