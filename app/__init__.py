import yaml
import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail
import logging
from logging.handlers import TimedRotatingFileHandler
import pprint

basedir = os.path.abspath(os.path.dirname(__file__))

# Instanciate config
if os.path.isfile("config.yml"):
    config = yaml.load(open("config.yml").read())
else:
    config = {
        "debug": True,
        "nobroadcast": False,
        "witness_url": os.environ.get(
            "WITNESS_URL",
            "wss://peerplays-dev.blocktrades.info/ws"
        ),
        "mail_host": os.environ.get("MAIL_HOST"),
        "mail_port": os.environ.get("MAIL_PORT", 25),
        "mail_user": os.environ.get("MAIL_USER"),
        "mail_pass": os.environ.get("MAIL_PASS"),
        "mail_from": os.environ.get("MAIL_FROM", "boss@localhost"),
        "mail_notify": os.environ.get("MAIL_NOTIFY"),
        "project_name": os.environ.get("PROJECT_NAME", "PeerPlays-Boss"),
        "secret_key": os.environ.get("SECRET_KEY", "RUR7LywKvncb4eoR"),
        "sql_database": os.environ.get("SQL_DATABASE", "sqlite:///{cwd}/database.db".format(cwd=basedir))
    }

# setup logging
log_folder = os.path.join("dump", "logs")
log_format = ('%(asctime)s %(levelname) -10s: %(message)s')
os.makedirs(log_folder, exist_ok=True)
trfh = TimedRotatingFileHandler(
            os.path.join(log_folder, "manual_intervention.log"),
            "midnight",
            1)
trfh.suffix = "%Y-%m-%d"
trfh.setLevel(logging.INFO)
trfh.setFormatter(logging.Formatter(log_format))

sh = logging.StreamHandler()
sh.setLevel(logging.INFO)
sh.setFormatter(logging.Formatter(log_format))

# set global logger (e.g. for werkzeug)
logging.basicConfig(level=logging.INFO,
                    format=log_format,
                    handlers=[trfh, sh])

# Instanciate flask
app = Flask(__name__)

# set app.logger from flask
while len(app.logger.handlers) > 0:
    app.logger.removeHandler(app.logger.handlers[0])

app.logger.addHandler(trfh)
app.logger.addHandler(sh)

app.logger.info(pprint.pformat(config))

# Flask Settings
app.config['DEBUG'] = config["debug"]
app.config['SECRET_KEY'] = config["secret_key"]

# Let's store the whole config struct
app.config['PROJECT'] = config

# # Config Mail
# app.config['MAIL_SERVER'] = config["mail_host"]
# app.config['MAIL_PORT'] = config["mail_port"]
# app.config['MAIL_USERNAME'] = config["mail_user"]
# app.config['MAIL_PASSWORD'] = config["mail_pass"]
# app.config['MAIL_DEFAULT_SENDER'] = config["mail_from"]
# app.config['MAIL_USE_TLS'] = True
# app.config['MAIL_USE_SSL'] = False
# mail = Mail(app)

# Config database
app.config['SQLALCHEMY_DATABASE_URI'] = config["sql_database"].format(cwd=basedir)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ECHO'] = config["debug"]
db = SQLAlchemy(app)

# disable CSRF protection for now, fix and remove
app.config['WTF_CSRF_ENABLED'] = False

from app import models, utils


@app.before_first_request
def before_first_request():
    try:
        db.create_all()
    except Exception as e:
        app.logger.warning(str(e))


@app.teardown_appcontext
def shutdown_session(exception=None):
    db.session.remove()
