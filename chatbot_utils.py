import os

# Useful Functions
# Recursively looks in dicts for nested dicts until finds values.
# Returns a dict
def dive_for_values(nest_list, info_dir, failzero = False, DEBUG = 1):

    if isinstance(nest_list,list) and len(nest_list) > 0:
        inner_list = nest_list[0]
        if len(inner_list) < 2:
            print("<DIVE> inner_list too short: ",inner_list,"original:",nest_list)
            if len(inner_list) == 1:
                in_in_list = inner_list[0]
                if isinstance(in_in_list, str):
                    nest_list = inner_list # Single value but accidentially in a list
        elif isinstance(inner_list[0], str) and isinstance(inner_list[1], list):
            if not len(inner_list) == 2:
                print("<DIVE> Bad list length, expected len 2 but got len",len(inner_list),nest_list)
                return {}
                
    dive_result = _dive(nest_list, info_dir, failzero, DEBUG)

    return dive_result


def _dive(c_list, c_dir, failzero = False, DEBUG = 1):
    out = {}
    for valname in c_list:
        # if DEBUG: print("<DIVE> vname, c_list",valname, c_list)
        if isinstance(valname, list):
            nextdirname, nestlist = valname
            if not nextdirname in c_dir:
                if failzero:
                    for vn in valname:
                        if isinstance(vn, list):
                            print("<DIVE> vn is a list",vn)
                            return out
                        out[vn] = 0
                else:
                    if DEBUG: print("<DIVE> ERROR! Cannot find subdict<{}> in {}".format(nextdirname,c_dir))
                    return out 
            else:
                nextdir = c_dir[nextdirname]
                out.update(_dive(nestlist,nextdir,failzero,DEBUG))
        else:
            if valname in c_dir:
                rawval = c_dir[valname]
                out[valname] = rawval
            elif failzero:
                # Returns 0
                out[valname] = 0
            else:
                if DEBUG: print("<DIVE> ERROR! Cannot find variable<{}> in {}".format(valname,c_dir))
    
    return out

def add_enh(key, value, ext_dict, subdict_name, topup, enhanced, persist = False, overwrite = False, DEBUG = 0):
    if DEBUG: print("Enhancing!{}:{}".format(key,value))

    if key in ext_dict and not overwrite:
        ext_dict[key] = ext_dict[key] + value
    else:
        ext_dict[key] = value
    
    # Dict of info to be returned and written into main info
    if persist:
        topup[key] = value
        enhanced[key] = value # Write to enhanced main dict instead of subdict
    else:
        # Subdict names inlcude calc_ext and rep_ext
        if not subdict_name in enhanced: enhanced[subdict_name] = {} 
        enhanced[subdict_name].update(ext_dict) # Write to the the subdict in enhanced
    return

def log_error(elog):
    print("###! ERROR LOG !###",elog)
    chatbot_directory = os.getcwd()
    filename = os.path.join(chatbot_directory,"errorlog.txt")
    
    try:
        with open (filename, "w+") as f:
            prevs = f.read()
            new = prevs + elog
            f.write(new)
    except Exception as e:
        print("Failed to log error!", e)
    return