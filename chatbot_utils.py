# Useful Functions
# Recursively looks in dicts for nested dicts until finds values.
def dive_for_values(c_list, c_dir, failzero = False, DEBUG = 1):
        out = {}
        for valname in c_list:
            # if DEBUG: print("<DIVE> vname, c_list",valname, c_list)
            if isinstance(valname, list):
                nextdirname, nestlist = valname
                if not nextdirname in c_dir:
                    if failzero:
                        out[valname] = 0
                    else:
                        if DEBUG: print("<DIVE> ERROR! Cannot find subdict<{}> in {}".format(nextdirname,c_dir))
                        return {} 
                else:
                    nextdir = c_dir[nextdirname]
                    out.update(dive_for_values(nestlist,nextdir))
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