import sys
from chatbot import Chatbot


print("STARTING")
a = sys.argv[1]
rep = "Recieved " + a
print(rep)
sys.stdout.flush()

if __name__ == "__main__":
    bot = Chatbot()
    bot.start()


