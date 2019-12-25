import os

# Useful Functions

# Wrapper function for dive_for_values where the detail path is a dot list
def dive_for_dot_values(dot_list, info_dir, failzero = False, DEBUG = 1, as_val = 0):
    print("AS VALUE inital", as_val)
    if not isinstance(dot_list, str):
        if isinstance(dot_list,list) and len(dot_list) == 1:
            dot_list = dot_list[0]
            return dive_for_dot_values(dot_list,info_dir, failzero, DEBUG, as_val)
        else:
            print("<DIVE FOR DOT> Bad input. Expected string", dot_list)
            return {}

    pathlist = dot_list.split(".")

    new_nest_list = []
    nested = False
    while 1:
        if len(pathlist) == 0:
            break
        curr = pathlist.pop(-1)
        if new_nest_list == []:
            if isinstance(curr, list):
                new_nest_list = curr
            else:
                new_nest_list = [curr]
        else:
            new_nest_list = [curr, new_nest_list]
            nested = True
    if nested: new_nest_list = [new_nest_list]

    out = dive_for_values(new_nest_list, info_dir, failzero, DEBUG, as_val)
    return out

# Recursively looks in dicts for nested dicts until finds values.
# Returns a dict of values
def dive_for_values(nest_list, info_dir, failzero = False, DEBUG = 1, as_val = 0):
    if isinstance(nest_list,int) or isinstance(nest_list,float):
        return nest_list
        
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
    
    # IF there is only 1 entry
    if len(dive_result) == 1 and as_val:
        dive_value = list(dive_result.values())[0]
        return dive_value

    return dive_result


def _dive(c_list, c_dir, failzero = False, DEBUG = 1):
    out = {}
    for valname in c_list:
        # if DEBUG: print("<DIVE> vname, c_list",valname, c_list)
        if isinstance(valname, list):
            if not len(valname) == 2:
                raise Exception("<DIVE> Valname expected len 2", str(valname))
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
    
    print("DIVE for", c_list,"RETURNING", out)
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


def cbround(val, dp = 0):
    if dp == 0:
        dp_arg = None # round doesnt work with just 0
    else:
        dp_arg = dp
    
    return round(val,dp_arg)