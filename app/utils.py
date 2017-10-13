from flask import redirect, flash, url_for, request, render_template
from flask_security import current_user
from functools import wraps
from datetime import datetime
from app.node import Node
from tkinter.constants import CURRENT


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
        
        walletInfo = "abc"
        return f(*args, **kwargs)
    return decorated_function

def render_template_menuinfo(tmpl_name, **kwargs):
    menuInfo = getMenuInfo()
    return render_template( tmpl_name, menuInfo=menuInfo, **kwargs)

def getMenuInfo():
    account = Node().getActiveAccount();
    
    currentTransaction = Node().getActiveTransaction()
    if not currentTransaction:
        operations = []
    else:
        operations = Node().getActiveTransaction().ops
     
        
    menuInfo = { 
            'accountName': account.identifier + " - " + account.name,
            'numberOfOpenTransactions': len(operations)
                }
    return menuInfo

class Singleton:
    """
    A non-thread-safe helper class to ease implementing singletons.
    This should be used as a decorator -- not a metaclass -- to the
    class that should be a singleton.

    The decorated class can define one `__init__` function that
    takes only the `self` argument. Also, the decorated class cannot be
    inherited from. Other than that, there are no restrictions that apply
    to the decorated class.

    To get the singleton instance, use the `Instance` method. Trying
    to use `__call__` will result in a `TypeError` being raised.

    """

    def __init__(self, decorated):
        self._decorated = decorated

    def Instance(self):
        """
        Returns the singleton instance. Upon its first call, it creates a
        new instance of the decorated class and calls its `__init__` method.
        On all subsequent calls, the already created instance is returned.

        """
        try:
            return self._instance
        except AttributeError:
            self._instance = self._decorated()
            return self._instance

    def __call__(self):
        raise TypeError('Singletons must be accessed through `Instance()`.')

    def __instancecheck__(self, inst):
        return isinstance(inst, self._decorated)
    