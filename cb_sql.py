# A set of tools to interact with SQL

# import pymysql
# import pymssql
from localfiles.details import get_all_details
cached_info = get_all_details()


# DB ACCESS SETTINGS
db_host = cached_info["sql_address"]
db_port = cached_info["sql_port"]
db_user = cached_info["username"]
db_pass = cached_info["pass"]
db_dbname = "chatbot_schema"
db_charset = "utf8mb4"
# db_cc = pymysql.cursors.DictCursor

tablename = "table1"

SQL_ENABLED = False

NO_WRITE_TO_SQL = False and SQL_ENABLED

if SQL_ENABLED:
    stdcon = {}
    # stdcon = pymysql.connect(host=db_host,
    #                         user=db_user,
    #                         password=db_pass,
    #                         db=db_dbname,
    #                         charset=db_charset,
    #                         cursorclass=pymysql.cursors.DictCursor)

def hello():
    # connection = pymysql.connect(host=db_host,
    #                         user=db_user,
    #                         password=db_pass,
    #                         db=db_dbname,
    #                         charset=db_charset,
    #                         cursorclass=pymysql.cursors.DictCursor)
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
    if not SQL_ENABLED:
        print("<BACKEND WARNING: Reading from SQL has been disabled> Restore it in cb_sql.py.\nCommand not executed:{}".format(sql))
        return ()
    with con.cursor() as cursor:
        cursor.execute(sql, sqlvals)
        result = cursor.fetchall()
    print(result)
    return result

def fetch_all_from_con(tabnam, columns = "*", condition = ""):
    if not SQL_ENABLED:
        print("<BACKEND WARNING: Reading from SQL has been disabled> Restore it in cb_sql.py.\n")
        return ()
    query = "SELECT {} FROM {} {}".format(columns,tabnam,condition)
    print("Q:", query)
    with stdcon.cursor() as cursor:
        cursor.execute(query,[])
        result = cursor.fetchall()
    return result

def commit_to_con(con, comcmd, comvals):
    if NO_WRITE_TO_SQL:
        print("<BACKEND WARNING: Writing to SQL has been disabled> Restore it in cb_sql.py.\nCommand not executed:{}".format(comcmd))
        return

    try:
        with con.cursor() as cursor:
            cursor.execute(comcmd, comvals)

        # connection is not autocommit by default. Must commit to save changes.
        con.commit()
        print("Committed to db")
    except Exception as e:
        print("EXCEPTION! Rolling back", e)
        print("Failed command:",comcmd)
        con.rollback()

def fetch_uid_from_sqltable(userID):
    cond = "WHERE userID='" + str(userID) + "'"
    f = fetch_all_from_con(tablename, condition = cond)
    if len(f) > 0:
        f = f[0]
    return f

def fetch_all_from_sqltable():
    f = fetch_all_from_con(tablename)
    if len(f) > 0:
        f = f[0]
    return f

# Writes to a predefined table
def write_to_sqltable(info):
    if not SQL_ENABLED:
        return 
    connection = stdcon
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
    r = fetch_all_from_con(tablename)
    print(r)
    f = fetch_uid_from_sqltable("hoe")
    print(f)