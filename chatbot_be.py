# Chatbot Backend

import os
import threading
from decimal import Decimal
from cbsv import read_json, dump_to_json, check_file_exists
from cb_sql import MSSQL_readwriter


dbfolder = "userdata"
DEBUG = 0
JSON_DATABASE = 1
WRITE_TO_JSON = 1

class DatabaseRunner():
    def __init__(self):
        self.backup_delay = 30
        self.timer_on = False
        
        if JSON_DATABASE:
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

    def modify_db_fetched(self, dbf):
        mod = {}
        modlist = {"cust_city":{"writeto":"city","swaps":[("苏州","苏州"),("上海","上海")]}}
        for d_name, val in dbf.items():
            if d_name in modlist:
                curr_mod = modlist[d_name]
                new_key = curr_mod["writeto"]
                for regex, output in curr_mod["swaps"]:
                    if regex in val:
                        outval = output
                    else: 
                        outval = val
                
                mod[new_key] = outval
            else:
                mod[d_name] = decimal_obj_to_float(val)
        print("<MODIFIED FETCH>",mod)
        return mod
              
    def fetch_user_info(self, user):
        def _fetch_from_JSON(user):
            # self.database reflects the entire json database
            if not user in self.database:
                self.database[user] = {}

        def _fetch_from_SQL(user):
            # Create empty entry for new user
            fetch = self.SQLrw.fetch_user_info_from_sqltable(user)
            if isinstance(fetch, dict):
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
                if JSON_DATABASE:
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
        if DEBUG: print("Creating chatlogs folder...")
        os.mkdir(os.path.join(direct,"chatlogs")) # If no folder, make a folder
    
    log_filepath = os.path.join(direct,"chatlogs/" + chatID + ".json")
    
    if os.path.isfile(log_filepath):
        towrite = read_json(log_filepath)
    else:
        towrite = []
    towrite.extend(chatlog)

    # Write to json file
    dump_to_json(log_filepath,towrite,DEBUG=1,OVERRIDE=1)
    return