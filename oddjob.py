import json

# Automatically does things like format json info

def read_json(json_filename):
    with open(json_filename, 'r') as f:
        data = json.loads(f.read())
    return data

def dump_to_json(filename, data, DEBUG = 0):
    with open(filename,'w') as f:
        json.dump(data, f, indent = 4)
    
    if DEBUG:
        print("Finished writing to " + str(filename))


json_data = read_json("chatbot_resource.json")

STATES = json_data["states"]

allstates = list(STATES.keys())

new_dict  = {}
for s in allstates:
    entry = {}
    entry["key"] = STATES[s]
    entry["gated"] = False
    entry["req_info"] = ""
    new_dict[s] = entry


output_filename = "dump.json"

dump_to_json(output_filename, new_dict, 1)
