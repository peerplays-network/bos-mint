from flask import render_template, redirect, request, session, flash, url_for, make_response, abort
from datetime import datetime
from . import app, db, forms, config
from .utils import unlocked_wallet_required

from collections import namedtuple
from app.forms import  InternationalizedStringForm
from app.node import Node, NodeException
from app.models import InternationalizedString, LanguageNotFoundException

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
@unlocked_wallet_required
def sport_new():
    # highlight active menu item
    sport_new_active = " active"
    
    sportForm = forms.SportNewForm()
    
    # Which button was pressed?
    if sportForm.submit.data and sportForm.validate_on_submit():
        # Create new sport
        try:
            proposal = Node().createSport( InternationalizedString.parseToList(sportForm.names) )
            flash("A creation proposal (id=" + "1" + ") for a new Sport (id=" + proposal + ") was created.")
            return redirect(url_for('index'))
        except NodeException as e:
            flash(e.message, category='error')
            raise e.cause
        
        return render_template("sport/new.html", **locals())
    
    elif sportForm.addLanguage.data:
        # an additional language line was requested
        sportForm.names.append_entry()
        return render_template("sport/new.html", **locals())
    
    # Show SportForm
    return render_template("sport/new.html", **locals())
    
@app.route("/sport/update", methods=['post','get'])
@unlocked_wallet_required
def sport_update_select():
    # highlight active menu item
    sport_update_active = " active"
    
    sportForm           = forms.SportSelectForm()
        
    if sportForm.validate_on_submit():
        return redirect(url_for('sport_update', sportId=sportForm.sport.data))
        
    return render_template("sport/select.html", **locals())
    
@app.route("/sport/update/<sportId>", methods=['post','get'])
@unlocked_wallet_required
def sport_update(sportId):
    # highlight active menu item
    sport_update_active = " active"
    
    sportForm = forms.SportUpdateForm()
    
    # Get the chosen sport
    isInvalidSportId = True 
    try:
        if sportId:
            sport = Node().getSport(sportId)
            sportForm.sport.choices = [ (sport["id"], sport["name"][0][1]) ]
            sportForm.sport.data    = sport["id"]
            
            if not sportForm.submit.data and not sportForm.addLanguage.data:
                # empty the fieldlist
                while len(sportForm.names) > 0:
                    sportForm.names.pop_entry()
                
                # fill fields in form
                for key,value in sport.items():
                    if (key == "name"):
                        for country,text in value:
                            try:
                                lng = InternationalizedString( country, text )
                            except LanguageNotFoundException as e:
                                # append an entry indicating the unknown language
                                lng = InternationalizedString( InternationalizedString.UNKNOWN, country + " - " + text )

                            # append entry to a FieldList creates forms from dictionary!                            
                            sportForm.names.append_entry( lng.getForm() )
            
            isInvalidSportId = False
                                
    except NodeException as e:
        flash(e.message, category='error')
        sportId = "Invalid Id"
        sportForm.sport.choices = [ ("Invalid Id", "Invalid Sport") ]
        sportForm.sport.data    = "Invalid Id"
        return render_template("sport/update.html", **locals())

    except Exception as e:
        flash("Unknown error occured retrieving data for the requested sport " + sportId + ": " + e.__class__.__name__, category='error')
        sportId = "Invalid Id"
        return render_template("sport/update.html", **locals())
   
   
    # Which button was pressed?
    if sportForm.submit.data and sportForm.validate_on_submit():
        # all data was entered correctly, validate and update sport
        proposal = Node().updateSport(sportId, InternationalizedString.parseToList(sportForm.names))
        flash("An update proposal (id=" + proposal + ") for Sport (id=" + sportId + ") was created.")
        return redirect(url_for('index'))
    
    elif sportForm.addLanguage.data:
        # an additional language line was requested
        sportForm.names.append_entry()
        return render_template("sport/update.html", **locals())
            
    
            
    return render_template("sport/update.html", **locals())
