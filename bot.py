import flask, pymongo, json
from flask import request, Flask
import signal, sys, time, datetime

db = None
mongoconn = None

cfg = None

originaltime = time.time()

#signal handling for shutdown on SIGINT

def signal_handler(signal, frame):
	#cleanup mongo connection n interrupt
	mongoconn.disconnect();
	sys.exit()

app = flask.Flask(__name__)


@app.route('/bot', methods=['POST'])
def onCall():
	if ( all([ (i in request.form.keys()) for i in cfg["required_tokens"] ]) ):
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
			
	old_msg = datetime.datetime.fromtimestamp(
					float(timestamp)
				).strftime('%Y-%m-%d %H:%M:%S')
	initial_time = datetime.datetime.fromtimestamp(
					float(originaltime)
				).strftime('%Y-%m-%d %H:%M:%S')

	n = rs(
		"Stats for %s:\\n"%(form["channel_name"]) +
		"messages logged: %s\\n"%(db[form["channel_id"]].find().count()) +
		"oldest msg: %s\\n"%( old_msg ) +
		"last restart: %s\\n"%( initial_time ) )

commands = {
	u'stats': statsparser,
	u'fuck': lambda a, b: rs(u'(\uFF61 \u2256 \u0E34 \u203F \u2256 \u0E34)')
}


#loading cfg and launch

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







#loading

def loadcfg(fname, fallback=True):
	try:
		f = open(fname)
		config = json.loads(f.read())
		f.close()
		return config
	except Exception as e:
		print e

		if(fallback):
			print "error loading config from %s, reverting to defaults"%(fname)
			return {
				"mongoport": 27017,
				"mongoaddr": "localhost",
				"hostport" : 65152
			}
		else:
			return None

if __name__ == "__main__":
	#load config
	if len(sys.argv) > 1:
		cfg = loadcfg(sys.argv[1],False)
		if not cfg:
			cfg = loadcfg("./config.json")
	else:
		cfg = loadcfg("./config.json")

	try:
		mongoconn = pymongo.MongoClient(cfg["mongoaddr"], cfg["mongoport"])
		db = mongoconn.slacklogbot
		signal.signal(signal.SIGINT, signal_handler)

		app.run(host='0.0.0.0', port=cfg["hostport"], debug=True)
	except pymongo.errors.ConnectionFailure:
		print "error connecting to mongodb database"
