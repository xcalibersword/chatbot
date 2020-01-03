# Chatbot Backend

import os
import threading
from decimal import Decimal
from datetime import datetime
from cbsv import read_json, dump_to_json, check_file_exists
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
    def modify_db_fetched(self, dbf):
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

        mod = {}
        default_details = {"首次":"no"}
        mod.update(default_details)
        modlist = {
            "cust_city":{
                "writeto":"city",
                "swaps":[("苏州","苏州"),("上海","上海")]
            },
            "shebao_jishu":{
                "writeto":"要社保",
                "if_present":"yes",
                "keep_og":True
            },
            "gjj_jishu":{
                "writeto":"要公积金",
                "if_present":"yes",
                "keep_og":True
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
              
    def fetch_user_info(self, user):
        def _fetch_from_JSON(user):
            # self.database reflects the entire json database
            if not user in self.database:
                self.database[user] = {}

        def _fetch_from_SQL(user):
            # Create empty entry for new user
            found, fetch = self.SQLrw.fetch_user_info_from_sqltable(user)
            if found:
                ndic = self.modify_db_fetched(fetch)
                have_existing_entry = True
            else:
                ndic = {}
                have_existing_entry = False
            self.database[user] = ndic
            return have_existing_entry

        if not user in self.database:
            success = _fetch_from_SQL(user)
            if not success:
                if READ_FROM_JSON:
                    _fetch_from_JSON(user)
            
        return self.database[user]

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
    dump_to_json(log_filepath,towrite,DEBUG=1,OVERRIDE=1)
    return