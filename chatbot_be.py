# Chatbot Backend

import os
import threading
from cbsv import read_json, dump_to_json, check_file_exists
from cb_sql import write_to_sqltable, fetch_uid_from_sqltable

dbfolder = "userdata"
DEBUG = 0

class DatabaseRunner():
    def __init__(self):
        self.backup_delay = 60
        self.timer_on = False
        
        base_directry = os.getcwd()
        dbfilename = "database.json"
        self.dbfilepath = os.path.join(base_directry,dbfolder,dbfilename)
        if DEBUG: print("Loading info from", self.dbfilepath)
        if not check_file_exists(self.dbfilepath):
            print("Creating empty database file")
            dump_to_json(self.dbfilepath,{}, OVERRIDE = 1) # Create an empty file
        self.database = read_json(self.dbfilepath)
        
    def fetch_user_info(self, user):
        if not user in self.database:
            # Create empty entry for new user
            fetch = fetch_uid_from_sqltable(user)
            if isinstance(fetch, dict):
                ndic = fetch
            else:
                ndic = {}
            self.database[user] = ndic
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
        print("self db", self.database)

        # Set timer to write
        self.trigger_backup()

    def _true_write_to_db(self):
        if DEBUG: print("Writing userinfo to database")
        def destroy_empty_records():
            for user in list(self.database.keys()):
                if self.database[user] == {}:
                    self.database.pop(user)
        destroy_empty_records()
        write_to_sqltable(self.database)
        # dump_to_json(self.dbfilepath, self.database)
        self.timer_on = False

