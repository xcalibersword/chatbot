# Useful Functions
# Recursively looks in dicts for nested dicts until finds values.
# Returns a dict
def dive_for_values(nest_list, info_dir, failzero = False, DEBUG = 1):

    if isinstance(nest_list,list) and len(nest_list) > 0:
        inner_list = nest_list[0]
        if isinstance(inner_list[0], str) and isinstance(inner_list[1], list):
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
                        out[vn] = 0
                else:
                    if DEBUG: print("<DIVE> ERROR! Cannot find subdict<{}> in {}".format(nextdirname,c_dir))
                    return {} 
            else:
                nextdir = c_dir[nextdirname]
                out.update(_dive(nestlist,nextdir))
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