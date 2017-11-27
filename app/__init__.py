import yaml
import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail
from pprint import pprint

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
        "sql_database": os.environ.get("SQL_DATABASE", "{{cwd}}/database.sqlite")
    }
pprint(config)

# Instanciate flask
app = Flask(__name__)

# Flask Settings
app.config['DEBUG'] = config["debug"]
app.config['SECRET_KEY'] = config["secret_key"]

# Let's store the whole config struct
app.config['PROJECT'] = config

# Config Mail
app.config['MAIL_SERVER'] = config["mail_host"]
app.config['MAIL_PORT'] = config["mail_port"]
app.config['MAIL_USERNAME'] = config["mail_user"]
app.config['MAIL_PASSWORD'] = config["mail_pass"]
app.config['MAIL_DEFAULT_SENDER'] = config["mail_from"]
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USE_SSL'] = False
mail = Mail(app)

# Config database
basedir = os.path.abspath(os.path.dirname(__file__))

app.config['SQLALCHEMY_DATABASE_URI'] = config["sql_database"].format(cwd=basedir)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ECHO'] = config["debug"]
db = SQLAlchemy(app)

# Assets
app.config['ASSETS_DEBUG'] = config["debug"]

# disable CSRF protection for now, fix and remove
app.config['WTF_CSRF_ENABLED'] = False

from app import models


@app.before_first_request
def before_first_request():
    try:
        db.create_all()
    except Exception as e:
        app.logger.warning(str(e))


@app.teardown_appcontext
def shutdown_session(exception=None):
    db.session.remove()
