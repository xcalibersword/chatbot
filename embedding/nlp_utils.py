STR_DIGITSET = {"0","1","2","3","4","5","6","7","8","9","."}

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