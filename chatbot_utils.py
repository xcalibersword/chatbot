import os
import datetime as dt
# Useful Functions
DEBUG_DEFAULT = 0

# Wrapper function for dive_for_values where the detail path is a dot list
def dive_for_dot_values(dot_locs, info_dir, failzero = False, DEBUG = DEBUG_DEFAULT, as_val = 0, full_path = 1):
    if not isinstance(dot_locs, str):
        if isinstance(dot_locs,list):
            if len(dot_locs) == 1:
                dot_locs = dot_locs[0]
                return dive_for_dot_values(dot_locs,info_dir, failzero, DEBUG, as_val, full_path = full_path)
            else:
                # A list of dot locations
                out_dict = {}
                for dotloc in dot_locs:
                    dive_result = dive_for_dot_values(dotloc, info_dir, failzero, DEBUG, as_val=0, full_path = full_path)
                    out_dict.update(dive_result) # Dive result must be a dict
                return out_dict
        else:
            print("<DIVE FOR DOT> Bad input. Expected string or list of strings but got:", dot_locs)
            return {}

    new_nest_list = _docloc_to_list(dot_locs)

    out = dive_for_values(new_nest_list, info_dir, failzero, DEBUG, as_val, full_path = full_path)
    return out

# Recursively looks in dicts for nested dicts until finds values.
# Returns a dict of values
def dive_for_values(nest_list, info_dir, failzero = False, DEBUG = DEBUG_DEFAULT, as_val = 0, full_path = 1):
    if isinstance(nest_list,int) or isinstance(nest_list,float):
        return nest_list
        
    if isinstance(nest_list,list) and len(nest_list) > 0:
        inner_list = nest_list[0]
        if len(inner_list) < 2:
            if len(inner_list) == 1:
                in_in_list = inner_list[0]
                if isinstance(in_in_list, str):
                    nest_list = inner_list # Single value but accidentially in a list
        elif isinstance(inner_list[0], str) and isinstance(inner_list[1], list):
            if not len(inner_list) == 2:
                print("<DIVE> Bad list length, expected len 2 but got len",len(inner_list),nest_list)
                return {}
                
    dive_result = _dive(nest_list, info_dir, "", failzero = failzero, DEBUG = DEBUG)
    
    # as_val. Returns a raw value IF there is only 1 entry
    if len(dive_result) == 1 and as_val:
        dive_value = list(dive_result.values())[0]
        return dive_value

    return dive_result


def _dive(c_list, c_dir, prefix, failzero = False, DEBUG = DEBUG_DEFAULT, full_path = 1):
    out = {}
    for valname in c_list:
        # if DEBUG: print("<DIVE> vname", valname, "c_list", c_list)
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
                new_pfx = _dive_prefix(prefix, nextdirname)
                out.update(_dive(nestlist,nextdir, new_pfx, failzero=failzero, DEBUG=DEBUG))
        else:
            if valname in c_dir:
                rawval = c_dir[valname]
                out[valname] = rawval
            elif failzero:
                # Returns 0
                out[valname] = 0
            else:
                if DEBUG: print("<DIVE> ERROR! Cannot find variable<{}>".format(valname))
    
    return out

def _dive_prefix(oldpfx, cdir):
    tkn = "."
    final_prefix = cdir + tkn
    if not oldpfx == "":
        final_prefix = oldpfx + tkn + final_prefix
    return final_prefix

def _docloc_to_list(dot_loc, flatlist = False):
    # str, list
    def collect(curr, prev):
        if flatlist:
            prev.append(curr)
            return prev
        else:
            if prev == []:
                return [curr]
            else:
                return [curr, prev]

    pathlist = dot_loc.split(".")
    new_nest_list = []

    while 1:
        if len(pathlist) == 0:
            break
        curr = pathlist.pop(-1)
        new_nest_list = collect(curr, new_nest_list)
        
    if not flatlist: new_nest_list = [new_nest_list]
    return new_nest_list

# Changes info
def dotpop(dotloc, original_info):
    flatlist = _docloc_to_list(dotloc, flatlist = 1)
    curr_d = original_info
    for ddir in flatlist:
        if ddir == flatlist[-1]:
            if ddir in curr_d:
                popped = curr_d.pop(ddir)
                return popped
            else:
                return False

        if ddir in curr_d:
            curr_d = curr_d.get(ddir)
        else:
            print("<DOTPOP> WARNING ", ddir,"not found in",original_info)
    return False

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
    if isinstance(val, str):
        return val
        
    if dp == 0:
        dp_arg = None # round doesnt work with just 0
    else:
        dp_arg = dp
    
    return round(val,dp_arg)

def get_yearmonth():
    dtobj = dt.datetime.now()
    years = str(dtobj.year)
    raw_months = str(dtobj.month)
    if len(raw_months) == 1:
        months = "0" + str(raw_months)
    else:
        months = raw_months
    out = years + months
    assert(len(out) == 6)
    return out