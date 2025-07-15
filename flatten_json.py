import json

with open("credentials.json", "r", encoding="utf-8") as f:
    data = json.load(f)
    one_line = json.dumps(data, separators=(",", ":"))
    print(one_line)
