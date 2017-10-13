from app.models import InternationalizedString, LanguageNotFoundException
from app.node import Node, NodeException
from flask import render_template, redirect, request, session, flash, url_for, make_response, abort

from . import app, db, forms, config
from .utils import unlocked_wallet_required
from functools import wraps
from app.utils import render_template_menuinfo
from app.forms import OperationForm, PendingOperationsForms


# InternationalizedString = namedtuple('InternationalizedString', ['country', 'text'])
# Sport = namedtuple('Sport', ['names', 'submit'])
###############################################################################
# Homepage
###############################################################################

@app.route('/')
@unlocked_wallet_required
def index():
    return render_template_menuinfo('index.html')


@app.route('/unlock', methods=['GET', 'POST'])
def unlock():
    unlockForm = forms.UnlockForm()

    if unlockForm.validate_on_submit():
        return redirect(request.args.get("next", url_for("index")))

    return render_template  ('unlock.html', **locals())


@app.route('/demo')
@unlocked_wallet_required
def demo():
    return "foobar"


@app.route("/wallet/new")
def newwallet():
    return "foobar"

@app.route("/cart", methods=['post','get'])
def pending_operations():
    pendingOperationsForm = PendingOperationsForms()
    pending_operations_active = True
    
    if pendingOperationsForm.validate_on_submit():
        flash('Operations have been flushed, not broadcasted yet.')
        Node().getActiveTransaction().ops = []
        
    
    # construct operationsform from active transaction
    transaction = Node().getActiveTransaction()
    
    if transaction:
        for op in transaction.ops:
            operationForm = OperationForm()
            operationForm.name = op.__repr__() 
            pendingOperationsForm.operations.append_entry(operationForm)
    
    
    return render_template_menuinfo("cart.html", **locals())

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
            flash("A creation proposal for a new sport was created.")
            return redirect(url_for('index'))
        except NodeException as e:
            flash(e.message, category='error')
            raise e.cause
        
        return render_template_menuinfo("sport/new.html", **locals())
    
    elif sportForm.addLanguage.data:
        # an additional language line was requested
        sportForm.names.append_entry()
        return render_template_menuinfo("sport/new.html", **locals())
    
    # Show SportForm
    return render_template_menuinfo("sport/new.html", **locals())
    
@app.route("/sport/update", methods=['post','get'])
@unlocked_wallet_required
def sport_update_select():
    # highlight active menu item
    sport_update_active = " active"
    
    sportForm           = forms.SportSelectForm()
        
    if sportForm.validate_on_submit():
        return redirect(url_for('sport_update', sportId=sportForm.sport.data))
        
    return render_template_menuinfo("sport/select.html", **locals())
    
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
        return render_template_menuinfo("sport/update.html", **locals())

    except Exception as e:
        flash("Unknown error occured retrieving data for the requested sport " + sportId + ": " + e.__class__.__name__, category='error')
        sportId = "Invalid Id"
        return render_template_menuinfo("sport/update.html", **locals())
   
   
    # Which button was pressed?
    if sportForm.submit.data and sportForm.validate_on_submit():
        # all data was entered correctly, validate and update sport
        proposal = Node().updateSport(sportId, InternationalizedString.parseToList(sportForm.names))
        flash("An update proposal  for sport (id=" + sportId + ") was created.")
        return redirect(url_for('index'))
    
    elif sportForm.addLanguage.data:
        # an additional language line was requested
        sportForm.names.append_entry()
        return render_template_menuinfo("sport/update.html", **locals())
            
    return render_template_menuinfo("sport/update.html", **locals())

@app.route("/eventgroup/new", methods=['post','get'])
@unlocked_wallet_required
def eventgroup_new():
    # look into https://github.com/Semantic-Org/Semantic-UI/issues/2978 for highlighting the chosen menu branch as well
    
    # highlight active menu item
    eventgroup_active = " active"
    
    newObjectForm = forms.NewForm()
    newObjectName = "event group"
    
    # Which button was pressed?
    if newObjectForm.submit.data and newObjectForm.validate_on_submit():
        # Create new object
        try:
#             proposal = Node().createEventGroup( InternationalizedString.parseToList(newObjectForm.names), sportId )
            proposalId = "mockId"
            newObjectId = "mockId" 
            flash("A creation proposal (id=" + proposalId + ") for a new " + newObjectName + " (id=" + newObjectId + ") was created.")
            return redirect(url_for('index'))
        except NodeException as e:
            flash(e.message, category='error')
            raise e.cause
        
        return render_template_menuinfo("new.html", **locals())
    
    elif newObjectForm.addLanguage.data:
        # an additional language line was requested
        newObjectForm.names.append_entry()
        return render_template_menuinfo("new.html", **locals())
    
    # Show NewForm
    return render_template_menuinfo("new.html", **locals())

@app.route("/bettingmarketgroup/new", methods=['post','get'])
@unlocked_wallet_required
def bettingmarketgroup_new():
    # look into https://github.com/Semantic-Org/Semantic-UI/issues/2978 for highlighting the chosen menu branch as well
    
    # highlight active menu item
    bettingmarketgroup_new_active = " active"
    
    newObjectForm = forms.NewForm()
    newObjectName = "betting market group"
    
    # Which button was pressed?
    if newObjectForm.submit.data and newObjectForm.validate_on_submit():
        # Create new object
        try:
            proposal = Node().createBettingMarketGroup( InternationalizedString.parseToList(newObjectForm.names) )
            proposalId = "mockId"
            newObjectId = "mockId" 
            flash("A creation proposal (id=" + proposalId + ") for a new " + newObjectName + " (id=" + newObjectId + ") was created.")
            return redirect(url_for('index'))
        except NodeException as e:
            flash(e.message, category='error')
            raise e.cause
        
        return render_template_menuinfo("new.html", **locals())
    
    elif newObjectForm.addLanguage.data:
        # an additional language line was requested
        newObjectForm.names.append_entry()
        return render_template_menuinfo("new.html", **locals())
    
    # Show NewForm
    return render_template_menuinfo("new.html", **locals())

@app.route("/bettingmarket/new", methods=['post','get'])
@unlocked_wallet_required
def bettingmarket_new():
    # look into https://github.com/Semantic-Org/Semantic-UI/issues/2978 for highlighting the chosen menu branch as well
    
    # highlight active menu item
    bettingmarket_new_active = " active"
    
    newObjectForm = forms.NewForm()
    newObjectName = "betting market"
    
    # Which button was pressed?
    if newObjectForm.submit.data and newObjectForm.validate_on_submit():
        # Create new object
        try:
            proposal = Node().createBettingMarket( InternationalizedString.parseToList(newObjectForm.names) )
            proposalId = "mockId"
            newObjectId = "mockId" 
            flash("A creation proposal (id=" + proposalId + ") for a new " + newObjectName + " (id=" + newObjectId + ") was created.")
            return redirect(url_for('index'))
        except NodeException as e:
            flash(e.message, category='error')
            raise e.cause
        
        return render_template_menuinfo("new.html", **locals())
    
    elif newObjectForm.addLanguage.data:
        # an additional language line was requested
        newObjectForm.names.append_entry()
        return render_template_menuinfo("new.html", **locals())
    
    # Show NewForm
    return render_template_menuinfo("new.html", **locals())

