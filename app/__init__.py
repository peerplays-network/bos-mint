import yaml
import os
from flask import Flask, jsonify, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
import logging
from logging.handlers import TimedRotatingFileHandler
from werkzeug.exceptions import HTTPException, InternalServerError
import pprint

from peerplays.instance import set_shared_config


def get_config():
    basedir = os.path.abspath(os.path.dirname(__file__))

    # Instanciate config
    if os.path.isfile("config.yml"):
        config = yaml.load(open("config.yml").read())
    else:
        raise NotImplementedError()  # define defaults here once config.yml structure is fixed

    config["sql_database"] = config["sql_database"].format(cwd=basedir)

    return config


def set_global_logger():
    # setup logging
    log_folder = os.path.join("dump", "logs")
    log_format = ('%(asctime)s %(levelname) -10s: %(message)s')
    os.makedirs(log_folder, exist_ok=True)
    trfh = TimedRotatingFileHandler(
        os.path.join(log_folder, "manual_intervention.log"),
        "midnight",
        1
    )
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

    return [trfh, sh]


def set_flask_logger(flask_app, handlers):
    # set app.logger from flask
    while len(app.logger.handlers) > 0:
        app.logger.removeHandler(app.logger.handlers[0])

    for handler in log_handlers:
        app.logger.addHandler(handler)


def set_app_config(flask_app, config):
    basedir = os.path.abspath(os.path.dirname(__file__))

    # Flask Settings
    flask_app.config['DEBUG'] = config["debug"]
    flask_app.config['SECRET_KEY'] = config["secret_key"]

    # Let's store the whole config struct
    flask_app.config['PROJECT'] = config

    # Config database
    flask_app.config['SQLALCHEMY_DATABASE_URI'] = config["sql_database"].format(cwd=basedir)
    flask_app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    flask_app.config['SQLALCHEMY_ECHO'] = config["debug"]

    # disable CSRF protection for now, fix and remove
    flask_app.config['WTF_CSRF_ENABLED'] = False


def set_peerplays_connection(config):
    use = config["connection"]["use"]
    set_shared_config(config["connection"][use])


def set_error_handling(flask_app):
    def handle_exception(e):
        if isinstance(e, HTTPException):
            raise e

        flask_app.logger.exception(e)
        flash(e.__class__.__name__ + ": " + str(e), category='error')
        return redirect(url_for('overview'))

    flask_app.errorhandler(Exception)(handle_exception)
    # In the case of an internal error after the user function
    # (e.g. a view does not return any value)
    # flask is looking for a specifically set InternalServerError handler,
    # see flask/app.py:handle_exception:1532
    flask_app.errorhandler(InternalServerError)(handle_exception)


config = get_config()

log_handlers = set_global_logger()

# Instanciate flask
app = Flask(__name__)

set_flask_logger(app, log_handlers)
set_app_config(app, config)
set_error_handling(app)
db = SQLAlchemy(app)
set_peerplays_connection(config)

app.logger.info(pprint.pformat(config))


@app.before_first_request
def before_first_request():
    try:
        db.create_all()
    except Exception as e:
        app.logger.warning(str(e))


@app.teardown_appcontext
def shutdown_session(exception=None):
    db.session.remove()
