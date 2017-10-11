from flask import render_template, redirect, request, session, flash, url_for, make_response, abort
from datetime import datetime
from . import app, db, forms, config
from .utils import unlocked_wallet_required

from collections import namedtuple
from app.forms import InternationalizedString
from app.node import Node, NodeException

# InternationalizedString = namedtuple('InternationalizedString', ['country', 'text'])
# Sport = namedtuple('Sport', ['names', 'submit'])
    

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


@app.route("/sport/new", methods=['post','get'])
def sport_new():
    sportForm = forms.SportForm()
    if sportForm.validate_on_submit():
        # Create new sport
        flash("a")
    else:
        # Show empty SportForm
        return render_template("sport.html", **locals())
    
@app.route("/sport/update/<sportId>", methods=['post','get'])
def sport_update(sportId):
    sportForm = forms.SportForm()
    # sport has already been loaded and user submitted
    
    # Which button was pressed?
    if sportForm.submit.data and sportForm.validate_on_submit():
        # all data was entered correctly, validate and update sport
        flash("A proposal for Sport " + sportId + " was succesfully created. (NW)")
        return redirect(url_for('index'))
    
    elif sportForm.addLanguage.data:
        # an additional language line was requested
        sportForm.names.append_entry()
        return render_template("sport.html", **locals())
            
    # Get exisiting sport on first rendering
    if not sportForm.submit.data:
        isInvalidSportId = True 
        try:
            sport = Node().getSport(sportId) 
            
            # empty the fieldlist
            while len(sportForm.names) > 0:
                sportForm.names.pop_entry()
                
            # fill fields in form
            for key,value in sport.items():
                if (key == "name"):
                    for country,text in value:
                        lng = InternationalizedString()
                        lng.country = country.upper()
                        lng.text    = text 
                        country
                        sportForm.names.append_entry(lng)
                        
            isInvalidSportId = False
        except NodeException as e:
            flash(e.message, category='error')
            sportId = "Invalid Id"
            return render_template("sport.html", **locals())

        except Exception as e:
            flash("Unknown error occured retrieving data for the requested sport " + sportId + ": " + e.__class__.__name__, category='error')
            sportId = "Invalid Id"
            return render_template("sport.html", **locals())
            
    return render_template("sport.html", **locals())
