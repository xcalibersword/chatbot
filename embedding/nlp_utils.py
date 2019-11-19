STR_DIGITSET = {"0","1","2","3","4","5","6","7","8","9","."}
CHI_DIGITSET = {"一","二","三","四","五","六","七","八","九","十","百","千","万","亿"}

def is_a_number(thing):
    if not isinstance(thing, str):
        try:
            w = str(thing)
        except Exception as e:
            print("<CHECK NUMBER>",e)
    else:
        w = thing
    
    # Check each character
    for char in w:
        if not char in STR_DIGITSET:
            return False

    return True

def replace_number_tokens(seq):
    number_token = "_123"
    out = []
    for token in seq:
        if is_a_number(token):
            out.append(number_token)
        else:
            out.append(token)
    return out