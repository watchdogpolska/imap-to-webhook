import json

from flask import Flask, request

app = Flask(__name__)


@app.route("/", methods=["GET", "POST", "DELETE"])
def hello():
    content = request.get_json()
    print(content)
    return json.dumps({"status": "OK"})
