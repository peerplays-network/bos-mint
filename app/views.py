from app.models import InternationalizedString, LanguageNotFoundException
from app.node import Node, NodeException
from flask import render_template, redirect, request, session, flash, url_for, make_response, abort

from . import app, db, forms, config
from .utils import unlocked_wallet_required
from functools import wraps
from app.utils import render_template_menuinfo
from app.forms import OperationForm, PendingOperationsForms, TranslatedFieldForm
from test.test_hash import FixedHash

from wtforms     import FormField


# InternationalizedString = namedtuple('InternationalizedString', ['country', 'text'])
# Sport = namedtuple('Sport', ['names', 'submit'])
###############################################################################
# Homepage
###############################################################################

@app.route('/')
@unlocked_wallet_required
def index():
    return redirect(url_for('overview'))

@app.route('/overview')
@app.route('/overview/<typeName>/<identifier>')
@unlocked_wallet_required
def overview(typeName=None, identifier=None):
    # get list of objects for typename, containing id, typeName and toString field
    getter = {
      'sport' :     lambda: [ { 
                               'id' : x["id"], 
                               'typeName': 'sport',
                               'toString': x["id"] + ' - ' + x["name"][0][1]  
                              } for x in Node().getSports() ],
      'eventgroup': lambda tmpSportId: [ { 
                                          'id' : x["id"], 
                                          'typeName': 'eventgroup',
                                          'toString': x["id"] + ' - ' + x["name"][0][1]  
                                         } for x in Node().getEventGroups(tmpSportId) ],
      'event': lambda tmpEventGroupId: [ { 
                                          'id' : x["id"], 
                                          'typeName': 'event',
                                          'toString': x["id"] + ' - ' + x["name"][0][1]  
                                         } for x in Node().getEvents(tmpEventGroupId) ], 
      'bettingmarketgroup': lambda tmpEventId: [ { 
                                          'id' : x["id"], 
                                          'typeName': 'bettingmarketgroup',
                                          'toString': x["id"] + ' - ' + x["description"][0][1]  
                                         } for x in Node().getBettingMarketGroups(tmpEventId) ],
      'bettingmarket': lambda tmpBMGId: [ { 
                                          'id' : x["id"], 
                                          'typeName': 'bettingmarket',
                                          'toString': x["id"] + ' - ' + x["description"][0][1]  
                                         } for x in Node().getBettingMarkets(tmpBMGId) ],
      'bet': lambda tmpBMGId: [  ], # not implemented yet
    }
    # get object for typename, containing id 
    reverseId = {
      'sport' :     lambda tmpId: None,
      'eventgroup': lambda tmpId: Node().getEventGroup(tmpId).sport.identifier,
      'event':      lambda tmpId: Node().getEvent(tmpId).eventgroup.identifier,
      'bettingmarketgroup':        lambda tmpId: Node().getBettingMarketGroup(tmpId).event.identifier,
      'bettingmarket':         lambda tmpId: Node().getBettingMarket(tmpId).bettingmarketgroup.identifier,
      'bet':        lambda tmpId: tmpId,
    }
    # which type does it cascade to
    nextType = {
                 'sport': 'eventgroup',
                 'eventgroup': 'event',
                 'event': 'bettingmarketgroup',
                 'bettingmarketgroup': 'bettingmarket',
                 'bettingmarket': 'bet'
               }
    # which type does it come from
    reverseType = {
                 'sport': None,
                 'eventgroup': 'sport',
                 'event': 'eventgroup',
                 'bettingmarketgroup': 'event',
                 'bettingmarket': 'bettingmarketgroup',
                 'bet': 'bettingmarket'
               }
    # human readable title
    titles   = { 
                 'sport': 'Sport',
                 'eventgroup': 'Event group',
                 'event': 'Event',
                 'bettingmarketgroup': 'Betting market group',
                 'bettingmarket': 'Betting market',
                 'bet': 'Bets'
               }
    # selected ids
    selected = { }
    
    # same structure for all chain elements    
    def buildChainElement( tmpList, title, typeName ):
        return { 'list': tmpList,
                 'title': title,
                 'typeName': typeName }
    
    # build reverse chain starting with the one selected
    reverseChain = []
    if typeName:
        tmpTypeName   = nextType.get(typeName)
    else:
        # in this case the user only wants the sports
        tmpTypeName = 'sport'

    tmpIdentifier = identifier 
    while tmpTypeName and not tmpTypeName == 'sport':
        tmpChainElement = buildChainElement( getter.get(tmpTypeName)(tmpIdentifier), titles.get(tmpTypeName), tmpTypeName ) 
        tmpTypeName   = reverseType.get(tmpTypeName)
        selected[tmpTypeName]      = tmpIdentifier
        tmpIdentifier = reverseId.get(tmpTypeName)(tmpIdentifier)
        
        
        reverseChain.append( tmpChainElement )
                
#         if tmpTypeName == 'event':
#             tmpIdentifier = '1.16.0'
#         else:
#             tmpIdentifier = '1'
       
    listChain = buildChainElement( getter.get('sport')(), titles.get('sport'), 'sport' )
    
    reverseChain.reverse()
    if reverseChain:
        tmpChainElement = listChain
        for chainElement in reverseChain:
            
            tmpChainElement["nextChainElement"] = chainElement
            tmpChainElement = chainElement
                   
    del getter, tmpTypeName, tmpIdentifier
               
    return render_template_menuinfo('index.html', **locals())


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

def genericNewForm(form, createFunction, typeName):
    # look into https://github.com/Semantic-Org/Semantic-UI/issues/2978 for highlighting the chosen menu branch as well
    
    def findAndProcessTranslatons(form):
        for field in form._fields.values():
            if isinstance(field, FormField) and isinstance(field.form, TranslatedFieldForm) and field.addLanguage.data:
                # an additional language line was requested
                field.translations.append_entry()
                return True
            
        return False
    
    # Which button was pressed?
    if findAndProcessTranslatons(form):
        del createFunction
        return render_template_menuinfo("new.html", **locals())
        
    elif form.submit.data and form.validate_on_submit():
        # Create new sport
        try:
            proposal = createFunction( form )
            flash("A creation proposal for a new " + typeName + " was created.")
            return redirect(url_for('index'))
        except NodeException as e:
            flash(e.message, category='error')
            raise e.cause
    
    del createFunction 
    
    return render_template_menuinfo("new.html", **locals())

@app.route("/sport/new", methods=['post','get'])
@unlocked_wallet_required
def sport_new(): 
    typeName         = "sport"
    form = forms.NewSportForm()
    createFunction = lambda tmpForm: Node().createSport( InternationalizedString.parseToList(tmpForm.name.translations) )
    
    return genericNewForm(form, createFunction, typeName)
    
@app.route("/eventgroup/new", methods=['post','get'])
@unlocked_wallet_required
def eventgroup_new(): 
    typeName         = "eventgroup"
    form = forms.NewEventGroupForm()
    createFunction = lambda tmpForm: Node().createSport( InternationalizedString.parseToList(tmpForm.name.translations) )
    
    return genericNewForm(form, createFunction, typeName)

@app.route("/event/new", methods=['post','get'])
@unlocked_wallet_required
def event_new(): 
    typeName         = "event"
    form = forms.NewEventForm()
    createFunction = lambda tmpForm: Node().createSport( InternationalizedString.parseToList(tmpForm.name.translations) )
    
    return genericNewForm(form, createFunction, typeName)

@app.route("/bettingmarketgroup/new", methods=['post','get'])
@unlocked_wallet_required
def bettingmarketgroup_new(): 
    typeName         = "bettingmarketgroup"
    form = forms.NewBettingMarketGroupForm()
    createFunction = lambda tmpForm: Node().createSport( InternationalizedString.parseToList(tmpForm.name.translations) )
    
    return genericNewForm(form, createFunction, typeName)

@app.route("/bettingmarket/new", methods=['post','get'])
@unlocked_wallet_required
def bettingmarket_new(): 
    typeName         = "bettingmarket"
    form = forms.NewBettingMarketForm()
    createFunction = lambda tmpForm: Node().createSport( InternationalizedString.parseToList(tmpForm.name.translations) )
    
    return genericNewForm(form, createFunction, typeName)

@app.route("/bet/new", methods=['post','get'])
@unlocked_wallet_required
def bet_new(): 
    return render_template_menuinfo('index.html', **locals())

