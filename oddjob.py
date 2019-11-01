import json

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

test = {"abc":123,"memem":7461}

print(test)
tt = str(test)
print(tt)

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