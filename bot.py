import flask, pymongo
from flask import request, Flask
import signal, sys

mongoport = 27017
mongoaddr = "localhost"
mongoconn = None
db = None

hostport = 65152

def signal_handler(signal, frame):
    #cleanup mongo connection n interrupt
    mongoconn.disconnect();
    sys.exit()

app = flask.Flask(__name__)
apitokens = ["token", "team_id", "channel_id", "channel_name", "timestamp",
        "user_id", "user_name", "text"]

if __name__ == "__main__":
    if len(sys.argv) > 1:
        hostport = int(sys.argv[1])
    mongoconn = pymongo.MongoClient(mongoaddr, mongoport)
    db = mongoconn.slacklogbot
    signal.signal(signal.SIGINT, signal_handler)

app.config["SERVER_NAME"] = "is-limbics.com:"+str(hostport)

@app.route('/bot', methods=['POST'])
def onCall():
    print "msg recieved"
    if ( all([ (i in request.form.keys()) for i in apitokens]) ):
        if request.form["text"].startswith("logbot"):
            return parsecommand(request.form)
        
        #because request.form.keys can't be cast to dict. FLASKU Y?
        d = dict( [(key, request.form[key]) for key in request.form.keys()] )
        db[str(request.form["channel_id"])].insert(d)
    return ""


def parsecommand(form):
    spl = form["text"].split(" ")

    if(spl[1] == "help"):
            return ms(
                slacklogbot
                )
    elif(spl[1] == "stats"):
        return ms(
            "Stats for %s:\\n"%(form["channel_name"]) +
            "messages logged: %s\\n"%(db[form["channel_id"]].find().count()) +
            "started at: %s\\n"%(db[form["channel_id"]].find().min().timestamp)
            )
    else:
        return rs("what?")

def rs(string):
    return "{\"text\": \"%s\"}"%(string)

if __name__ == "__main__":
    app.run(host='0.0.0.0')
