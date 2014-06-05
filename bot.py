import flask, pymongo
from flask import request, Flask
import signal, sys, time, datetime

mongoport = 27017
mongoaddr = "localhost"
mongoconn = None
db = None

originaltime = time.time()

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

@app.route('/bot', methods=['POST'])
def onCall():
    if ( all([ (i in request.form.keys()) for i in apitokens]) ):
        print "msg recieved"        
        #because request.form.keys can't be cast to dict. FLASKU Y?
        d = dict( [(key, request.form[key]) for key in request.form.keys()] )
        db[str(request.form["channel_id"])].insert(d)
        if request.form["text"].startswith("logbot"):
            print "pushing msg to logbot"
            return parsecommand(request.form)
    else:
        print "msg rejected"
    return ""


def statsparser(form, spl):
    timestamp = db[form["channel_id"]].find().sort(
                [("timestamp", 1)] ).limit(1).next()["timestamp"] 
            
    old_msg = datetime.datetime.fromtimestamp(int(timestamp)).strftime('%Y-%m-%d %H:%M:%S')
    initial_time = datetime.datetime.fromtimestamp(int(originaltime)).strftime('%Y-%m-%d %H:%M:%S')

    n = rs(
        "Stats for %s:\\n"%(form["channel_name"]) +
        "messages logged: %s\\n"%(db[form["channel_id"]].find().count()) +
        "oldest msg: %s\\n"%( old_msg ) +
        "last restart: %s\\n"%( initial_time ) )
    print n
    return n

commands = {
    u'stats': statsparser,
    u'fuck': lambda a, b: rs(u'(\uFF61 \u2256 \u0E34 \u203F \u2256 \u0E34)')
}

def parsecommand(form):
    spl = form["text"].split(" ")
    print spl
    if (len(spl)>1):
        if(spl[1] == u'help'):
                return rs(
                    "Commands:\\n"+
                    reduce(
                        lambda a, b: a+u'\\n'+b, 
                        [ "\u2022    "+key for key in commands]
                    )
                )
        elif (spl[1] in commands.keys()):
            return commands[spl[1]](form, spl)
        else:
            return  rs("I don't know that command")
    else:
        return rs("what?")

def rs(string):
    print 
    return "{\"text\": \"%s\"}"%(string)

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=hostport, debug=True)
