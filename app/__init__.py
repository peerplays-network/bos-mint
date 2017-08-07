import yaml
import sys
import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail

# Instanciate config
config = yaml.load(open("config.yml").read())

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
app.config['SQLALCHEMY_DATABASE_URI'] = config["sql_database"]
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ECHO'] = config["debug"]
db = SQLAlchemy(app)

# Assets
app.config['ASSETS_DEBUG'] = config["debug"]


@app.before_first_request
def before_first_request():
    try:
        db.create_all()
    except Exception as e:
        app.logger.warning(str(e))


@app.teardown_appcontext
def shutdown_session(exception=None):
    db.session.remove()
