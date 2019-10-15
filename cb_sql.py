# A set of tools to interact with SQL

import pymysql

tablename = "table1"

stdcon = pymysql.connect(host='localhost',
                            user='root',
                            password='abcd1234',
                            db='chatbot_schema',
                            charset='utf8mb4',
                            cursorclass=pymysql.cursors.DictCursor)

def hello():
    connection = pymysql.connect(host='localhost',
                                user='root',
                                password='abcd1234',
                                db='chatbot_schema',
                                charset='utf8mb4',
                                cursorclass=pymysql.cursors.DictCursor)
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
        with con.cursor() as cursor:
            cursor.execute(sql, sqlvals)
            result = cursor.fetchall()
        print(result)
        return result

def fetch_all_from_con(tabnam):
    query = "SELECT * FROM " + tabnam
    with stdcon.cursor() as cursor:
        cursor.execute(query,[])
        result = cursor.fetchall()
    return result

def commit_to_con(con, comcmd, comvals):
    try:
        with con.cursor() as cursor:
            # Create a new record
            cursor.execute(comcmd, comvals)

        # connection is not autocommit by default. So you must commit to save
        # your changes.
        con.commit()
    except Exception as e:
        print("EXCEPTION! Rolling back", e)
        print("command",comcmd)
        con.rollback()
    finally:
        print("Committed")


def write_to_sqltable(tablename, info):
    connection = pymysql.connect(host='localhost',
                                user='root',
                                password='abcd1234',
                                db='chatbot_schema',
                                charset='utf8mb4',
                                cursorclass=pymysql.cursors.DictCursor)

    users = list(info.keys())
    
    for uk in users:
        userinfo = info[uk]
        vals = list(userinfo.values())
        print("v",vals)
        cols = ', '.join(userinfo.keys())
        qmarks = ', '.join(['%s'] * len(userinfo)) # Generates n * ? separated by commas
        qry = "INSERT INTO %s (%s) VALUES (%s)" % (tablename, cols, qmarks)
        commit_to_con(connection, qry, vals)

asdf = {"alina":{"userID":"小花朵","city":"北京", "首次":"yes"}}
# write_to_sqltable(tablename,asdf)
r = fetch_all_from_con(tablename)
print(r)