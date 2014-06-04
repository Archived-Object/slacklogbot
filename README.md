bot to log chat messages sent to it by slackbot.

configure by enabling an api hook and poining it to the server this is running
on, on the specified port (8000 by default)

need gunicorn to run.
use gunicorn bot:app to deploy
