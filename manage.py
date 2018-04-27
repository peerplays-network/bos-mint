#!/usr/bin/env python3
from flask_script import Manager
from bos_mint import db, config
from bos_mint.web import app

manager = Manager(app)


@manager.command
def web(port=5000, host="127.0.0.1"):
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
