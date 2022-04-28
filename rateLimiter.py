import psycopg2
from secrets import dbname, username, password, IP_table, userID_table, IP_addresses, IP_requests, IP_start_requests, IP_users, userIDs, user_requests, user_start_requests
from datetime import datetime
from flask import request

_connection = None

# number of requests per IP address in a given time interval
IP_request_limit = 50 

# number of requests per user in a given time interval
user_request_limit = 20

# time interval in which current number of requests are tracked
limit_interval = 10

# provides the ability to adjust the number of requests allotted per IP address in a given interval of time
def set_IP_request_limit(limit):
    global IP_request_limit
    IP_request_limit = limit

# provides the ability to adjust the number of requests allotted per user in a given interval of time
def set_user_request_limit(limit):
    global user_request_limit
    user_request_limit = limit

# provides the ability to adjust the interval of time in which current requests are tracked
def set_limit_interval(interval):
    global limit_interval
    limit_interval = interval


# sets up the connection to a database where IP address and user information are stored
def getConnection():
    global _connection
    try:
        _connection = psycopg2.connect(f"dbname = {dbname} user = {username} password = {password}")
        return _connection
    except:
        raise("Error while connecting to database. Make sure that the database name, username, and/or password are entered correctly. Make sure that the database has been created.")
 

# adds a new IP address to the database
def _addIPAddress(IPAddress, cur, userID = None):
    if userID:
        postgreSQL_insert_Query = f"""INSERT INTO "{IP_table}" ("{IP_addresses}", "{IP_requests}", "{IP_start_requests}", "{IP_users}") VALUES ('{IPAddress}', '{0}', '{datetime.now()}', ARRAY{[userID]})"""
        
        cur.execute(postgreSQL_insert_Query)
    else:
        postgreSQL_insert_Query = f"""INSERT INTO "{IP_table}" ("{IP_addresses}", "{IP_requests}", "{IP_start_requests}") VALUES ('{IPAddress}', '{0}', '{datetime.now()}')"""
        
        cur.execute(postgreSQL_insert_Query)

# adds a new user to the database and updates the users associated with a given IP address
def _addUser(userID, IPAddress, IP_info, cur):
    IP_info[0][f"{IP_users}"].append(userID)
    postgreSQL_update_query = f"""Update "{IP_table}" set "{IP_users}" = ARRAY{IP_info[0][f"{IP_users}"]} where "{IP_addresses}" = '{IPAddress}'"""
    
    cur.execute(postgreSQL_update_query)

    postgreSQL_insert_Query = f""" INSERT INTO "{userID_table}" ("{userIDs}", "{user_requests}", "{user_start_requests}") VALUES ('{userID}', '{1}', '{datetime.now()}')"""
    cur.execute(postgreSQL_insert_Query)

# monitors the api usage for a given IP address and userID. Returns True if a given IP address and/or userID is allowed to use the api in the current time interval and returns False otherwise based on the parameters set
def track_api_usage(IPAddress, cur, _connection, userID):

    # obtain information corresponding to given IP address
    postgreSQL_select_Query = f"""SELECT * FROM "{IP_table}" WHERE "{IP_addresses}" = '{IPAddress}'"""
    cur.execute(postgreSQL_select_Query)
    IP_info = cur.fetchall()

    # add a new IP address if given IP address was not found
    if len(IP_info) == 0: 
        _addIPAddress(IPAddress, cur, userID)
        postgreSQL_select_Query = f"""SELECT * FROM "{IP_table}" WHERE "{IP_addresses}" = '{IPAddress}'"""
        cur.execute(postgreSQL_select_Query)
        IP_info = cur.fetchall()
    
    # check whether the rate limit was exceeded
    curr_datetime = datetime.now()
    curr_IP_interval = (curr_datetime - IP_info[0][f"{IP_start_requests}"]).total_seconds()
    if curr_IP_interval <= limit_interval and IP_info[0][f"{IP_requests}"] >= IP_request_limit:
        return False
    # reset the starting time for requests for the given IP address and reset the current number of requests in the interval if time interval exceeded
    if curr_IP_interval > limit_interval:
        postgreSQL_update_query = f"""Update "{IP_table}" set "{IP_start_requests}" = '{datetime.now()}', "{IP_requests}" = '{0}' where "{IP_addresses}" = '{IPAddress}'"""
        cur.execute(postgreSQL_update_query)

    
    # increment the number of requests
    postgreSQL_select_Query = f"""SELECT * FROM "{IP_table}" WHERE "{IP_addresses}" = '{IPAddress}'"""
    cur.execute(postgreSQL_select_Query)
    IP_info = cur.fetchall()
    
    postgreSQL_update_query = f"""Update "{IP_table}" set "{IP_requests}" = '{IP_info[0][f"{IP_requests}"] + 1}' where "{IP_addresses}" = '{IPAddress}'""" 
    cur.execute(postgreSQL_update_query)

    # protocol if optional userID is passed in
    if userID:
        # protocol for if the userID is already registered for the given IP address
        if not IP_info[0][f"{IP_users}"]:
            IP_info[0][f"{IP_users}"] = []
            _addUser(userID, IPAddress, IP_info, cur)
        if userID in IP_info[0][f"{IP_users}"]:
                # get user-specific information
                postgreSQL_select_Query = f"""select * from "{userID_table}" where "{userIDs}" = '{userID}'"""
                cur.execute(postgreSQL_select_Query)
                user_info = cur.fetchall()

                # check whether the user has exceeded the user-specific rate limit
                curr_user_interval = (curr_datetime - user_info[0][f"{user_start_requests}"]).total_seconds()
                if curr_user_interval <= limit_interval and user_info[0][f"{user_requests}"] >= user_request_limit:
                    return False
                
                 # reset the starting time for requests for the given userID and reset the current number of requests in the interval if time interval exceeded
                if curr_user_interval > limit_interval:
                    postgreSQL_update_query = f"""Update "{userID_table}" set "{user_start_requests}" = '{datetime.now()}', "{user_requests}" = '{0}' where "{userIDs}" = '{userID}'"""

                    cur.execute(postgreSQL_update_query)
                
                # increment the number of requests for the user 
                postgreSQL_select_Query = f"""select * from "{userID_table}" where "{userIDs}" = '{userID}'"""
                cur.execute(postgreSQL_select_Query)
                user_info = cur.fetchall()

                postgreSQL_update_query = f"""Update "{userID_table}" set "{user_requests}" = '{user_info[0][f"{user_requests}"] + 1}' where "{userIDs}" = '{userID}'"""
                cur.execute(postgreSQL_update_query)
        else:
            # if the given user is not found in the list of users, create a new user
            _addUser(userID, IPAddress, IP_info, cur)
    
    # commit all changes in the database and close connection
    _connection.commit()
    
    # signal that the api can be used
    return True
    
# returns a hash of the current number of requests for each identifier (IP addresses and userIDs up to 20)
def tracked_usage(cur):

    # get all IP address information
    postgreSQL_select_Query = f'select * from "{IP_table}"'
    cur.execute(postgreSQL_select_Query)
    IP_info = cur.fetchall()

    # set up hash
    allInfoHash = {}

    # traverse through rows in IP address table
    for row in IP_info:
        # current number of requests for given IP address
        allInfoHash[row[f"{IP_addresses}"]] = row[f"{IP_requests}"]
        # for each user associated with a given IP address, record current number of requests
        for userID in row[f"{IP_users}"]:
            postgreSQL_select_Query = f"""select * from "{userID_table}" where "{userIDs}" = '{userID}'"""
            cur.execute(postgreSQL_select_Query)
            userID_info = cur.fetchall()
            allInfoHash[userID] = userID_info[0][f"{user_requests}"] 

    return allInfoHash







                

                






