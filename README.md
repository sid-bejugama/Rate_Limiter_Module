# Rate_Limiter

In order to use the module, using the guidelines for the required tables and columns in the secrets.py file, create a database in postgres 
and update the values in the secrets.py file (or feel free to create your own secrets.py file). You need to have postgres installed and it would be 
helpful to have pgadmin installed so you can easily create new databases (it is a much nicer UI than the terminal). 

The values in secrets.py are imported into the rate limiter module. From there, import the rateLimiter.py module for use in your API and call the functions you would like in areas
in your code where you would like to check for API usage such that when a user calls the API, the functions are automatically called. You can create
custom error messages based on the output of track_api_usage (a False return value could prompt an error to the user that lets them know that the 
rate limit was exceeded). An example server is created and a sample client is provided for you to run. Simply run the server locally and run the python test client, updating parameters, number of requests, etc. as you;d like. You have the option of inputting a userID as a url-encoded parameter. which will also be handled. You should be able to see additions to your database tables as you track the API usage of new IP addresses and 
new userIDs and view updates to their requests. You can also manually adjust the user-specific and IP-specific limits on requests and the intervals within which requests are tracked in your database. Calling tracked_usage will return a hash of all the requests per IP address and userID that you have
seen thus far. 
