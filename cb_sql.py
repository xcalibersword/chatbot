# A set of tools to interact with SQL
import os
import pymssql as msql # Ignore the error message from this. But it means this is lib incompatible with Python 3.8 and above.
from localfiles.details import get_read_details, get_write_details
read_info = get_read_details()

# DB ACCESS SETTINGS
db_host = read_info["sql_address"]
db_port = read_info["sql_port"]
db_user = read_info["username"]
db_pass = read_info["pass"]
db_dbname = "Northwind"
db_tablename = "dbo.Customers"
db_charset = "utf8mb4"
db_conn = None

SQL_READ_ENABLED = True
LOCALFILES_PRESENT = ""
NO_WRITE_TO_SQL = False and SQL_READ_ENABLED

# db_host = "40.68.37.158" #ADVENTURE WORKS
# db_user = "Sample user"
# db_pass = "password"
# db_dbname = "AdventureWorks2012"

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
    
def connect_to_T430():
    global db_conn

    if SQL_READ_ENABLED:
        db_conn = msql.connect(server=db_host, user=db_user, password=db_pass, database=db_dbname) 
        print("Connected!")

    return db_conn

def insert_test():
    connection = db_conn
    try:
        vals = ('我是个鸟儿', '甲城市')
        slots = "(userID, city)"
        # vals = ('testuid', 'abc')
        sqlcmd = "INSERT INTO " + tablename + " " + slots + " VALUES (%s, %s)"
        print("query:",sqlcmd)
        commit_to_con(connection, sqlcmd, vals)
        
        sql = "SELECT * FROM " + tablename
        sqlval = ()
        fetch_from_con(connection, sql, sqlval)
    finally:
        connection.close()

def fetch_from_con(con, sql, sqlvals):        
    if check_local_files_bad(sql):
        return ()

    with con.cursor() as cursor:
        cursor.execute(sql, sqlvals)
        result = cursor.fetchall()
    print(result)
    return result

def fetch_all_from_con(tabnam, columns = "*", condition = ""):
    query = "SELECT {} FROM {} {}".format(columns,tabnam,condition)
    if check_local_files_bad(query):
        return ()

    stdcon = db_conn
    with stdcon.cursor() as cursor:
        cursor.execute(query,[])
        result = cursor.fetchall()
    return result

def fetch_lines_from_table(tablename, column_name, value):
    cond = "WHERE " + column_name + "='" + str(value) + "'"
    f = fetch_all_from_con(tablename, condition = cond)
    return f

def fetch_all_from_sqltable():
    f = fetch_all_from_con(tablename)
    if len(f) > 0:
        f = f[0]
    return f

# Writes to the connection
def commit_to_con(conn, comcmd, comvals):
    if NO_WRITE_TO_SQL:
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
def write_to_sqltable(info):
    if not SQL_READ_ENABLED:
        return 
    connection = db_conn
    userids = fetch_all_from_con(tablename, columns = "userID")
    userids = map(lambda x: x['userID'],userids)
    print("uids",userids)
    
    users = list(info.keys())
    
    for uk in users:
        userinfo = info[uk].copy()
        vals = list(userinfo.values())
        print("uinfo",userinfo)
        cols = ', '.join(userinfo.keys())
        qmarks = ', '.join(['%s'] * len(userinfo)) # Generates n * ? separated by commas
        if uk in userids:
            delq = "DELETE FROM %s WHERE userID = '%s'" % (tablename, uk)
            commit_to_con(connection, delq, ())

        qry = "INSERT INTO %s (%s) VALUES (%s)" % (tablename, cols, qmarks)
        commit_to_con(connection, qry, vals)

asdf = {"alina":{"userID":"小花朵","city":"北京", "首次":"yes"}}

# write_to_sqltable(tablename,asdf)
if __name__ == "__main__":
    connect_to_T430()
    tablename = db_tablename
    # r = fetch_all_from_con(tablename)
    # print(r)
    f = fetch_lines_from_table(tablename,"CustomerID","RICSU")
    print(f)