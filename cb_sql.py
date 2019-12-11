# A set of tools to interact with SQL
import os
import pymssql as msql # Ignore the error message from this. But it means this is lib incompatible with Python 3.8 and above.
import signal 
from datetime import datetime
from localfiles.details import get_read_details, get_write_details
write_info = get_write_details()
read_info = get_read_details()

SQL_JSON = {
    "predef_queries":{
        "init_get_info_query":{
            "cust_tb_id_col":"淘宝会员名",
            "writevals":[
                ("cust_city", "缴费城市"),
                ("shebao_jishu", "社保基数"),
                ("gjj_jishu", "公积金基数"),
                ("shebao_svc_fee", "社保服务费"),
                ("start_date","计费开始日期"),
                ("curr_payment_status", "员工缴费状态")
            ],
            "table": "基本信息",
            "conditions": "where 员工缴费状态='正常缴费' or 员工缴费状态='新进'or 员工缴费状态='新进补缴'"
        },
        "cust_payment_status_query": {
            "cust_tb_id_col":"淘宝会员名",
            "writevals":[
                ("cust_city", "缴费城市")
            ],
            "column":"员工缴费状态", 
            "table": "基本信息",
            "conditions": "where 员工缴费状态='正常缴费' or 员工缴费状态='新进'or 员工缴费状态='新进补缴'"
        },
        "bill_info_history_query": {
            "cust_tb_id_col":"淘宝会员名",
            "writevals":[],
            "column": "账单月份_文本值",
            "table": "billinfo_淘宝_主表",
            "conditions": "where 账单月份_文本值 = '{yyyymm}'"
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

def build_context_info():
    dt_now = datetime.now()
    year = dt_now.year
    month = dt_now.month
    yearmonth_str = str(year) + str(month)
    info_dict = {"yyyymm":yearmonth_str}
    return info_dict

class Alarmy:
    def __init__(self):
        self.job_done = False

    def set_exec_time_limit(self):
        def signal_handler(signum, frame):
            if not self.job_done:
                raise Exception("Timed out!")
            return
        self.job_done = False
        signal.signal(signal.SIGALRM, signal_handler)
        signal.alarm(10)   # Ten seconds

    def alarm_off(self):
        self.job_done = True


class MSSQL_readwriter:
    def __init__(self):
        self.alarmy = Alarmy()

        self.write_conn = None
        self.connect_to_write()

        self.read_conn = None
        self.connect_to_read()

    def connect_to_write(self):
        global SQL_WRITE_ENABLED
        if SQL_WRITE_ENABLED:
            print("Trying to connect to Write...")
            self.alarmy.set_exec_time_limit()
            try:
                self.write_conn = msql.connect(server=db_host, user=db_user, password=db_pass, database=db_dbname)
                self.alarmy.alarm_off()
                print("Connected to Write!")
            except Exception as e:
                print("Write Connection Exception!",e)
                SQL_WRITE_ENABLED = False

        
    def connect_to_read(self):
        global SQL_READ_ENABLED
        if SQL_READ_ENABLED:
            print("Trying to connect to Read...")
            self.alarmy.set_exec_time_limit()
            try:
                self.read_conn = msql.connect(server=db_read_host, user=db_read_user, password=db_read_pass) 
                self.alarmy.alarm_off()
                # read_conn = msql.connect(server=db_read_host, user=db_read_user, password=db_read_pass, database=db_read_dbname) 
                print("Connected to Read!")
            except Exception as e:
                print("Read Connection Exception!",e)
                SQL_READ_ENABLED = False


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

    def fetch_user_info_from_sqltable(self, user_name):
        iq = INITIAL_QUERY
        if DEBUG: print("<SQL FETCH INFO> Looking for {}".format(user_name))
        found, f_dict = self.execute_predef_query(iq, user_name)

        uid_f = f_dict
        return found, uid_f

    def fetch_all_from_sqltable(self,tablename):
        f = self.fetch_all_from_con(tablename)
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

    def execute_predef_query(self, query, uid):
        matchfound = False
        out = {}
        if not SQL_READ_ENABLED:
            return (matchfound, out)
        
        context_info = build_context_info()
        table = query.get("table")
        tb_id_col = query.get("cust_tb_id_col")
        write_vals = query.get("writevals")
        conds = query.get("conditions")
        conds = conds.format(context_info) # Fill with dynamic values
        f_rows = self.fetch_all_from_con(table, condition= conds)
        if DEBUG: print("<PREDEF Q> fetched {} queries".format(str(len(f_rows))))

        count = 0
        
        for row in f_rows:
            if row.get(tb_id_col,"") == uid:
                if DEBUG: print("<PREDEF Q> FOUND a match for {}".format(uid), "L00ked through {} rows".format(count))
                for k, colname in write_vals:
                    out[k] = row.get(colname, "")
                
                matchfound = True
            count += 1

        if out == {}:
            if DEBUG: print("<PREDEF Q> NO MATCH for {}".format(uid))

        return (matchfound, out)

    

asdf = {"alina":{"userID":"小花朵","city":"北京", "首次":"yes"}}

if __name__ == "__main__":
    sqr = MSSQL_readwriter()
    tablename = db_tablename
    uid = "dreampaopao"
    pq = db_read_queries["init_get_info_query"]
    pf = sqr.execute_predef_query(pq, uid)
    print(pf)