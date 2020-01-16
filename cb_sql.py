# A set of tools to interact with SQL
import os
import pymssql as msql # Ignore the error message from this. But it means this is lib incompatible with Python 3.8 and above.
import threading
import chatbot_utils as cu
from localfiles.details import get_read_details, get_write_details

write_info = get_write_details()
read_info = get_read_details()

SQL_JSON = {
    "predef_queries":{
        "init_get_info_query":{
            "cust_tb_id_col":"淘宝会员名",
            "key_col":"最后修改日期",
            "query_key":"basic",
            "writevals":[
                ("user_id", "淘宝会员名"),
                ("cust_city", "缴费城市"),
                ("cust_city_detailed", "社保类型"),
                ("shebao_jishu", "社保基数"),
                ("gjj_jishu", "公积金基数"),
                ("shebao_svc_fee", "社保服务费"),
                ("plan_start_date","社保开始日期"),
                ("last_changed", "最后修改日期"),
                ("curr_payment_status", "员工缴费状态")
            ],
            "table": "基本信息",
            "conditions": "where 淘宝会员名 = '{customer_ID}'"
        },
        "get_customer_and_bill_query":{
            "cust_tb_id_col": "淘宝会员名",
            "key_col":"姓名",
            "query_key":"bill_info",
            "writevals":[
                ("customer_fullname", "姓名"),
                ("curr_month_amt_due", "本月应付")
            ],
            "table": "Billinfo_淘宝_主表",
            "conditions": "where 账单月份_文本值 like '{yyyymm}' and 淘宝会员名 = '{customer_ID}'",
        },
        "active_customer_query": {
            "COMMENTS": "This might be redundant because exist query looks for this detail already",
            "cust_tb_id_col":"淘宝会员名",
            "key_col":"最后修改日期",
            "query_key":"active",
            "writevals":[],
            "column":"员工缴费状态", 
            "table": "基本信息",
            "conditions": "where 淘宝会员名 = '{customer_ID}'and (员工缴费状态='正常缴费' or 员工缴费状态='新进'or 员工缴费状态='新进补缴')"
        },
        "get_usernames_query": {
            "cust_tb_id_col":"淘宝会员名",
            "writevals":[
                ("user_id", "淘宝会员名")
            ],
            "table": "基本信息",
            "conditions": ""
        },
        "yuangongxinxi_query": {
            "cust_tb_id_col":"淘宝ID",
            "writevals":[
                ("cust_city", "缴费城市"),
                ("shebao_jishu", "社保基数"),
                ("gjj_jishu", "公积金基数"),
                ("shebao_svc_fee", "社保服务费"),
            ],
            "column":"员工缴费状态", 
            "table": "员工信息",
            "conditions": "where 员工缴费状态='正常缴费' or 员工缴费状态='新进'or 员工缴费状态='新进补缴'"
        }
    }
}


# DB ACCESS SETTINGS
db_host = write_info["sql_address"]
db_port = write_info["sql_port"]
db_user = write_info["username"]
db_pass = write_info["pass"]
db_dbname = "Northwind"
db_tablename = "dbo.Customers"
db_charset = "utf8mb4"


db_read_host = read_info["sql_address"]
db_read_port = read_info["sql_port"]
db_read_user = read_info["username"]
db_read_pass = read_info["pass"]
db_read_dbname = read_info["dbname"]
db_read_queries = SQL_JSON["predef_queries"]
INITIAL_QUERY = db_read_queries["init_get_info_query"]
AMT_PAYABLE_QUERY = db_read_queries["get_customer_and_bill_query"]
ACTIVE_CUST_QUERY = db_read_queries["active_customer_query"]
USERNAME_QUERY = db_read_queries["get_usernames_query"]

write_conn = None
read_conn = None

DEBUG = 1
SQL_READ_ENABLED = True
SQL_WRITE_ENABLED = False
LOCALFILES_PRESENT = ""

# db_host = "40.68.37.158" #ADVENTURE WORKS
# db_user = "Sample user"
# db_pass = "password"
# db_dbname = "AdventureWorks2012"

NO_INFO = {}

def have_localfiles():
    global LOCALFILES_PRESENT
    if LOCALFILES_PRESENT == "":
        foldername = "localfiles"
        filename = "details.py"
        localpath = os.path.join(foldername,filename)
        LOCALFILES_PRESENT = os.path.exists(localpath)
    return LOCALFILES_PRESENT

def check_local_files_bad(sql):
    if have_localfiles():
        return False
    else:
        print("<CB SQL> No details file provided, unable to read/write to Database")
        return True

def add_to_str(s, thing):
    return s + thing + ";"

def build_context_info(uid):
    yearmonth_str = cu.get_yearmonth()
    info_dict = {'yyyymm':yearmonth_str}
    info_dict["customer_ID"] = uid

    return info_dict

class Alarmy:
    def __init__(self):
        self.job_done = False
        self.lto = 10

    def set_exec_time_limit(self):
        def timeout_callback():
            if not self.job_done:
                raise Exception("Timed out!")
            return
        self.job_done = False
        timer = threading.Timer(self.lto, timeout_callback)
        timer.start()

    def alarm_off(self):
        self.job_done = True


class MSSQL_readwriter:
    def __init__(self):
        # self.alarmy = Alarmy()
        self.lto = 10 # Login time out
        self.qto = 5 # Query time out

        self.write_conn = None
        self.connect_to_write()

        self.read_conn = None
        self.connect_to_read()

    def cannot_write(self):
        return self.write_conn == None

    def cannot_read(self):
        return self.read_conn == None

    def connect_to_write(self):
        global SQL_WRITE_ENABLED
        if SQL_WRITE_ENABLED:
            print("Trying to connect to Write...")
            try:
                
                self.write_conn = msql.connect(server=db_host, user=db_user, password=db_pass, database=db_dbname,login_timeout=self.lto,timeout=self.qto)
                print("Connected to Write!")
            except Exception as e:
                print("Write Connection Exception!",e)

        
    def connect_to_read(self):
        global SQL_READ_ENABLED
        if SQL_READ_ENABLED:
            print("Trying to connect to Read...")
            try:
                self.read_conn = msql.connect(server=db_read_host, user=db_read_user, password=db_read_pass,login_timeout=self.lto,timeout=self.qto) 
                # read_conn = msql.connect(server=db_read_host, user=db_read_user, password=db_read_pass, database=db_read_dbname) 
                print("Connected to Read!")
            except Exception as e:
                print("Read Connection Exception!",e)


    def insert_test(self):
        connection = self.write_conn
        try:
            vals = ('我是个鸟儿', '甲城市')
            slots = "(userID, city)"
            # vals = ('testuid', 'abc')
            sqlcmd = "INSERT INTO " + tablename + " " + slots + " VALUES (%s, %s)"
            print("query:",sqlcmd)
            self.commit_to_con(connection, sqlcmd, vals)
            
        finally:
            connection.close()

    def fetch_all_from_con(self, tabnam, columns = "*", condition = ""):
        query = "SELECT {} FROM {} {}".format(columns,tabnam,condition)
        if check_local_files_bad(query):
            return []
        
        if self.cannot_read():
            print("<FETCH FROM CON> No Connection, returning empty dict")
            return {}

        conn = self.read_conn
        try:
            with conn.cursor(as_dict=True) as cursor:
                cursor.execute(query,[])
                result = cursor.fetchall()
            if result is None:
                result = []
            return result
        except Exception as e:
            print("<FETCH ALL ERROR>", e)

    def fetch_lines_matching_value(self, tablename, column_name, value):
        cond = "WHERE " + column_name + "='" + str(value) + "'"
        f = self.fetch_all_from_con(tablename, condition = cond)
        return f

    # Writes to the connection
    def commit_to_con(self,conn, comcmd, comvals):
        if SQL_WRITE_ENABLED:
            print("<BACKEND WARNING: Writing to SQL has been disabled> Restore it in cb_sql.py.\nCommand not executed:{}".format(comcmd))
            return

        if check_local_files_bad("COMMIT"):
            return ()

        try:
            with conn.cursor() as cursor:
                cursor.execute(comcmd, comvals)

            # connection is not autocommit by default. Must commit to save changes.
            conn.commit()
            print("Committed to db")
        except Exception as e:
            print("EXCEPTION! Rolling back", e)
            print("Failed command:",comcmd)
            conn.rollback()

    # Writes to a predefined table
    def write_to_sqltable(self,users_info):
        if not SQL_WRITE_ENABLED:
            return 
        connection = self.write_conn
        userids = self.fetch_all_from_con(tablename, columns = "userID")
        userids = map(lambda x: x['userID'],userids)
        print("uids",userids)
        
        users = list(users_info.keys())
        
        for uk in users:
            userinfo = users_info[uk].copy()
            vals = list(userinfo.values())
            if DEBUG: print("<WRITE TO SQL> uinfo",userinfo)
            cols = ', '.join(userinfo.keys())
            qmarks = ', '.join(['%s'] * len(userinfo)) # Generates n * ? separated by commas
            if uk in userids:
                delq = "DELETE FROM %s WHERE userID = '%s'" % (tablename, uk)
                self.commit_to_con(connection, delq, ())

            qry = "INSERT INTO %s (%s) VALUES (%s)" % (tablename, cols, qmarks)
            self.commit_to_con(connection, qry, vals)

    def fetch_user_info_from_sqltable(self, user_name):
        def update_dict(collector, retrieved, query):
            qkey = query.get("query_key")
            collector[qkey] = retrieved

        def execute_and_update(collector, query, user_name):
            flag, f_dict = self._execute_predef_query(query, user_name)
            update_dict(collector, f_dict, query)
            return flag

        if self.cannot_read():
            # Try to connect again
            self.connect_to_read()
        if DEBUG: print("<SQL FETCH INFO> Looking for {}".format(user_name))

        master_d = {}
        is_exists = execute_and_update(master_d, INITIAL_QUERY, user_name)
        # print("Exists", master_d)

        is_billed = execute_and_update(master_d, AMT_PAYABLE_QUERY, user_name) 
        # print("Billed", master_d)

        status = (is_exists, is_billed)

        if is_exists and not is_billed:
            print("<FETCH USERINFO FROM SQL>Manged to find {} in 基本信息 but not billinfo_淘宝_主表".format(user_name))
        
        return status, master_d

    def fetch_all_from_sqltable(self,tablename):
        f = self.fetch_all_from_con(tablename)
        return f

    def _execute_predef_query(self, query, uid):
        matchfound = False
        out = {}

        if uid == "" or uid == " ":
            return (matchfound, out)

        if not SQL_READ_ENABLED:
            return (matchfound, out)
        table = query.get("table")
        key_col = query.get("key_col")
        write_vals = query.get("writevals")
        conds = query.get("conditions", "")

        context_info = build_context_info(uid)
        final_conds = conds.format(**context_info)

        f_rows = self.fetch_all_from_con(table, condition= final_conds)
        if DEBUG: print("<PREDEF Q> Searching for {} in {} fetched {} queries".format(uid, table, str(len(f_rows))))

        for row in f_rows:
            key = row.get(key_col,False)
            if not key: raise Exception("No key found! Table:{}. Key_col:{}".format(table, key_col))
            entry = {}
            for k, colname in write_vals:
                entry[k] = row.get(colname, "")
            
            out[key] = entry
        
        if len(out) > 0:
            matchfound = True

        
        # for row in f_rows:
        #     if row.get(tb_id_col,"") == uid:
        #         if DEBUG: print("<PREDEF Q> FOUND a match for {}".format(uid), "L00ked through {} rows".format(count))
        #         for k, colname in write_vals:
        #             out[k] = row.get(colname, "")
                
        #         matchfound = True
        #     count += 1

        return (matchfound, out)

    

asdf = {"alina":{"userID":"小花朵","city":"北京", "首次":"yes"}}

if __name__ == "__main__":
    sqr = MSSQL_readwriter()
    # bl, allnames_qr = sqr._execute_predef_query(USERNAME_QUERY, "")
    # listof = list(allnames_qr.items())
    # po = listof[:10][:10][:10][:10]
    # po = sqr.fetch_all_from_con("Billinfo_淘宝_主表", condition="where 淘宝会员名 = 'dreampaopao'")
    # print(po, "<END>")
    while 1:
        username = input("Please enter a username: ")
        pf = sqr.fetch_user_info_from_sqltable(username)
        print(pf)