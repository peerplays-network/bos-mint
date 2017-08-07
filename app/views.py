from flask import render_template, redirect, request, session, flash, url_for, make_response, abort
from datetime import datetime
from . import app, db, forms, config
from .utils import unlocked_wallet_required


###############################################################################
# Homepage
###############################################################################
@app.route('/')
@unlocked_wallet_required
def index():
    return render_template('index.html')


@app.route('/unlock', methods=['GET', 'POST'])
def unlock():
    unlockForm = forms.UnlockForm()

    if unlockForm.validate_on_submit():
        return redirect(request.args.get("next", url_for("index")))

    return render_template('unlock.html', **locals())


@app.route('/demo')
@unlocked_wallet_required
def demo():
    return "foobar"


@app.route("/wallet/new")
def newwallet():
    return "foobar"


@app.route("/sport/new")
def sport_new():
    sportForm = forms.SportForm()
    return render_template("sport.html", **locals())
