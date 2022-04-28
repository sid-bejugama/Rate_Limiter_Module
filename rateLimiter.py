import psycopg2
from secrets import dbname, username, password, IP_table, userID_table, IP_addresses, IP_requests, IP_start_requests, IP_users, userIDs, user_requests, user_start_requests, user_interval, user_limit, IP_interval, IP_limit
from datetime import datetime
from flask import request

# sets up the connection to a database where IP address and user information are stored
def getConnection():
    try:
        _connection = psycopg2.connect(f"dbname = {dbname} user = {username} password = {password}")
        return _connection
    except:
        raise("Error while connecting to database. Make sure that the database name, username, and/or password are entered correctly. Make sure that the database has been created.")
 

# adds a new IP address to the database

# changed this so that the IP address is not initialized with a user regardless of whether the user is logged in. The user is added later when creating a new user.
def _addIPAddress(IPAddress, cur):
    # before, the code looked like this:

    #postgreSQL_insert_Query = f"""INSERT INTO "{IP_table}" ("{IP_addresses}", "{IP_requests}", "{IP_start_requests}", "{IP_users}") VALUES ('{IPAddress}', '{0}', '{datetime.now()}', "{userID}")"""

    #This caused a problem because a new IP address initialized with a userID would then prevent a new user from being added into the user table as it would not enter the code block starting on line 122

    # sets default values of 10 and 50 for the interval and limit, respectively
    postgreSQL_insert_Query = f"""INSERT INTO "{IP_table}" ("{IP_addresses}", "{IP_requests}", "{IP_start_requests}", "{IP_interval}", "{IP_limit}") VALUES ('{IPAddress}', '{0}', '{datetime.now()}', '{10}', '{50}')"""
        
    cur.execute(postgreSQL_insert_Query)

# adds a new user to the database and updates the users associated with a given IP address
def _addUser(userID, IPAddress, IP_info, cur):
    IP_info[0][f"{IP_users}"].append(userID)
    postgreSQL_update_query = f"""Update "{IP_table}" set "{IP_users}" = ARRAY{IP_info[0][f"{IP_users}"]} where "{IP_addresses}" = '{IPAddress}'"""
    
    cur.execute(postgreSQL_update_query)

    # sets default values of 20, 10 for the limit and interval, respectively
    postgreSQL_insert_Query = f""" INSERT INTO "{userID_table}" ("{userIDs}", "{user_requests}", "{user_start_requests}", "{user_limit}", "{user_interval}") VALUES ('{userID}', '{0}', '{datetime.now()}', '{20}', '{10}')"""

    cur.execute(postgreSQL_insert_Query)

# monitors the api usage for a given IP address and userID. Returns True if a given IP address and/or userID is allowed to use the api in the current time interval and returns False otherwise based on the parameters set
def track_api_usage(IPAddress, cur, _connection, userID):

    # obtain information corresponding to given IP address
    postgreSQL_select_Query = f"""SELECT * FROM "{IP_table}" WHERE "{IP_addresses}" = '{IPAddress}'"""
    cur.execute(postgreSQL_select_Query)
    IP_info = cur.fetchall()

    # add a new IP address if given IP address was not found
    if len(IP_info) == 0: 
        _addIPAddress(IPAddress, cur)
        postgreSQL_select_Query = f"""SELECT * FROM "{IP_table}" WHERE "{IP_addresses}" = '{IPAddress}'"""
        cur.execute(postgreSQL_select_Query)
        IP_info = cur.fetchall()
    
    # check whether the rate limit was exceeded
    curr_datetime = datetime.now()
    curr_IP_interval = (curr_datetime - IP_info[0][f"{IP_start_requests}"]).total_seconds()
    if curr_IP_interval <= IP_info[0][f"{IP_interval}"] and IP_info[0][f"{IP_requests}"] >= IP_info[0][f"{IP_limit}"]:
        return False
    # reset the starting time for requests for the given IP address and reset the current number of requests in the interval if time interval exceeded
    IPreset = False
    if curr_IP_interval > IP_info[0][f"{IP_interval}"]:
        IPreset = True
        postgreSQL_update_query = f"""Update "{IP_table}" set "{IP_start_requests}" = '{datetime.now()}', "{IP_requests}" = '{0}' where "{IP_addresses}" = '{IPAddress}'"""
        cur.execute(postgreSQL_update_query)

    
    # increment the number of requests
    if IPreset:
        postgreSQL_select_Query = f"""SELECT * FROM "{IP_table}" WHERE "{IP_addresses}" = '{IPAddress}'"""
        cur.execute(postgreSQL_select_Query)
        IP_info = cur.fetchall()
    
    postgreSQL_update_query = f"""Update "{IP_table}" set "{IP_requests}" = '{IP_info[0][f"{IP_requests}"] + 1}' where "{IP_addresses}" = '{IPAddress}'""" 
    cur.execute(postgreSQL_update_query)

    # protocol if optional userID is passed in
    if userID:
        # protocol for if there are no users associated with the given IP address yet

        # this is where the problem arose because the new IP address would be initialized with a userID if a user is logged in the first time an IP address is used to make a request
        if not IP_info[0][f"{IP_users}"]:
            IP_info[0][f"{IP_users}"] = []
            _addUser(userID, IPAddress, IP_info, cur)
        # protocol for if the userID is already registered for the given IP address
        if userID in IP_info[0][f"{IP_users}"]:
                # get user-specific information
                postgreSQL_select_Query = f"""select * from "{userID_table}" where "{userIDs}" = '{userID}'"""
                cur.execute(postgreSQL_select_Query)
                user_info = cur.fetchall()


                # check whether the user has exceeded the user-specific rate limit
                curr_user_interval = (curr_datetime - user_info[0][f"{user_start_requests}"]).total_seconds()
                if curr_user_interval <= user_info[0][f"{user_interval}"] and user_info[0][f"{user_requests}"] >= user_info[0][f"{user_limit}"]:
                    return False
                
                # reset the starting time for requests for the given userID and reset the current number of requests in the interval if time interval exceeded
                userReset = False
                if curr_user_interval > user_info[0][f"{user_interval}"]:
                    userReset = True
                    postgreSQL_update_query = f"""Update "{userID_table}" set "{user_start_requests}" = '{datetime.now()}', "{user_requests}" = '{0}' where "{userIDs}" = '{userID}'"""

                    cur.execute(postgreSQL_update_query)
                
                # increment the number of requests for the user 
                if userReset:
                    postgreSQL_select_Query = f"""select * from "{userID_table}" where "{userIDs}" = '{userID}'"""
                    cur.execute(postgreSQL_select_Query)
                    user_info = cur.fetchall()

                postgreSQL_update_query = f"""Update "{userID_table}" set "{user_requests}" = '{user_info[0][f"{user_requests}"] + 1}' where "{userIDs}" = '{userID}'"""
                cur.execute(postgreSQL_update_query)
        else:
            # if the given user is not found in the list of users, create a new user
            _addUser(userID, IPAddress, IP_info, cur)
    
    # commit all changes in the database
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







                

                






