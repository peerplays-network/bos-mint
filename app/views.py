from app.forms import OperationForm, PendingOperationsForms, TranslatedFieldForm
from app.models import InternationalizedString, LanguageNotFoundException
from app.node import Node, NodeException, NonScalableRequest
from app.utils import render_template_menuinfo
from flask import render_template, redirect, request, session, flash, url_for, make_response, abort
from wtforms     import FormField

from . import app, db, forms, config
from .utils import unlocked_wallet_required
from app import utils

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
    # get object for typename, containing id of parent object
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
    # selected ids
    selected = { }
    
    # same structure for all chain elements    
    def buildChainElement( tmpList, title, typeName ):
        return { 'list':     tmpList,
                 'title':    title,
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
        try:
            tmpChainElement = buildChainElement( utils.getTypesGetter(tmpTypeName)(tmpIdentifier), utils.getTitle(tmpTypeName), tmpTypeName )
        except NodeException as e:
            flash(e.message, category='error')
            return render_template_menuinfo('index.html', **locals())
        
        tmpTypeName   = reverseType.get(tmpTypeName)
        selected[tmpTypeName]      = tmpIdentifier
        tmpIdentifier = reverseId.get(tmpTypeName)(tmpIdentifier)
                
        reverseChain.append( tmpChainElement )
       
    listChain = buildChainElement( utils.getTypesGetter('sport')(None), utils.getTitle('sport'), 'sport' )
    
    reverseChain.reverse()
    if reverseChain:
        tmpChainElement = listChain
        for chainElement in reverseChain:
            
            tmpChainElement["nextChainElement"] = chainElement
            tmpChainElement = chainElement
                   
    del tmpTypeName, tmpIdentifier
               
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

def findAndProcessTranslatons(form):
    for field in form._fields.values():
        if isinstance(field, FormField) and isinstance(field.form, TranslatedFieldForm) and field.addLanguage.data:
            # an additional language line was requested
            field.translations.append_entry()
            return True
        
    return False

def genericNewForm(form, createFunction, typeName):
    # look into https://github.com/Semantic-Org/Semantic-UI/issues/2978 for highlighting the chosen menu branch as well
    
    typeNameTitle = utils.getTitle(typeName)
    
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

def genericUpdate(formClass, typeName, selectId, populateFunction, updateFunction ):
    selectFunction  = utils.getTypeGetter(typeName)
    choicesFunction = utils.getTypesGetter(typeName)
            
    try:
        # maybe only query the selected object, if one is preselected, saves traffic
        # currently: always query all
        parentId = None
        if selectId:
            parentId = utils.getParentTypeGetter(typeName)(selectId)
            
        form = forms.buildUpdateForm(typeName, 
                                     choicesFunction(parentId),
                                     formClass,
                                     selectId )
    except NonScalableRequest as e:
        return redirect(url_for('overview'))
    except NodeException as e:
        flash(e.message, category='error')
        return render_template_menuinfo("update.html", **locals())
    
    typeNameTitle = utils.getTitle(typeName)
    
    if not selectId:
        if form.submit.data:
            return redirect(url_for(typeName + '_update', selectId=form.select.data))
        else:
            return render_template_menuinfo("update.html", **locals())

    # update was called with given id, make sure it exists
    try:
        if selectId:
            selectedObject = selectFunction(selectId)
    except NodeException as e:
        flash(e.message, category='error')
        return render_template_menuinfo("update.html", **locals())

    # user wants to add language?
    if findAndProcessTranslatons(form):
        return render_template_menuinfo("update.html", **locals())
    
    # first request? populate selected object
    if not form.submit.data:
        # preselect 
        form.select.data = selectId
        
    populateFunction(form, selectedObject)
    
    if form.validate_on_submit(): # user submitted, wants to change  
        # all data was entered correctly, validate and update sport
        proposal = updateFunction(form, selectedObject)
        flash("An update proposal  for " + utils.getTitle(typeName) + " (id=" + selectId + ") was created.")
        return redirect(url_for('index'))
    
    return render_template_menuinfo("update.html", **locals())

@app.route("/sport/update", methods=['post','get'])
@app.route("/sport/update/<selectId>", methods=['post','get'])
@unlocked_wallet_required
def sport_update(selectId=None):
    # highlight active menu item
    typeName = 'sport'
    
    def updateFunction(form, selectedObject):
        return Node().updateSport(selectedObject['id'], InternationalizedString.parseToList(form.name))

    def populateFunction(form, selectedObject):
        # fill values on initialization
        if not form.submit.data:
            form.name.fill( selectedObject['name'] )

    return genericUpdate(forms.NewSportForm, typeName, selectId, populateFunction, updateFunction )

@app.route("/eventgroup/update", methods=['post','get'])
@app.route("/eventgroup/update/<selectId>", methods=['post','get'])
@unlocked_wallet_required
def eventgroup_update(selectId=None):
    formClass = forms.NewEventGroupForm
    typeName  = 'eventgroup'
    
    def updateFunction(form, selectedObject):
        return Node().updateEventGroup(selectedObject['id'], InternationalizedString.parseToList(form.name), form.sport.data)

    def populateFunction(form, selectedObject):
        # fill values on initialization
        if not form.submit.data:
            form.sport.data = selectedObject.sport['id']
            form.name.fill( selectedObject['name'] )

    return genericUpdate(formClass, typeName, selectId, populateFunction, updateFunction )
    
@app.route("/event/update", methods=['post','get'])
@app.route("/event/update/<selectId>", methods=['post','get'])
@unlocked_wallet_required
def event_update(selectId=None):
    formClass = forms.NewEventForm
    typeName  = 'event'
    
    def updateFunction(form, selectedObject):
        return Node().updateEvent(selectedObject['id'], 
                                  InternationalizedString.parseToList(form.name), 
                                  InternationalizedString.parseToList(form.season),
                                  form.start.data,
                                  form.eventgroup.data)

    def populateFunction(form, selectedObject):
        # choices need to be filled at all times
        form.eventgroup.choices = forms.selectDictToList(utils.getTypesGetter('eventgroup')(selectedObject.eventgroup.sport['id']))
        
        # fill values on initialization
        if not form.submit.data:
            form.eventgroup.data = selectedObject.eventgroup['id']
            form.name.fill( selectedObject['name'] )
            form.season.fill( selectedObject['season'] )
                    
    return genericUpdate(formClass, typeName, selectId, populateFunction, updateFunction )
    
@app.route("/bettingmarketgroup/update", methods=['post','get'])
@app.route("/bettingmarketgroup/update/<selectId>", methods=['post','get'])
@unlocked_wallet_required
def bettingmarketgroup_update(selectId=None):
    formClass = forms.NewBettingMarketGroupForm
    typeName  = 'bettingmarketgroup'
    
    def updateFunction(form, selectedObject):
        return Node().updateBettingMarketGroup(selectedObject['id'], 
                                  InternationalizedString.parseToList(form.description), 
                                  form.event.data)

    def populateFunction(form, selectedObject):
        # choices need to be filled at all times
        form.event.choices = forms.selectDictToList(utils.getTypesGetter('event')(selectedObject.event['event_group_id']))
        
        # fill values on initialization
        if not form.submit.data:
            form.event.data    = selectedObject['event_id']
            form.bettingmarketrule.data = selectedObject['rules_id']
            form.description.fill( selectedObject['description'] )
                    
    return genericUpdate(formClass, typeName, selectId, populateFunction, updateFunction )
    
@app.route("/bettingmarket/update", methods=['post','get'])
@app.route("/bettingmarket/update/<selectId>", methods=['post','get'])
@unlocked_wallet_required
def bettingmarket_update(selectId=None):
    formClass = forms.NewBettingMarketForm
    typeName  = 'bettingmarket'
    
    def updateFunction(form, selectedObject):
        return Node().updateBettingMarket(selectedObject['id'], 
                                  InternationalizedString.parseToList(form.payoutCondition),
                                  InternationalizedString.parseToList(form.description),  
                                  form.bettingmarketgroup.data)

    def populateFunction(form, selectedObject):
        # choices need to be filled at all times
        form.bettingmarketgroup.choices = forms.selectDictToList(utils.getTypesGetter('bettingmarketgroup')(selectedObject.bettingmarketgroup['event_id']))
        
        # fill values on initialization
        if not form.submit.data:
            form.bettingmarketgroup.data    = selectedObject['group_id']
            form.payoutCondition.fill( selectedObject['payout_condition'] )
            form.description.fill( selectedObject['description'] )
                    
    return genericUpdate(formClass, typeName, selectId, populateFunction, updateFunction )


    