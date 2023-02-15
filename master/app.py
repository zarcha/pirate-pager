import sqlite3
import requests
import re
from threading import Thread
from time import sleep
from flask import Flask, request, json
from jproperties import Properties

app = Flask(__name__, static_url_path='/static')

configs = Properties()
with open('server.properties', 'rb') as config_file:
    configs.load(config_file)

def createDB():
    connection = sqlite3.connect(configs.get("db").data)
    cur = connection.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS nodes (name PRIMARY KEY UNIQUE, address, location, frequencies, status)")  
    cur.execute("CREATE TABLE IF NOT EXISTS pagers (handle PRIMARY KEY UNIQUE, capcode, frequency, nodes)")

@app.route("/")
def webSendPage():
    html = """
    <form action="/fsendpage" method="post">
        <label for="capcode">Pager Capcode or Handle:</label><br>
        <input type="text" style="width: 100%; height: 30px" id="key" name="key" placeholder="0000000/pageMan69" required><br>
        <label for="msg">Message:</label><br>
        <input type="text" style="width: 100%; height: 30px" id="msg" name="msg" value="Hello World!" required><br><br>
        <input type="submit" style="width: 70px; height: 30px; font-weight: bold" value="Send">
    </form>"""
    return createHtmlPage(html), 200

@app.route("/add")
def webAddPager():
    html = """
    <p>Using the same handle as another pager will overwirte their data, you can use that to also update your own pager information</p>
    <form action="/faddpager" method="post">
        <label for="capcode">Handle (No spaces and no special characters):</label><br>
        <input type="text" style="width: 100%; height: 30px" id="handle" pattern="^\w[a-zA-Z0-9.]*$" name="handle" placeholder="pageMan69" required><br>
        <label for="capcode">Capcode (7 digit pager identifier):</label><br>
        <input type="text" style="width: 100%; height: 30px" id="capcode" pattern="[0-9]{7}" name="capcode" placeholder="0000000" required><br>
        <label for="msg">frequency:</label><br>
        <input type="number" style="width: 100%; height: 30px" step="0.0001" id="frequency" name="frequency" placeholder="000.0000" required><br>
        <label for="msg">Nodes (Comma seperated list of node to receive pages from):</label><br>
        <input type="text" style="width: 100%; height: 30px" id="nodes" name="nodes" value="" required><br><br>
        <input type="submit" style="width: 70px; height: 30px; font-weight: bold" value="Send">
    </form>"""
    return createHtmlPage(html), 200

@app.route("/pagers")
def webPagers():
    html = """
        <h3>Pager List</h3>
        <table>
            <tbody>
                <tr>
                    <th style="width: 430px; text-align: left">
                        Handle
                    </th>
                    <th style="width: 70px;">
                        Capcode
                    </th>
                </tr>
    """
    connection = sqlite3.connect(configs.get("db").data)
    cur = connection.cursor()
    for row in cur.execute("SELECT handle, capcode FROM pagers"):
        html += '<tr><td>%s</td><td style="text-align: center">%s</td></tr>' % (row[0], row[1])
    html += """
            </tbody>
        </table>
    """
    return createHtmlPage(html), 200

@app.route("/nodes")
def webNodes():
    html = """
        <h3>Node List</h3>
        <table>
            <tbody>
                <tr>
                    <th style="width: 200px; text-align: left">
                        Name
                    </th>
                    <th style="width: 115px;">
                        Locations
                    </th>
                    <th style="width: 115px;">
                        Frequencies
                    </th>
                    <th style="width: 70px;">
                        Status
                    </th>
                </tr>
    """
    connection = sqlite3.connect(configs.get("db").data)
    cur = connection.cursor()
    for row in cur.execute("SELECT name, location, frequencies, status FROM nodes"):
        html += '<tr><td style="text-align: left">%s</td><td style="text-align: center">%s</td><td style="text-align: center">%s</td><td style="text-align: center">%s</td></tr>' % (row[0], row[1], row[2], row[3])
    html += """
            </tbody>
        </table>
    """
    return createHtmlPage(html), 200

@app.route("/addnode", methods=['POST'])
def addNode():
    body = json.loads(request.data)
    if not re.match("^\w[a-zA-Z0-9.]*$", body["name"]):
        return "Node name can only be letters and number with no spaces.", 400
    connection = sqlite3.connect(configs.get("db").data)
    cur = connection.cursor()
    cur.execute("INSERT INTO nodes VALUES ('%s', '%s', '%s', '%s', 'online') ON CONFLICT DO UPDATE SET name='%s', address='%s', location='%s', frequencies='%s', status='online'" % (body["name"], body["address"], body["location"], body["frequencies"], body["name"], body["address"], body["location"], body["frequencies"]))
    connection.commit()
    print ("Added node with params of: '%s', '%s', '%s', '%s'" % (body["name"], body["address"], body["location"], body["frequencies"]))
    return "Node has been added.", 200

@app.route("/faddpager", methods=['POST'])
def faddpager():
    result = addPagerToDB(request.form.get("handle"), request.form.get("capcode"), request.form.get("frequency"), request.form.get("nodes"))
    return createHtmlPage('<p>%s</p><a href="/">return home</a>' % result), 200

@app.route("/addpager", methods=['POST'])
def addPager():
    body = json.loads(request.data)
    result = addPagerToDB(body["handle"], body["capcode"], body["frequency"], body["nodes"])
    return result, 200

@app.route("/fsendpage", methods=['POST'])
def fsendPage():
    result = sendPageToNode(request.form.get("key"), request.form.get("msg"))
    return createHtmlPage('<p>%s</p><a href="/">return home</a>' % result), 200

@app.route("/sendpage", methods=['POST'])
def sendPage():
    body = json.loads(request.data)
    result = sendPageToNode(body["key"], body["msg"])
    return result, 200

def sendPageToNode(key, msg):
    connection = sqlite3.connect(configs.get("db").data)
    cur = connection.cursor()
    if key.isnumeric():
        res = cur.execute("SELECT capcode, frequency, nodes FROM pagers WHERE capcode='%s'" % key)
    else:
        res = cur.execute("SELECT capcode, frequency, nodes FROM pagers WHERE handle='%s'" % key)
    pager = res.fetchall()
    if len(pager) > 1:
        return "More than one of the specified capcode exists, please use the handle instead."
    else:
        pager = pager[0]
    if pager:
        for node in pager[2].split(","):
            res = cur.execute("SELECT address FROM nodes WHERE name='%s'" % node.strip())
            nodeAddress = res.fetchone()
            if nodeAddress:
                nodeAddress = nodeAddress[0]
                try:
                    req = requests.post("%s/page" % nodeAddress, json = {"capcode": pager[0], "msg": msg, "frequency": pager[1]})
                    print ("Sent message to %s for %s with msg %s at freq %s" % (nodeAddress, pager[0], msg, pager[1]))
                    return req.text
                except requests.exceptions.RequestException:
                    print ("Node %s is not avalible." % node.strip())
                    return "Node %s is not avalible." % node.strip()
            else:
                return "Node %s does not exist." % node.strip()
    else:
        return "Pager does not exist."

def addPagerToDB(handle, capcode, frequency, nodes):
    connection = sqlite3.connect(configs.get("db").data)
    cur = connection.cursor()
    for node in nodes.split(","):
        res = cur.execute("SELECT frequencies FROM nodes WHERE name='%s'" % node.strip())
        nodeFreq = res.fetchone()
        if nodeFreq:
                nodeFreq = nodeFreq[0]
                if verifyFreqRange(frequency, nodeFreq):
                    cur.execute("INSERT INTO pagers VALUES ('%s', '%s', '%s', '%s') ON CONFLICT DO UPDATE SET handle='%s', capcode='%s', frequency='%s', nodes='%s'" % (handle, capcode, frequency, nodes, handle, capcode, frequency, nodes))
                    connection.commit()
                    print ("Added pager with params of: '%s', '%s', '%s', '%s'" % (handle, capcode, frequency, nodes))
                    return "Pager has been added."
                else:
                    return "Node %s does not support this pagers frequency, please resubmit pager with a different node." % node.strip()
        else:
            return "Node %s does not exist, please resubmit pager application with this node removed." % node.strip()
    
def verifyFreqRange(pagerFreq, nodeFreq):
  if nodeFreq != "any":
    if "-" in nodeFreq:
        for freq in nodeFreq.split(","):
            if float(pagerFreq) < float(freq.split("-")[0]) or float(pagerFreq) > float(freq.split("-")[1]):
                return False 
    else:
        return float(nodeFreq) == float(pagerFreq)
  return True

def checkNodeHealth():
    while True:
        print ("Checking nodes health.")
        connection = sqlite3.connect(configs.get("db").data)
        cur = connection.cursor()
        for row in cur.execute("SELECT name, address FROM nodes"):
            try:
                req = requests.get("%s/health" % row[1])
                if req.text != "alive":
                    raise requests.exceptions.RequestException("did not responed with alive")
                cur.execute("UPDATE nodes SET status='online' WHERE name='%s'" % row[0])
                connection.commit()
            except requests.exceptions.RequestException:
                print ("Node %s health check failed, marking it offline." % row[0])
                cur.execute("UPDATE nodes SET status='offline' WHERE name='%s'" % row[0])
                connection.commit()
        sleep(1800)
    return

def createHtmlPage(innerHtml):
    html = """
        <html>
            <head>
                <title>Pirate Pager</title>
                <link rel="icon" type="image/x-icon" href="/static/favicon.ico">
            </head>
            <body style="margin: 0 auto; width: 500; text-align: center; color: white; background-image: url('http://art.teleportacia.org/observation/vernacular/stars/starry.gif')">
                <img style="height: 200px; margin-top: 10px; margin-bottom: 10px" src="/static/logo.gif" />
                <div style="margin-bottom: 20px; background-color: cyan">
                    <a href="/" style="margin: 10px">Send Page</a>
                    <a href="/add" style="margin: 10px">Add Pager</a>
                    <a href="/pagers" style="margin: 10px">Pager List</a>
                    <a href="/nodes" style="margin: 10px">Node List</a>
                </div>
    """
    html += innerHtml
    html += """
            <div style="width: 30%; display: block; margin-left: auto; margin-right: auto; margin-top: 20px">
                <img src="/static/pika.gif" />
            </div>
            <p>Created by Zach Lambert 2023</p>
        </body>
    </html>
    """
    return html

createDB()
print("Server is now running on port: %s" % configs.get("port").data)
thread = Thread(target = checkNodeHealth)
thread.start()