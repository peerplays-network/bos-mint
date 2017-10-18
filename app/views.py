from app.forms import OperationForm, PendingOperationsForms, TranslatedFieldForm,\
    NewWalletForm, GetAccountForm
from app.models import InternationalizedString, LanguageNotFoundException
from app.node import Node, NodeException, NonScalableRequest
from app.utils import render_template_menuinfo
from flask import render_template, redirect, request, session, flash, url_for, make_response, abort
from wtforms     import FormField

from . import app, db, forms, config
from .utils import unlocked_wallet_required
from app import utils
from peerplays.exceptions import WalletExists

# InternationalizedString = namedtuple('InternationalizedString', ['country', 'text'])
# Sport = namedtuple('Sport', ['names', 'submit'])
###############################################################################
# Homepage
###############################################################################
@app.route('/')
def index():
    return redirect(url_for('overview'))

@app.route('/unlock', methods=['GET', 'POST'])
def unlock():
    unlockForm = forms.UnlockForm()

    if unlockForm.validate_on_submit():
        return redirect(utils.processNextArgument( request.args.get('next'), url_for('overview'))) 

    return render_template_menuinfo('unlock.html', **locals())

@app.route('/account/info')
# @unlocked_wallet_required
def account_info():
    account = Node().getSelectedAccount()
    
    form = forms.AccountForm()
    form.fill( account )
    
    return render_template_menuinfo("account.html", **locals())

@app.route("/account/select/<accountId>", methods=['GET', 'POST'])
@unlocked_wallet_required
def account_select(accountId):
    try:
        accountName = Node().selectAccount(accountId)
        flash('Account ' + accountName + ' selected!')
    except Exception as e:
        flash(e.__repr__(), category='error')
             
    return redirect(utils.processNextArgument( request.args.get('next'), url_for('overview'))) 

@app.route("/account/add", methods=['GET', 'POST'])
@unlocked_wallet_required
def account_add():
    form = GetAccountForm()
    formTitle = "Add Account to wallet"
     
    if form.validate_on_submit():
        try:
            Node().addAccountToWallet( form.name.data, form.password.data, form.role.data )
        except Exception as e:
            flash(e.__repr__(), category='error')
        
        redirect(utils.processNextArgument( request.args.get('next'), url_for('overview'))) 
             
    return render_template_menuinfo('generic.html', **locals())

@app.route("/wallet/new", methods=['GET', 'POST'])
def newwallet():
    form = NewWalletForm()
    formTitle = "Enter password to create new wallet"
    formMessage = "A local wallet will be automatically created. This local wallet is encrypted with your password, and will contain any private keys belonging to your accounts. It is important that you take the time to backup this wallet once created!"
    
    if form.validate_on_submit():
        try:
            Node().wallet_create( form.password.data ) 
            return redirect(utils.processNextArgument( request.args.get('next'), 'index'))
        except WalletExists as e:
            flash('There is already an open wallet.', category='error')
        except Exception as e:
            flash(e.__repr__(), category='error')
            
    return render_template_menuinfo('generic.html', **locals())

@app.route('/overview')
@app.route('/overview/<typeName>/<identifier>')
def overview(typeName=None, identifier=None):
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
        tmpTypeName   = utils.getChildType(typeName)
    else:
        # in this case the user only wants the sports
        tmpTypeName = 'sport'

    # reverse through all parents starting with the type given by typeName
    tmpParentIdentifier = identifier 
    while tmpTypeName and not tmpTypeName == 'sport':
        try:
            # build chain element for tmpTypeName
            tmpChainElement = buildChainElement( utils.getTypesGetter(tmpTypeName)(tmpParentIdentifier), utils.getTitle(tmpTypeName), tmpTypeName )
        except NodeException as e:
            flash(e.message, category='error')
            return render_template_menuinfo('index.html', **locals())
        
        tmpTypeName   = utils.getParentType(tmpTypeName)
        selected[tmpTypeName]      = tmpParentIdentifier
        tmpParentIdentifier = utils.getParentTypeGetter(tmpTypeName)(tmpParentIdentifier)
                        
        reverseChain.append( tmpChainElement )
       
    listChain = buildChainElement( utils.getTypesGetter('sport')(None), utils.getTitle('sport'), 'sport' )
    
    reverseChain.reverse()
    if reverseChain:
        tmpChainElement = listChain
        for chainElement in reverseChain:
            
            tmpChainElement["nextChainElement"] = chainElement
            tmpChainElement = chainElement
                   
    del tmpTypeName, tmpParentIdentifier
               
    return render_template_menuinfo('index.html', **locals())


@app.route("/cart", methods=['post','get'])
@unlocked_wallet_required
def pending_operations():
    pendingOperationsForm = PendingOperationsForms()
    pending_operations_active = True
    
    if pendingOperationsForm.validate_on_submit():
        flash('Operations have been flushed, not broadcasted yet.')
        Node().getActiveTransaction().ops = []
        
    
    # construct operationsform from active transaction
    transaction = Node().getOpenTransaction()
    
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

def genericNewForm(formClass, parentId=None):
    # look into https://github.com/Semantic-Org/Semantic-UI/issues/2978 for highlighting the chosen menu branch as well
    form = formClass()
    typeName      = formClass.getTypeName()
    typeNameTitle = utils.getTitle( typeName )
    
    selectedParent = None
    default        = None
    if parentId:
        selectedParent = utils.getParentByIdGetter(typeName)(parentId)
        default = { 'parentId': parentId }
        
    form.init(selectedParent, default)
    
    # Which button was pressed?
    if findAndProcessTranslatons(form):
        return render_template_menuinfo("new.html", **locals())
        
    elif form.submit.data and form.validate_on_submit():
        # Create new sport
        try:
            proposal = form.create()
            flash("A creation proposal for a new " + utils.getTitle(typeName) + " was created.")
            return redirect(utils.processNextArgument( request.args.get('next'), 'index'))
        except NodeException as e:
            flash(e.message, category='error')
            raise e.cause
    
    return render_template_menuinfo("new.html", **locals())

@app.route("/sport/new", methods=['post','get'])
@unlocked_wallet_required
def sport_new(): 
    return genericNewForm( forms.NewSportForm )

@app.route("/eventgroup/new", methods=['post','get'])    
@app.route("/eventgroup/new/<parentId>", methods=['post','get'])
@unlocked_wallet_required
def eventgroup_new(parentId=None): 
    return genericNewForm( forms.NewEventGroupForm, parentId ) 

@app.route("/event/new/<parentId>", methods=['post','get'])
@unlocked_wallet_required
def event_new(parentId): 
    return genericNewForm( forms.NewEventForm, parentId )

@app.route("/bettingmarketgroup/new/<parentId>", methods=['post','get'])
@unlocked_wallet_required
def bettingmarketgroup_new(parentId): 
    return genericNewForm( forms.NewBettingMarketGroupForm, parentId )

@app.route("/bettingmarket/new/<parentId>", methods=['post','get'])
@unlocked_wallet_required
def bettingmarket_new(parentId): 
    return genericNewForm( forms.NewBettingMarketForm, parentId )

@app.route("/bet/new", methods=['post','get'])
@unlocked_wallet_required
def bet_new(): 
    return render_template_menuinfo('index.html', **locals())

def genericUpdate(formClass, selectId):
    typeName = formClass.getTypeName()
    
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
    
    form.init(selectedObject)
    
    # first request? populate selected object
    if not form.submit.data:
        # preselect 
        form.select.data = selectId
        form.fill(selectedObject)
    
    if form.validate_on_submit(): # user submitted, wants to change  
        # all data was entered correctly, validate and update sport
        proposal = form.update(selectedObject['id'])
        flash("An update proposal  for " + utils.getTitle(typeName) + " (id=" + selectId + ") was created.")
        return redirect(utils.processNextArgument( request.args.get('next'), 'index'))
        
    return render_template_menuinfo("update.html", **locals())

@app.route("/sport/update", methods=['post','get'])
@app.route("/sport/update/<selectId>", methods=['post','get'])
@unlocked_wallet_required
def sport_update(selectId=None):
    return genericUpdate(forms.NewSportForm, selectId )

@app.route("/eventgroup/update", methods=['post','get'])
@app.route("/eventgroup/update/<selectId>", methods=['post','get'])
@unlocked_wallet_required
def eventgroup_update(selectId=None):
    formClass = forms.NewEventGroupForm
    
    return genericUpdate(formClass, selectId )
    
@app.route("/event/update", methods=['post','get'])
@app.route("/event/update/<selectId>", methods=['post','get'])
@unlocked_wallet_required
def event_update(selectId=None):
    formClass = forms.NewEventForm
                    
    return genericUpdate(formClass, selectId )
    
@app.route("/bettingmarketgroup/update", methods=['post','get'])
@app.route("/bettingmarketgroup/update/<selectId>", methods=['post','get'])
@unlocked_wallet_required
def bettingmarketgroup_update(selectId=None):
    formClass = forms.NewBettingMarketGroupForm
    
    return genericUpdate(formClass, selectId )
    
@app.route("/bettingmarket/update", methods=['post','get'])
@app.route("/bettingmarket/update/<selectId>", methods=['post','get'])
@unlocked_wallet_required
def bettingmarket_update(selectId=None):
    formClass = forms.NewBettingMarketForm
                    
    return genericUpdate(formClass, selectId )


    