from flask import redirect, flash, url_for, request
from flask_security import current_user
from functools import wraps
from datetime import datetime


def strfdelta(time, fmt):
    if not hasattr(time, "days"):  # dirty hack
        now = datetime.now()
        if isinstance(time, str):
            time = datetime.strptime(time, '%Y-%m-%dT%H:%M:%S')
        time = abs(now - time)

    d = {"days": time.days}
    d["hours"], rem = divmod(time.seconds, 3600)
    d["minutes"], d["seconds"] = divmod(rem, 60)
    return fmt.format(**d)


def unlocked_wallet_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        from .node import Node
        if not Node().wallet_exists():
            flash(
                "No wallet has been created yet. You need to do that and "
                "import your witness active key"
            )
            return redirect(url_for('newwallet', next=request.url))
        if Node().locked():
            flash(
                "In order to access this functionality, you need "
                "to unlock your wallet first!"
            )
            return redirect(url_for('unlock', next=request.url))
        return f(*args, **kwargs)
    return decorated_function
