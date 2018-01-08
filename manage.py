#!/usr/bin/env python3

import sys
from flask_script import Manager, Command
# from flask_migrate import Migrate, MigrateCommand
from app import db, config
from app.web import app
import threading
from app.maillog import logmodule

manager = Manager(app)
log = logmodule(__name__)
# migrate = Migrate(app, db)
# manager.add_command('db', MigrateCommand)


@manager.command
def web(port=5001, host="127.0.0.1"):
    app.run(debug=True, port=int(port), host=host)


@manager.command
def sql():
    from subprocess import Popen
    parts = config["sql_database"].split("/")
    database = parts[-1].strip()
    user = parts[2].split(":")[0].strip()
    password = parts[2].split(":")[1].split("@")[0].strip()
    host = parts[2].split("@")[1].strip()
    args = [
        "mysql",
        "-h", host,
        "-u", user,
        "--password={}".format(password),
        "-D", database
    ]
    Popen(args).wait()


if __name__ == '__main__':
    manager.run()
