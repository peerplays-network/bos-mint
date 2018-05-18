import os
import yaml
import pprint
import logging
import pkg_resources

from flask import Flask, jsonify, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from logging.handlers import TimedRotatingFileHandler
from werkzeug.exceptions import HTTPException, InternalServerError
from peerplays.instance import set_shared_config
import collections
from copy import deepcopy
import io


def get_version():
    try:
        with open(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'VERSION')) as version_file:
            return version_file.read().strip()
    except FileNotFoundError:
        with open(os.path.join(os.path.dirname(os.path.realpath(__file__)), "..", 'VERSION')) as version_file:
            return version_file.read().strip()


__VERSION__ = get_version()


class Config():
    """ This class allows us to load the configuration from a YAML encoded
        configuration file.
    """

    ERRORS = {
        "secret_key": "Please create a configuration file config-bos-mint.yml in your working directory with a secret_key entry, see config-example.yaml",
        "connection.use": "Please create a configuration file config-bos-mint.yml in your working directory with a connection.use entry, see config-example.yaml"
    }

    data = None
    source = None

    @staticmethod
    def load(config_files=[], relative_location=False):
        """ Load config from a file

            :param str file_name: (defaults to ['config.yaml']) File name and
                path to load config from
        """

        if not Config.data:
            Config.data = {}

        if not config_files:
            # load all config files as default
            config_files.append("config-defaults.yaml")
        if type(config_files) == str:
            config_files = [config_files]

            for config_file in config_files:
                if relative_location:
                    file_path = config_file
                else:
                    file_path = os.path.join(
                        os.path.dirname(os.path.realpath(__file__)),
                        config_file
                    )
                stream = io.open(file_path, 'r', encoding='utf-8')
                with stream:
                    Config.data = Config._nested_update(Config.data, yaml.load(stream))

            if not Config.source:
                Config.source = ""
            Config.source = Config.source + ";" + ";".join(config_files)

    @staticmethod
    def get_config(config_name=None):
        """ Static method that returns the configuration as dictionary.
            Usage:

            .. code-block:: python

                Config.get_config()
        """
        if not config_name:
            if not Config.data:
                raise Exception("Either preload the configuration or specify config_name!")
        else:
            if not Config.data:
                Config.data = {}
            Config.load(config_name)
        return deepcopy(Config.data)

    @staticmethod
    def get(*args, **kwargs):
        """
        This config getter method allows sophisticated and encapsulated access to the config file, while
        being able to define defaults in-code where necessary.

        :param args: key to retrieve from config, nested in order. if the last is not a string it is assumed to be the default, but giving default keyword is then forbidden
        :type tuple of strings, last can be object
        :param message: message to be displayed when not found, defaults to entry in ERRORS dict with the
                                key defined by the desired config keys in args (key1.key2.key2). For example
                                Config.get("foo", "bar") will attempt to retrieve config["foo"]["bar"], and if
                                not found raise an exception with ERRORS["foo.bar"] message
        :type message: string
        :param default: default value if not found in config
        :type default: object
        """
        default_given = "default" in kwargs
        default = kwargs.pop("default", None)
        message = kwargs.pop("message", None)
        # check if last in args is default value
        if type(args[len(args) - 1]) != str:
            if default_given:
                raise KeyError("There can only be one default set. Either use default=value or add non-string values as last positioned argument!")
            default = args[len(args) - 1]
            args = args[0:len(args) - 1]

        try:
            nested = Config.data
            for key in args:
                if type(key) == str:
                    nested = nested[key]
                else:
                    raise KeyError("The given key " + str(key) + " is not valid.")
            if nested is None:
                raise KeyError()
        except KeyError:
            lookup_key = '.'.join(str(i) for i in args)
            if not message:
                if Config.ERRORS.get(lookup_key):
                    message = Config.ERRORS[lookup_key]
                else:
                    message = "Configuration key {0} not found in {1}!"
                message = message.format(lookup_key, Config.source)
            if default_given:
                logging.getLogger(__name__).debug(message + " Using given default value.")
                return default
            else:
                raise KeyError(message)

        return nested

    @staticmethod
    def reset():
        """ Static method to reset the configuration storage
        """
        Config.data = None
        Config.source = None

    @staticmethod
    def _nested_update(d, u):
        for k, v in u.items():
            if isinstance(v, collections.Mapping):
                d[k] = Config._nested_update(d.get(k, {}), v)
            else:
                if d:
                    d[k] = v
                else:
                    d = {}
                    d[k] = v
        return d


if not Config.data:
    Config.load("config-defaults.yaml")
    notify = False
    try:
        # overwrites defaults
        Config.load("config-bos-mint.yaml", True)
        notify = True
    except FileNotFoundError:
        pass

    if notify:
        logging.getLogger(__name__).info("Custom config has been loaded " + Config.source)


def get_config():
    Config.load("config-defaults.yaml")
    notify = False
    try:
        # overwrites defaults
        Config.load("config-bos-mint.yaml", True)
        notify = True
    except FileNotFoundError:
        pass

    if notify:
        logging.getLogger(__name__).info("bos-mint: Custom config has been loaded " + Config.source)

    Config.get("connection", "use")
    Config.get("secret_key")

    config = Config.data

    config["sql_database"] = config["sql_database"].format(cwd=os.getcwd())

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
    trfh.setFormatter(logging.Formatter(log_format))

    sh = logging.StreamHandler()
    sh.setFormatter(logging.Formatter(log_format))

    # set global logger (e.g. for werkzeug)
    if Config.get("debug"):
        trfh.setLevel(logging.DEBUG)
        sh.setLevel(logging.DEBUG)
        logging.basicConfig(level=logging.DEBUG,
                            format=log_format,
                            handlers=[trfh, sh])
    else:
        trfh.setLevel(logging.INFO)
        sh.setLevel(logging.INFO)
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
    connection_config = config["connection"][use]

    # avoid connectivity loops
    if connection_config.get("num_retries", None) is None:
        connection_config["num_retries"] = 3

    set_shared_config(connection_config)


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


app.logger.debug(pprint.pformat(config))


@app.before_first_request
def before_first_request():
    try:
        db.create_all()
    except Exception as e:
        app.logger.warning(str(e))


@app.teardown_appcontext
def shutdown_session(exception=None):
    db.session.remove()
