import requests
import time
for i in range(1):
    r = requests.get("https://rate-limiter-module-app.herokuapp.com/useapi")
    print(r.status_code)

