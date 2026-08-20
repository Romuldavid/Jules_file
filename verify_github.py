import urllib.request
import json

url = "https://api.github.com/repos/Romuldavid/Jules_file/contents?ref=main"
req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})

try:
    with urllib.request.urlopen(req) as response:
        data = json.loads(response.read().decode())
        print("Files in main branch on GitHub:")
        for item in data:
            print(" -", item["name"])
except Exception as e:
    print("Error querying GitHub API:", e)
