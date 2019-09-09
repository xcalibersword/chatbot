#get entity, get answer from DB, get response, store param for future use, negation

import sqlite3
import pandas
#connect to a database .db
conn = sqlite3.connect(r"F:\Codes\Internship (chatbot)\DataCamp\hotels.db")
c = conn.cursor()
#can be obtained using rasa nlu or any other nlu engine
#entities = rasa.interpreter.parse(message)

data = {
'entities': 
    [
        {'end': '7', 'entity': 'price', 'start': 2, 'value': 'lo'}, 
        {'end': 26, 'entity': 'location', 'start': 21, 'value': 'north'}
    ], 

'intent': 
    {
    'confidence': 0.9, 'name': 'hotel_search'
    }
}
params = {}
#takes all the entity as parameter
for ent in data["entities"]:
    params[ent["entity"]] = ent["value"]
print(params)
#this will be based on the intent found
query = "select name from hotels"
#template per entity for sql query
filters = ["{}=?".format(k) for k in params.keys()]
print(filters)
#forming the query
conditions = " and ".join(filters)
final_q = " where ".join([query,conditions])
print(final_q)
#getting the value from the entity detected
t = tuple(params.values())
print(t)
#fetching result from sql database
c.execute(final_q,t)
results = c.fetchall()

#get the column required

#select the right response

#save param, reply user

#negation parameter to take note of what the user do not want, to differentiate from what the user wants
