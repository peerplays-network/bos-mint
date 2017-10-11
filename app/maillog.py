import sys
import logging
from logging.handlers import SMTPHandler, RotatingFileHandler
from . import app, config


def logmodule(module):
    # log = app.logger
    thislog = logging.getLogger(module)
    thislog.addHandler(log_handler_mail)
    thislog.addHandler(log_handler_rotate)
    thislog.addHandler(log_handler_stdout)
    thislog.setLevel(logging.INFO)
    return thislog


log_handler_mail = SMTPHandler(config["mail_host"].split(":"),
                               config["mail_from"],
                               config["admins"],
                               '[%s] Error' % config["project_name"],
                               (config["mail_user"],
                                config["mail_pass"]))
log_handler_mail.setFormatter(logging.Formatter(
    "Message type:       %(levelname)s\n" +
    "Location:           %(pathname)s:%(lineno)d\n" +
    "Module:             %(module)s\n" +
    "Function:           %(funcName)s\n" +
    "Time:               %(asctime)s\n" +
    "\n" +
    "Message:\n" +
    "\n" +
    "%(message)s\n"
))
log_handler_mail.setLevel(logging.WARNING)

###############################################################################
# stdout
###############################################################################
log_handler_stdout = logging.StreamHandler(sys.stdout)
log_handler_stdout.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
log_handler_stdout.setLevel(logging.INFO)

###############################################################################
# logfile rotate
###############################################################################
log_handler_rotate = RotatingFileHandler('%s.log' % config["project_name"],
                                         maxBytes=1024 * 1024 * 100,
                                         backupCount=20)
log_handler_rotate.setLevel(logging.INFO)

###############################################################################
# Even log this module here
###############################################################################
log = logmodule(__name__)