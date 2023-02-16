import subprocess
import requests
from flask import Flask, request, json
from jproperties import Properties

configs = Properties()
with open('server.properties', 'rb') as config_file:
  configs.load(config_file)

app = Flask(__name__)

@app.route("/health")
def healthCheck():
  return "alive", 200

@app.route("/page", methods=['POST'])
def page():
  body = json.loads(request.data)
  if not verifyFreqRange(body["frequency"]):
    return "Not in frequency range of server",500
  options = ""
  if body["type"] == "NUMERIC":
    options = "-n"
  page_command = subprocess.run("echo -e \"%s:%s\" | ./pocsag -f %se6 -t 1 %s" % (body["capcode"], body["msg"], body["frequency", options]), shell=True, executable='/bin/bash')
  if page_command.returncode == 0:
    return "Page sent", 200
  else:
    return "Failed to send page",500

def verifyFreqRange(msgFreq):
  freqs = configs.get("frequencies").data
  if freqs != "any":
    if "-" in freqs:
      for freq in freqs.split(","):
        if msgFreq < float(freq.split("-")[0]) or msgFreq > float(freq.split("-")[1]):
          return False 
    else:
      return float(freqs) == float(msgFreq)
  return True

def registerWithManager():
  try:
    req = requests.post("%s/addnode" % (configs.get("manager").data), json = {"name": configs.get("name").data, "address":"http://%s:%s" % (configs.get("ip").data, configs.get("port").data), "location": configs.get("location").data, "frequencies": configs.get("frequencies").data})
    if req.status_code == 200:
      print ("Node has been registered with the pager management server.")
    else:
      raise ValueError("Node failed to register with pager management server: %s" % req.text)
  except requests.exceptions.RequestException:
    print ("Node failed to connect to management server.")
    exit()
  return

registerWithManager()

print("Server is now running on port: %s" % configs.get("port").data)