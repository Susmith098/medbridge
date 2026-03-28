import urllib.request
import json

url = 'http://localhost:5000/api/analyze'
data = {'text': "conscious but very confused, keeps asking what happened. There is heavy bleeding from his head and his right leg looks twisted in a wrong direction. He said his name is Rajan. He is diabetic and takes metformin. He is allergic to penicillin. Accident happened about 15 minutes ago."}
data = json.dumps(data).encode('utf-8')
req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})

try:
    with urllib.request.urlopen(req) as response:
        result = response.read()
        print("SUCCESS:", result.decode('utf-8'))
except urllib.error.HTTPError as e:
    print("FAILED:", e.code, e.read().decode('utf-8'))
except Exception as e:
    print("ERROR:", repr(e))
