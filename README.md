# Rate_Limiter

In order to use the module, using the guidelines for the required tables and columns in the secrets.py file, create a database in postgres 
and update the values in the secrets.py file (or feel free to create your own secrets.py file). You need to have postgres installed and it would be 
helpful to have pgadmin installed so you can easily create new databases (it is a much nicer UI than the terminal). 

The values in secrets.py are imported into the rate limiter module. From there, import the rateLimiter.py module for use in your API and call the functions you would like in areas
in your code where you would like to check for API usage such that when a user calls the API, the functions are automatically called. You can create
custom error messages based on the output of track_api_usage (a False return value could prompt an error to the user that lets them know that the 
rate limit was exceeded). 

To test this, simply call your API and the functions will be executed. You can call the functions you would like without having to 
input an IP address as the track_api_usage function will get the IP address of the client. You have the option of inputting a userID (if you have access 
to it), which will also be handled. You should be able to see additions to your database tables as you track the API usage of new IP addresses and 
new userIDs and view updates to their requests. Calling tracked_usage will return a hash of all the requests per IP address and userID that you have
seen thus far. 
