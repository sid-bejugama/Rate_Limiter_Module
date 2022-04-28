import requests
import time
for i in range(51):
    r = requests.get("http://127.0.0.1:5000/useapi")
    print(r.text, i)
    time.sleep(.1)

