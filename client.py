import requests
import time
for i in range(67):
    r = requests.get("http://127.0.0.1:5000/useapi?userID=sid")
    print(r.text, i)

