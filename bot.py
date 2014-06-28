import flask, pymongo, json
from flask import request, Flask, render_template
from bson.objectid import ObjectId
import signal, sys, time, datetime

db = None
mongoconn = None
cfg = None

originaltime = time.time()
app = flask.Flask(__name__)



#################################
#             Pages             #
#################################

@app.route('/bot', methods=['POST','GET'])
def onCall():
	if ( all([ (i in request.form.keys()) for i in cfg["required_tokens"] ]) ):
		print "msg recieved"
		#because request.form.keys can't be cast to dict. FLASKU Y?
		d = dict( [(key, 
			(int(request.form[key])
				if request.form[key].isdigit() else
					request.form[key]) 
			) for key in request.form.keys()] )
		db[str(request.form["channel_id"])].insert(d)
		save_channel_alias(
			request.form["channel_name"],
			request.form["channel_id"])

		if request.form["text"].startswith("logbot"):
			print "pushing msg to logbot"
			return parsecommand(request.form)
	else:
		print "msg rejected - tokens"
		return rs("msg rejected: did not have required parameters (%s)}"%(
			", ".join([ i for i in cfg["required_tokens"] if i not in request.form.keys() ])
		))
	return ""

@app.route('/log/<channel>')
def serveLog(channel):

	channel_id = (get_channel_alias(channel) if (channel not in db.collection_names()) else channel)
	if channel_id is None:
		return render_template("error.html", msg="no channel '%s'"%(channel) )
	elif not channel_id:
		channel_id = channel

	log_json = json.dumps(makeSerializable(dict(logBackend(channel_id))))

	return render_template("log.html",
		channel_id=channel_id,
		channel_name=channel,
		content=log_json)

@app.route('/log/backend/<channel_name>/<timestamp>/<number>')
@app.route('/log/backend/<channel_name>/<timestamp>')
@app.route('/log/backend/<channel_name>/')
def serveLogBackend(channel_name, timestamp="0", number="10", direction=False):
	ts, n = (0, 10)
	try:
		ts = float(timestamp)
		n = int(number)
	except ValueError:
		return "!that's not a number, dummy!"

	d =	logBackend(
				get_channel_alias(channel_name),
				ts, not bool(direction), n
			)

	if isinstance(d, str):
		return d
	else:
		return json.dumps(makeSerializable(dict(d)))


def logBackend(channel_id, timestamp=0.0, backwards=True, number=10):
	posts=[]

	recent_n = db[channel_id].find(
		({"timestamp":{"$lt": timestamp}} if timestamp !=0.0 else {})
		).sort([("timestamp",-1)]).limit(number)

	if timestamp == 0.0:
		timestamp = recent_n[recent_n.count()-1]["timestamp"]

	posts = list(recent_n)
	
	if len(posts) == 0:
		return "!no posts timestamp < %s, limit %s, (%s, %sP)"%(
					timestamp, number,
					timestamp.__class__.__name__,
					number.__class__.__name__
				)

	old = min(posts, key=lambda a: a["timestamp"])
	new = max(posts, key=lambda a: a["timestamp"])

	return {"data" : posts, 
			"oldest" : { 
					"timestamp" : old["timestamp"], 
					"_id" : old["_id"], 
				},
			"newest" : { 
					"timestamp" : new["timestamp"], 
					"_id" : new["_id"], 
				}
			} 

@app.route('/error')
def serveError():
	return render_template("error.html",msg="nothing went wrong")

#################################
#          logbot cmds          #
#################################

def statsparser(form, spl):
	timestamp = db[form["channel_id"]].find().sort(
				[("timestamp", 1)] ).limit(1).next()["timestamp"] 
			
	old_msg = datetime.datetime.fromtimestamp(
					float(timestamp)
				).strftime('%Y-%m-%d %H:%M:%S')
	initial_time = datetime.datetime.fromtimestamp(
					float(originaltime)
				).strftime('%Y-%m-%d %H:%M:%S')

	link_to_log = "http://%s:%s/log/%s"%(cfg["hostname"], cfg["hostport"], form["channel_id"])

	return rs(
		("Stats for %s:\\n"+
		"messages logged: %s\\n" +
		"oldest msg: %s\\n" +
		"last restart: %s\\n"+
		"see full log at %s")%(
			form["channel_name"],
			db[form["channel_id"]].find().count(),
			old_msg,
			initial_time,
			link_to_log ))

def listnotes(form, spl):
	db[form["channel_id"]+"_notes"].find("live")

def recordnote(form, spl):
	db[form["channel_id"]+"_notes"].insert({
		"text": " ".join(spl[1:]),
		"time": form["timestamp"],
		"live": 1 
		})

def removenote(form, spl):
	pass

def reloadcfg(form, spl):
	global cfg
	filename = "./config.json" if len(spl)<=2 else spl[2]
	d = loadcfg(filename, False)
	if d is not None:
		cfg = d
		return rs("loaded config %s"%(filename))
	else:
		return rs("failed to load config %s"%(filename))




commands = {
	u'stats': statsparser,
	u'fuck': lambda a, b: rs(u'(\uFF61 \u2256 \u0E34 \u203F \u2256 \u0E34)'),
#	u'notes': listnotes,
#	u'note': recordnote,
#	u'removenote': removenote.
	u'reload': reloadcfg
}

#################################
#            parseing           #
#################################

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



#################################
#        helper methods         #
#################################

#saving aliases for channel ids
def save_channel_alias(alias, channel_id):
	#check if it exists in the database
	if ("aliases" in db.collection_names() and 
			db.aliases.find({"alias":alias}).count() > 0 ):
		return False
	else:
		db.aliases.insert({"alias":alias, "id": channel_id})

#serving aliases for channel ids
def get_channel_alias(alias):
	if alias in db.collection_names():
		return alias
	elif not "aliases" in db.collection_names():
		return False
	else:
		x = db.aliases.find_one({"alias":alias});
		if x:
			return (x["id"])
		else:
			return None

def makeSerializable(jayson):
	for i in jayson if isinstance(jayson, dict) else range(len(jayson)):
		if isinstance(jayson[i], dict) or isinstance(jayson[i], list):
			jayson[i] = makeSerializable(jayson[i])
		elif isinstance(jayson[i], ObjectId):
			jayson[i] = str(jayson[i])
	return jayson


def udict_to_ascii(jayson):
	return dict([
		(
			(d, udict_to_ascii(jayson[d]))
				if (isinstance(jayson[d], dict) or isinstance(jayson[d], list)) else
			(
				( unicode_or_not(d), unicode_or_not(jayson[d]))
			)
		)
		for d in (
				jayson if isinstance(jayson, dict)
				else range(len(jayson))
			)
	])

def unicode_or_not(c):
	return c.encode("ascii","xmlcharrefreplace") if isinstance(c,unicode) else c

def password_auth():
	pass


#################################
#    loading cfg and launch     #
#################################

#signal handling for shutdown on SIGINT
def signal_handler(signal, frame):
	#cleanup mongo connection n interrupt
	mongoconn.disconnect();
	sys.exit()


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
