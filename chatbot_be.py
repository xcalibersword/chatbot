# Chatbot Backend

import os
import threading
from copy import deepcopy
from decimal import Decimal
from datetime import datetime

from cbsv import read_json, dump_to_json, check_file_exists, CHINA_CITIES
from cb_sql import MSSQL_readwriter


dbfolder = "userdata"
DEBUG = 0
READ_FROM_JSON = 1
WRITE_TO_JSON = 1

class DatabaseRunner():
    def __init__(self):
        self.backup_delay = 30
        self.timer_on = False
        
        if READ_FROM_JSON:
            self.database = self._read_json_db()
        else:
            self.database = {}

        self.SQLrw = MSSQL_readwriter()

    def _read_json_db(self):
        def _create_json_db():
            if not check_file_exists(self.dbfilepath):
                print("Creating empty database file")
                dump_to_json(self.dbfilepath,{}, OVERRIDE = 1) # Create an empty file
            return

        base_directry = os.getcwd()
        dbfilename = "database.json"
        # self.dbfilepath = os.path.join(base_directry,dbfolder,dbfilename)
        self.dbfilepath = os.path.join(base_directry,dbfilename) # For testing purpose
        _create_json_db()

        if DEBUG: print("Loading info from", self.dbfilepath)
        return read_json(self.dbfilepath)

    # Assuming there is a match
    def repackage_sql_fetched(self, dbf, status):
        # Database dates are datetimes. Incompatible with Json.
        def datetime_obj_to_str(dateobj):
            if isinstance(dateobj, datetime):
                return str(dateobj)
            return dateobj

        # Database values are Decimals. Incompatible with Json.
        def decimal_obj_to_float(dobj):
            if isinstance(dobj, Decimal):
                return float(dobj)
            return dobj

        def convert_object_to_values(obj):
            obj = decimal_obj_to_float(obj)
            obj = datetime_obj_to_str(obj)
            return obj

        # Removes the ones with bad cust city
        def filter_inpure_exist_entries(d):
            basic_dict = d.get("basic")

            out = {}
            except_flag = False
            exceptional_k = "exceptional_case"
            secondary_k = "secondary_shebao"
            deciding_key = "cust_city"
            
            valid_vals = CHINA_CITIES()
            
            extra_count = 0
            basic_dict_list = list(basic_dict.values())
            for ed_entry in basic_dict_list:
                deciding_entry_val = ed_entry.get(deciding_key,"")
                for v in valid_vals:
                    if v in deciding_entry_val:
                        if out == {}:
                            out.update(ed_entry)
                            break
                        else:
                            extra_count += 1
                            extra_k = secondary_k + str(extra_count)
                            out[extra_k] = ed_entry
                            except_flag = True
                            break
            
            out[exceptional_k] = "yes" if except_flag else "no"

            return out
        def billing_to_list(d):
            def _repackage(bd):
                outlist = [] 
                bd_itemlist = list(bd.items())
                for realname, details in bd_itemlist:
                    amt_due = details.get("curr_month_amt_due","")
                    l_entry = (realname, amt_due)
                    outlist.append(l_entry)
                return outlist

            bill_d = d.get("bill_info")
            return _repackage(bill_d)

        # Swaps and converts values
        def repackage_base_details(d):
            mod = {}
            default_details = {"首次":"no"} # Values assigned by default
            mod.update(default_details)
            
            modlist = {
                "curr_payment_status":{
                    "writeto":"curr_payment_status",
                    "swaps":[
                        ("正常缴费", "normal"),
                        ("新进", "normal"),
                        ("新进补缴", "normal")
                    ]
                },
                "cust_city":{
                    "writeto":"city",
                    "swaps":[("苏州","苏州"),("上海","上海")]
                },
                "shebao_jishu":{
                    "writeto":"要社保",
                    "if_present": "yes",
                    "swaps":[("None","no"), ("", "no")]
                },
                "gjj_jishu":{
                    "writeto":"要公积金",
                    "if_present": "yes",
                    "swaps":[("None","no"), ("", "no")]
                }
            }

            for d_name, val in dbf.items():
                print("<MOD DB FETCH> Mod",mod," + ", d_name)
                if d_name in modlist:                    
                    curr_mod = modlist[d_name]
                    new_key = curr_mod["writeto"]
                    if curr_mod.get("if_present",False):
                        outval = curr_mod["if_present"]
                        if curr_mod.get("keep_og", True):
                            mod[d_name] = convert_object_to_values(val)

                    for regex, output in curr_mod.get("swaps",[]):
                        if regex in val:
                            outval = output
                        else: 
                            outval = val
                    
                    mod[new_key] = outval
                else:
                    mod[d_name] = convert_object_to_values(val)
            print("<MODIFIED FETCH>", mod)
            return mod

        def attach_status(d, status):
            # Returns a string the represents the status of the customer
            def judge_status(d, status):
                exist, bill = status
                pay_status_key = "员工缴费状态"
                valid_status = ["正常缴费", "新进", "新进补缴"]
                pay_status = d.get(pay_status_key, "")

                if pay_status in valid_status:
                    s1 = "Active"
                else:
                    s1 = "Inactive"
                
                if bill:
                    s2 = "Bill"
                else:
                    s2 = "NoBill"

                out_str = s1 + "_" + s2
                return out_str
            
            status_tup = judge_status(d, status)
            d["customer_status"] = status_tup                
        
        base = filter_inpure_exist_entries(dbf)
        bill_list = billing_to_list(dbf)

        final = repackage_base_details(base)
        final["bills"] = bill_list
        attach_status(final,status)

        return final

        
              
    # Returns a tuple of (Bool, Dict)
    def fetch_user_info(self, user):
        BLANK_ENTRY = {}
        def _fetch_from_JSON(user):
            # self.database reflects the entire json database
            if not user in self.database:
                self.database[user] = {}

        def _fetch_from_SQL(user):
            # Create empty entry for new user
            status, fetch = self.SQLrw.fetch_user_info_from_sqltable(user)
            found = status[0] # (exists, has bill)

            if found:
                ndic = self.repackage_sql_fetched(fetch, status)
            else:
                ndic = {}
            self.database[user] = ndic
            return found

        if not user in self.database:
            success = _fetch_from_SQL(user)
            if not success:
                if READ_FROM_JSON:
                    _fetch_from_JSON(user)

        found = not self.database[user] == BLANK_ENTRY
        return (found, self.database[user])

    def trigger_backup(self):
        if self.timer_on:
            return
        self.timer_on = True
        backuptimer = threading.Timer(self.backup_delay, self._true_write_to_db)
        backuptimer.start()

    def write_to_db(self, chatid, info):
        if not chatid in self.database:
            # Create empty entry for new user
            self.database[chatid] = {}

        # Write to a dict that will later be pushed to the db
        self.database[chatid].update({"userID":chatid})
        self.database[chatid].update(info)
        if DEBUG: print("<Write to DB> self.db", self.database)

        # Set timer to write
        self.trigger_backup()

    def _true_write_to_db(self):
        def destroy_local_empty_records():
            for user in list(self.database.keys()):
                if self.database[user] == {}:
                    self.database.pop(user)

        if DEBUG: print("Writing userinfo to database")
        destroy_local_empty_records()
        if WRITE_TO_JSON:
            dump_to_json(self.dbfilepath, self.database)
        else:
            self.SQLrw.write_to_sqltable(self.database)
        self.timer_on = False

# Assumes messages are in a list structure
def record_chatlog_to_json(chatID, chatlog):
    direct = os.getcwd()
    log_folder = "chatlogs"
    if not os.path.isdir(os.path.join(direct,log_folder)):
        print("Creating chatlogs folder...")
        os.mkdir(os.path.join(direct,"chatlogs")) # If no folder, make a folder
    
    log_filepath = os.path.join(direct,"chatlogs/" + chatID + ".json")
    
    if os.path.isfile(log_filepath):
        towrite = read_json(log_filepath)
        loglen = len(towrite)
        if DEBUG: print("<RECORD CHATLOG> Existing chatlog for {}: {} lines".format(chatID,loglen))
    else:
        towrite = []

    towrite.extend(chatlog)
    loglen = len(towrite)
    if DEBUG: print("<RECORD CHATLOG> Final write: {} lines".format(loglen))

    # Write to json file
    dump_to_json(log_filepath,towrite,DEBUG=0,OVERRIDE=1)
    return