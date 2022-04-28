from flask import Flask, redirect, url_for, request
from rateLimiter import *
import psycopg2
import psycopg2.extras
import os
  
app = Flask(__name__)

@app.route('/useapi/')
def useAPI():
    if request.environ.get('HTTP_X_FORWARDED_FOR') is None:
        ip_address = request.environ['REMOTE_ADDR']
    else:
        ip_address = request.environ['HTTP_X_FORWARDED_FOR']
    user_id = request.args.get('userID', None)
    
    APILimit = track_api_usage(ip_address, cur, conn, user_id)

    if APILimit: return redirect(url_for('success', IPAddress=ip_address, userID=user_id))

    else: return redirect(url_for('error'))

@app.route("/")
def base_route():
    return "Welcome!"

@app.route("/hashed")
def get_hash():
    return tracked_usage(cur)

@app.route('/error')
def error():
    return "Too many requests", 429
  
@app.route('/success/')
def success():
    ip = request.args.get("IPAddress")
    userId = request.args.get("userID", None)
    returnVal = f'Your IPAddress is: {ip}.'
    if userId: return returnVal + f' Your userID is {userId}'
    else:
        return returnVal + f' You are not logged in.'

  
# main driver function
if __name__ == '__main__':
  
    # run() method of Flask class runs the application 
    # on the local development server.
    conn = getConnection()
    cur = conn.cursor(cursor_factory = psycopg2.extras.RealDictCursor)
    port = int(os.environ.get("PORT", 33507))
    app.run(host='0.0.0.0', port=port)