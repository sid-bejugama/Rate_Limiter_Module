import psycopg2
from secrets import dbname, username, password, IP_table, userID_table, IP_addresses, IP_requests, IP_start_requests, IP_users, userIDs, user_requests, user_start_requests
from datetime import datetime
import socket

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
def _getConnection():
    global _connection
    try:
        _connection = psycopg2.connect(f"dbname = {dbname}, user = {username}, password = {password}, cursor_factory=RealDictCursor")
        return _connection
    except:
        raise("Error while connecting to database. Make sure that the database name, username, and/or password are entered correctly. Make sure that the database has been created.")
 

# adds a new IP address to the database
def _addIPAddress(IPAddress, cur, userID = None):
    postgreSQL_insert_Query = f""" INSERT INTO {IP_table} ({IP_addresses, IP_requests, IP_start_requests, IP_users}) VALUES (%s,%s,%s,%s)"""
    if userID:
        cur.execute(postgreSQL_insert_Query, (IPAddress, 0, datetime.now(), [userID]))
    else:
        cur.execute(postgreSQL_insert_Query, (IPAddress, 0, datetime.now(), []))

# adds a new user to the database and updates the users associated with a given IP address
def _addUser(userID, IPAddress, IP_info, cur):
    postgreSQL_update_query = f"""Update {IP_table} set {IP_users} = %s where {IP_addresses} = %s"""
    new_IP_info = IP_info[0][f"{userID}"].append(userID)
    cur.execute(postgreSQL_update_query, (new_IP_info, IPAddress))

    postgreSQL_insert_Query = f""" INSERT INTO {userID_table} ({userIDs}, {user_requests}, {user_start_requests}) VALUES (%s,%s,%s)"""
    cur.execute(postgreSQL_insert_Query, (userID, 1, datetime.now()))

# monitors the api usage for a given IP address and userID. Returns True if a given IP address and/or userID is allowed to use the api in the current time interval and returns False otherwise based on the parameters set
def track_api_usage(userID = None):
    # get client IP address
    host_name = socket.gethostname()    
    IPAddress = socket.gethostbyname(host_name)

    # connect to database
    if not _connection: connection = _getConnection()
    cur = connection.cursor()

    # obtain information corresponding to given IP address
    postgreSQL_select_Query = f"select * from {IP_table} where {IP_addresses} = %s"
    cur.execute(postgreSQL_select_Query, (IPAddress, ))
    IP_info = cur.fetchall()

    # add a new IP address if given IP address was not found
    if len(IP_info) == 0: 
        _addIPAddress(IPAddress, cur, userID)
        IP_info = cur.fetchall()
    
    # check whether the rate limit was exceeded
    curr_datetime = datetime.now()
    curr_IP_interval = (curr_datetime - IP_info[0][f"{IP_start_requests}"]).total_seconds()
    if curr_IP_interval <= limit_interval and IP_info[0][f"{IP_requests}"] > IP_request_limit:
        return False
    
    # reset the starting time for requests for the given IP address and reset the current number of requests in the interval if time interval exceeded
    if curr_IP_interval > limit_interval:
        postgreSQL_update_query = f"""Update {IP_table} set {IP_start_requests} = %s, {IP_requests} = %s where {IP_addresses} = %s"""
        
        cur.execute(postgreSQL_update_query, (datetime.now(), 0, IPAddress))
    
    # increment the number of requests
    postgreSQL_update_query = f"""Update {IP_table} set {IP_requests} = %s where {IP_addresses} = %s""" 
    cur.execute(postgreSQL_update_query, (IP_info[0][f"{IP_requests}"] + 1, IPAddress))

    # protocol if optional userID is passed in
    if userID:
        # protocol for if the userID is already registered for the given IP address
        if userID in IP_info[0][f"{userID}"]:
                # get user-specific information
                postgreSQL_select_Query = f"select * from {userID_table} where {userIDs} = %s"
                cur.execute(postgreSQL_select_Query, (userID, ))
                user_info = cur.fetchall()

                # check whether the user has exceeded the user-specific rate limit
                curr_user_interval = (curr_datetime - user_info[0][f"{user_start_requests}"]).total_seconds()
                if curr_user_interval <= limit_interval and user_info[0][f"{user_requests}"] > user_request_limit:
                    return False
                
                 # reset the starting time for requests for the given userID and reset the current number of requests in the interval if time interval exceeded
                if curr_user_interval > limit_interval:
                    postgreSQL_update_query = f"""Update {userID_table} set {user_start_requests} = %s, {user_requests} = %s where {userIDs} = %s"""

                    cur.execute(postgreSQL_update_query, (datetime.now(), 0, userID))
                
                # increment the number of requests for the user 
                postgreSQL_update_query = f"""Update {userID_table} set {user_requests} = %s where {userIDs} = %s"""
                cur.execute(postgreSQL_update_query, (user_info[0][f"{user_requests}"] + 1, userID))
        else:
            # if the given user is not found in the list of users, create a new user
            _addUser(userID, IPAddress, IP_info, cur)
    
    # commit all changes in the database and close connection
    _connection.commit()
    cur.close()
    _connection.close()
    
    # signal that the api can be used
    return True
    
# returns a hash of the current number of requests for each identifier (IP addresses and userIDs up to 20)
def tracked_usage():
    # connect to database
    if not _connection: connection = _getConnection()
    cur = connection.cursor()

    # get all IP address information
    postgreSQL_select_Query = f"select * from {IP_table}"
    cur.execute(postgreSQL_select_Query)
    IP_info = cur.fetchall()

    # set up hash
    allInfoHash = {}

    # traverse through rows in IP address table
    for row in IP_info:
        # current number of requests for given IP address
        allInfoHash[row[f"{IP_addresses}"]] = row[f"{IP_requests}"]
        # for each user associated with a given IP address, record current number of requests
        for userID in row[3]:
            postgreSQL_select_Query = f"select * from {userID_table} where {userIDs} = %s"
            cur.execute(postgreSQL_select_Query, (userID, ))
            userID_info = cur.fetchall()
            allInfoHash[userID_info[0][f"{userIDs}"]] = userID_info[0][f"{user_requests}"] 
    
    # close connection
    cur.close()
    connection.close()

    return allInfoHash







                

                






