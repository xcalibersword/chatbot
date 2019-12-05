import json
<<<<<<< master
<<<<<<< master
from decimal import Decimal
=======
import re
>>>>>>> Create val_slots using RE
=======
import re
>>>>>>> Create val_slots using RE

# Working file to automatically do things like format json info

def read_json(json_filename):
    with open(json_filename, 'r',encoding="utf-8") as f:
        data = json.loads(f.read(),encoding="utf-8")
    return data

def dump_to_json(filename, data, DEBUG = 0):
    with open(filename,'w', encoding="utf-8") as f:
        json.dump(data, f, indent = 4, ensure_ascii=0)
    
    if DEBUG:
        print("Finished writing to " + str(filename))

<<<<<<< master
<<<<<<< master
test = {"abc":123,"memem":7461}
test = Decimal(5.12345)
print(test, type(test))
test2 = test.to_integral_value()
print(test2, type(test2))
test3 = float(test2)
print(test3, type(test3))

# tt = str(test)
# print(tt)
=======
=======
>>>>>>> Create val_slots using RE
test = "I want 10-12月"
test = "要交9到12月份"
reDB = "(1?[0-9])月?(~|-|到)(1?[0-9])月?"
db2 = "(?<=(~|-|到))(1?[0-9])月?"
tt = re.search(reDB, test)
tt2 = re.search(db2, test)
print("first: ",tt)
print("1:", tt.group(1))
print("2:", tt2.group(2))
<<<<<<< master
>>>>>>> Create val_slots using RE
=======
>>>>>>> Create val_slots using RE

# json_data = read_json("chatbot_resource.json")

# things = json_data["states"] # CHANGE TARGETS

# thinglist = list(things.keys())

# new_dict  = {}
# for t in thinglist:
#     oldentry = things[t]
#     entry = {}
#     existingkeys = list(oldentry.keys())
#     for ek in existingkeys:
#         entry[ek] = oldentry[ek]

#     # ACTION HAPPENS HERE
#     if not "replies" in entry:
#         entry["replies"] = []
#     new_dict[t] = entry

# output_filename = "dump.json"

# dump_to_json(output_filename, new_dict)

print("Done")