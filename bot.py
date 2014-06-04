import flask, pymongo
from flask import request
import signal, sys

mongoport = 27017
mongoaddr = "localhost"
mongoconn = None

hostport = 8000

app = flask.Flask(__name__)
apitokens = ["token", "team_id", "channel_id", "channel_name", "timestamp",
        "user_id", "user_name", "text"]

@app.route('/', methods=['POST'])
def onCall():
    print "msg recieved"
    if ( all([ (i in request.form.keys()) for i in apitokens]) ):
        #because request.form.keys can't be cast to dict. FLASKU Y?
        d = dict( [(key, request.form[key]) for key in request.form.keys()] )
        mongoconn.slacklogbot[str(request.form["channel_id"])].insert(d)
        return "{text:\"logging confirmed\"}\n"
    return "i dun get my props..\n"

def signal_handler(signal, frame):
    #cleanup mongo connection n interrupt
    mongoconn.disconnect();
    sys.exit()

if __name__ == "__main__":
    print "bootup"

    if(len(sys.argv) > 1):
        hostport = int(sys.argv[1])

    app.config["SERVER_NAME"] = "127.0.0.1:"+str(hostport)


    mongoconn = pymongo.MongoClient(mongoaddr, mongoport)
    signal.signal(signal.SIGINT, signal_handler)

    app.run(debug=True)
