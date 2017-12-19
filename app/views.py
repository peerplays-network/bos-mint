from app.forms import TranslatedFieldForm, NewWalletForm, GetAccountForm,\
    ApprovalForm, BettingMarketGroupResolveForm
from app.istring import InternationalizedString, LanguageNotFoundException
from app.node import Node, NodeException, NonScalableRequest,\
                        BroadcastActiveOperationsExceptions
from app.utils import render_template_menuinfo, requires_node
from flask import render_template, redirect, request, session, flash,\
                    url_for, make_response, abort
from wtforms import FormField, SubmitField

from . import app, db, forms, config
from .utils import unlocked_wallet_required
from app import utils, widgets
from peerplays.exceptions import WalletExists
from app.models import LocalProposal, ViewConfiguration

###############################################################################
# Homepage
###############################################################################


@app.route('/')
def index():
    return redirect(url_for('overview'))


@app.route('/lock', methods=['GET', 'POST'])
@requires_node
def lock():
    Node().lock()
    return redirect(url_for('overview'))


@app.route('/unlock', methods=['GET', 'POST'])
@requires_node
def unlock():
    unlockForm = forms.UnlockForm()

    if unlockForm.validate_on_submit():
        return redirect(utils.processNextArgument(
            request.args.get('next'), 'overview'))

    return render_template_menuinfo('unlock.html', **locals())


@app.route('/account/info')
@requires_node
def account_info():
    account = Node().getSelectedAccount()

    form = forms.AccountForm()
    form.fill(account)

    return render_template_menuinfo("account.html", **locals())


@app.route("/account/select/<accountId>", methods=['GET', 'POST'])
@requires_node
def account_select(accountId):
    try:
        accountName = Node().selectAccount(accountId)
        flash('Account ' + accountName + ' selected!')
    except BroadcastActiveOperationsExceptions as e:
        flash(str(e), category='error')
        return redirect(url_for('pending_operations'))

    return redirect(utils.processNextArgument(
        request.args.get('next'), 'overview'))


@app.route("/account/add", methods=['GET', 'POST'])
@unlocked_wallet_required
@requires_node
def account_add():
    form = GetAccountForm()
    formTitle = "Add Account to wallet"

    if form.validate_on_submit():
        # submit checks if account exists
        try:
            Node().addAccountToWallet(form.privateKey.data)
        except Exception as e:
            flash(
                'There was a problem adding the account to the wallet. ({})'.format(
                    str(e)),
                category='error')

        redirect(utils.processNextArgument(
            request.args.get('next'), 'overview'))

    return render_template_menuinfo('generic.html', **locals())


@app.route("/wallet/new", methods=['GET', 'POST'])
@requires_node
def newwallet():
    form = NewWalletForm()
    formTitle = "Enter password to create new wallet"
    formMessage = (
        "A local wallet will be automatically created." +
        " This local wallet is encrypted with your password, and" +
        " will contain any private keys belonging to your accounts." +
        " It is important that you take the time to backup this wallet" +
        " once created!")

    if form.validate_on_submit():
        try:
            Node().wallet_create(form.password.data)
            return redirect(utils.processNextArgument(
                request.args.get('next'), 'index'))
        except WalletExists as e:
            flash('There is already an open wallet.', category='error')
        except Exception as e:
            flash(e.__repr__(), category='error')

    return render_template_menuinfo('generic.html', **locals())


@app.route('/overview')
@app.route('/overview/<typeName>')
@app.route('/overview/<typeName>/<identifier>')
@requires_node
def overview(typeName=None, identifier=None):
    # selected ids
    selected = {}

    # same structure for all chain elements and list elements
    def buildListElements(tmpList):
            for entry in tmpList:
                if entry['typeName'] == 'event':
                    entry['extraLink'] = [{
                        'title': 'Start',
                        'link': 'event_start',
                        'icon': 'lightning'
                    }, {
                        'title': 'Finish',
                        'link': 'event_finish',
                        'icon': 'flag checkered'
                    }]
                elif entry['typeName'] == 'bettingmarket':
                    entry['extraLink'] = [{
                        'title': 'Grade',
                        'link': 'bettingmarket_grade',
                        'icon': 'book'
                    }]
                elif entry['typeName'] == 'bettingmarketgroup':
                    entry['extraLink'] = [{
                        'title': 'Freeze',
                        'link': 'bettingmarketgroup_freeze',
                        'icon': 'snowflake'
                    }, {
                        'title': 'Unfreeze',
                        'link': 'bettingmarketgroup_unfreeze',
                        'icon': 'fire'
                    }, {
                        'title': 'Resolve',
                        'link': 'bettingmarketgroup_resolve',
                        'icon': 'money'
                    }]
            return tmpList

    def buildChainElement(parentId, typeName):
        tmpList = utils.getComprisedTypesGetter(typeName)(parentId)
        title = utils.getTitle(typeName)

        if typeName == 'bettingmarketgroup':
            return {
                'list': buildListElements(tmpList),
                'title': title,
                'typeName': typeName,
                'extraLink': [{
                    'title': 'Create ' + utils.getTitle('bettingmarketgrouprule'),
                    'link': 'bettingmarketgrouprule_new',
                    'icon': 'plus'
                }, {
                    'title': 'List ' + utils.getTitle('bettingmarketgrouprule') + 's',
                    'link': 'overview',
                    'argument': ('typeName', 'bettingmarketgrouprule'),
                    'icon': 'unhide'
                }, {
                    'title': 'Resolve ' + utils.getTitle('bettingmarketgroup') + 's',
                    'link': 'bettingmarketgroup_resolve_selectgroup',
                    'argument': ('eventId', parentId),
                    'icon': 'money'
                }
                ]}
        else:
            return {
                'list': buildListElements(tmpList),
                'title': title,
                'typeName': typeName
            }

    # bettingmarketroule has no parent or childs
    if typeName == 'bettingmarketgrouprule':
        redirect(url_for('overview', typeName='bettingmarketgrouprule'))

    # build reverse chain starting with the one selected
    reverseChain = []
    if typeName and identifier:
        tmpTypeName = utils.getChildType(typeName)
    elif typeName and not identifier:
        # overview of desired typeName
        tmpTypeName = typeName
    else:
        # in this case the user only wants the sports
        tmpTypeName = 'sport'

    # reverse through all parents starting with the type given by typeName
    tmpParentIdentifier = identifier
    while tmpTypeName and not tmpTypeName == 'sport':
        # build chain element for tmpTypeName
        tmpChainElement = buildChainElement(tmpParentIdentifier,
                                            tmpTypeName)

        tmpTypeName = utils.getParentType(tmpTypeName)
        if tmpTypeName:
            selected[tmpTypeName] = tmpParentIdentifier
            tmpParentIdentifier = utils.getComprisedParentTypeGetter(
                tmpTypeName)(tmpParentIdentifier)

        if isinstance(tmpChainElement, list):
            for item in tmpChainElement:
                reverseChain.append(item)
        else:
            reverseChain.append(tmpChainElement)

    if tmpTypeName == 'sport':
        sportElement = buildChainElement(None, 'sport')
        reverseChain.append(sportElement)

    reverseChain.reverse()
    listChain = reverseChain[0]
    if reverseChain:
        tmpChainElement = []
        for chainElement in reverseChain:
            if tmpChainElement:
                tmpChainElement["nextChainElement"] = chainElement

            tmpChainElement = chainElement

    del tmpTypeName, tmpParentIdentifier

    return render_template_menuinfo('index.html', **locals())


@app.route("/pending/discard", methods=['GET', 'POST'])
@unlocked_wallet_required
def pending_operations_discard():
    Node().discardPendingTransaction()
    flash('All pending operations have been discarded.')

    if session.get('automatic_approval', False):
        pass

    return redirect(url_for('pending_operations'))


@app.route("/pending/broadcast", methods=['POST'])
@unlocked_wallet_required
def pending_operations_broadcast():
    if ViewConfiguration.get('automatic_approval', 'enabled', False):
        Node().get_node().blocking = True

    try:
        answer = Node().broadcastPendingTransaction()

        if ViewConfiguration.get('automatic_approval', 'enabled', False):
            proposalId = answer['trx']['operation_results'][0][1]
            flash('All pending operations have been broadcasted and the resulting proposal has been approved.')
            Node().acceptProposal(proposalId)
        else:
            flash('All pending operations have been broadcasted.')

        return redirect(url_for('pending_operations'))
    except Exception as e:
        Node().get_node().blocking = False
        raise e


@app.route("/pending", methods=['get'])
def pending_operations():
    form = ApprovalForm()
    form.approve.data = ViewConfiguration.get('automatic_approval', 'enabled', False)

    # construct operationsform from active transaction
    transaction = Node().getPendingTransaction()
    if transaction:
        containerList = [ widgets.prepareTransactionDataForRendering(transaction) ]
    del transaction

    return render_template_menuinfo("pendingOperations.html", **locals())


@app.route("/pending/automaticapproval", methods=['post'])
def automatic_approval():
    form = ApprovalForm()

    if form.validate_on_submit():
        ViewConfiguration.set('automatic_approval', 'enabled', form.approve.data)

    return redirect(url_for('pending_operations'))


@app.route("/proposals", methods=['post', 'get'])
def votable_proposals():
    try:
        proposals = Node().getAllProposals()
        if proposals:
            accountId = Node().getSelectedAccount()['id']

            containerList = widgets.prepareProposalsDataForRendering(proposals)
            containerReview = {}
            reviewedProposals = LocalProposal.getAllAsList()

            for proposal in proposals:
                if proposal['id'] in reviewedProposals:
                    # if the proposal is stored in the localproposals database it already has been reviewed, but maybe
                    # rejected
                    containerReview[proposal['id']] = {'reviewed': True, 'approved': accountId in proposal.get('available_active_approvals')}
                elif accountId in proposal.get('available_active_approvals'):
                    # already approved ones also go into the reviewed column, even without a localproposal entry
                    containerReview[proposal['id']] = {'reviewed': True, 'approved': True}

        del proposals

        return render_template_menuinfo("votableProposals.html", **locals())
    except NodeException as e:
        flash(str(e), category='error')
        return redirect(url_for("overview"))


@app.route("/proposals/accept/<proposalId>", methods=['post', 'get'])
@unlocked_wallet_required
def votable_proposals_accept(proposalId):
    Node().acceptProposal(proposalId)
    LocalProposal.wasReviewed(proposalId)
    flash('Proposal (' + proposalId + ') has been accepted')
    return redirect(url_for('votable_proposals'))


@app.route("/proposals/reject/<proposalId>", methods=['post', 'get'])
@unlocked_wallet_required
def votable_proposals_reject(proposalId):
    try:
        Node().rejectProposal(proposalId)
    except Exception as e:
        pass

    LocalProposal.wasReviewed(proposalId)
    flash('Proposal (' + proposalId + ') has been rejected')
    return redirect(url_for('votable_proposals'))


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
    typeName = formClass.getTypeName()
    typeNameTitle = utils.getTitle(typeName)

    selectedParent = None
    default = None
    if parentId:
        selectedParent = utils.getComprisedParentByIdGetter(typeName)(parentId)
        default = {'parentId': parentId}

    form.init(selectedParent, default)

    # Which button was pressed?
    if findAndProcessTranslatons(form):
        return render_template_menuinfo("new.html", **locals())

    elif form.submit.data and form.validate_on_submit():
        # Create new sport
        operation = form.create()
        flash("A creation proposal for a new " +
              utils.getTitle(typeName) + " was created and will be" +
              " displayed with a relative id in the overview.")
        return redirect(url_for('overview',
                        typeName=operation['typeName'],
                        identifier=operation['id']))

    return render_template_menuinfo("new.html", **locals())


@app.route("/sport/new", methods=['post', 'get'])
@unlocked_wallet_required
@requires_node
def sport_new():
    return genericNewForm(forms.NewSportForm)


@app.route("/eventgroup/new", methods=['post', 'get'])
@app.route("/eventgroup/new/<parentId>", methods=['post', 'get'])
@unlocked_wallet_required
@requires_node
def eventgroup_new(parentId=None):
    return genericNewForm(forms.NewEventGroupForm, parentId)


@app.route("/event/new/<parentId>", methods=['post', 'get'])
@unlocked_wallet_required
@requires_node
def event_new(parentId):
    return genericNewForm(forms.NewEventForm, parentId)


@app.route("/bettingmarketgroup/new/<parentId>", methods=['post', 'get'])
@unlocked_wallet_required
@requires_node
def bettingmarketgroup_new(parentId):
    return genericNewForm(forms.NewBettingMarketGroupForm, parentId)


@app.route("/bettingmarketgrouprule/new", methods=['post', 'get'])
@unlocked_wallet_required
@requires_node
def bettingmarketgrouprule_new(parentId=None):
    return genericNewForm(forms.NewBettingMarketGroupRuleForm)


@app.route("/bettingmarket/new/<parentId>", methods=['post', 'get'])
@unlocked_wallet_required
@requires_node
def bettingmarket_new(parentId):
    return genericNewForm(forms.NewBettingMarketForm, parentId)


@app.route("/bet/new", methods=['post', 'get'])
@unlocked_wallet_required
@requires_node
def bet_new():
    return render_template_menuinfo('index.html', **locals())


def genericUpdate(formClass, selectId, removeSubmits=False):
    typeName = formClass.getTypeName()

    selectFunction = utils.getTypeGetter(typeName)
    choicesFunction = utils.getTypesGetter(typeName)

    try:
        # maybe only query the selected object, if one is preselected,
        # saves traffic currently: always query all
        parentId = None
        if selectId:
            parentId = utils.getParentTypeGetter(typeName)(selectId)

        form = forms.buildUpdateForm(typeName,
                                     choicesFunction(parentId),
                                     formClass,
                                     selectId)
    except NonScalableRequest as e:
        return redirect(url_for('overview'))
    except NodeException as e:
        flash(str(e), category='error')
        return render_template_menuinfo("update.html", **locals())

    typeNameTitle = utils.getTitle(typeName)

    if not selectId:
        if form.submit.data:
            return redirect(url_for(typeName + '_update',
                                    selectId=form.select.data))
        else:
            return render_template_menuinfo("update.html", **locals())

    # update was called with given id, make sure it exists
    try:
        if selectId:
            selectedObject = selectFunction(selectId)
    except NodeException as e:
        flash(str(e), category='error')
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

    if removeSubmits:
        # remove submit button
        # todo: disable any and all user input
        typeNameAction = 'Details of'

        for fieldName in form._fields.keys():
            field = form._fields[fieldName]

            if isinstance(field, SubmitField):
                delattr(form, fieldName)
            elif isinstance(field, FormField):
                for subfieldName in field.form._fields.keys():
                    subField = field.form._fields[subfieldName]
                    if isinstance(subField, SubmitField):
                        delattr(field.form, subfieldName)

        return render_template_menuinfo("update.html", **locals())

    else:
        typeNameAction = 'Update'

    if form.validate_on_submit():
        # user submitted, wants to change
        # all data was entered correctly, validate and update sport
        proposal = form.update(selectedObject['id'])
        flash("An update proposal  for " + utils.getTitle(typeName) +
              " (id=" + selectId + ") was created.")
        return redirect(utils.processNextArgument(
            request.args.get('next'), 'index'))

    return render_template_menuinfo("update.html", **locals())


@app.route("/sport/update", methods=['post', 'get'])
@app.route("/sport/update/<selectId>", methods=['post', 'get'])
@unlocked_wallet_required
@requires_node
def sport_update(selectId=None):
    return genericUpdate(forms.NewSportForm, selectId)


@app.route("/eventgroup/update", methods=['post', 'get'])
@app.route("/eventgroup/update/<selectId>", methods=['post', 'get'])
@unlocked_wallet_required
@requires_node
def eventgroup_update(selectId=None):
    formClass = forms.NewEventGroupForm

    return genericUpdate(formClass, selectId)


@app.route("/event/update", methods=['post', 'get'])
@app.route("/event/update/<selectId>", methods=['post', 'get'])
@unlocked_wallet_required
@requires_node
def event_update(selectId=None):
    formClass = forms.NewEventForm
    return genericUpdate(formClass, selectId)


@app.route("/bettingmarketgroup/update", methods=['post', 'get'])
@app.route("/bettingmarketgroup/update/<selectId>", methods=['post', 'get'])
@unlocked_wallet_required
@requires_node
def bettingmarketgroup_update(selectId=None):
    formClass = forms.NewBettingMarketGroupForm
    return genericUpdate(formClass, selectId)


@app.route("/bettingmarket/update", methods=['post', 'get'])
@app.route("/bettingmarket/update/<selectId>", methods=['post', 'get'])
@unlocked_wallet_required
@requires_node
def bettingmarket_update(selectId=None):
    formClass = forms.NewBettingMarketForm
    return genericUpdate(formClass, selectId)


@app.route("/bettingmarketgrouprule/update", methods=['post', 'get'])
@app.route("/bettingmarketgrouprule/update/<selectId>", methods=['post', 'get'])
@unlocked_wallet_required
@requires_node
def bettingmarketgrouprule_update(selectId=None):
    formClass = forms.NewBettingMarketGroupRuleForm
    return genericUpdate(formClass, selectId)


@app.route("/sport/details/<selectId>")
@requires_node
def sport_details(selectId):
    return genericUpdate(forms.NewSportForm, selectId, True)


@app.route("/eventgroup/details/<selectId>")
@requires_node
def eventgroup_details(selectId):
    formClass = forms.NewEventGroupForm
    return genericUpdate(formClass, selectId, True)


@app.route("/event/details/<selectId>")
@requires_node
def event_details(selectId):
    formClass = forms.NewEventForm
    return genericUpdate(formClass, selectId, True)


@app.route("/bettingmarketgroup/details/<selectId>")
@requires_node
def bettingmarketgroup_details(selectId):
    formClass = forms.NewBettingMarketGroupForm
    return genericUpdate(formClass, selectId, True)


@app.route("/bettingmarketgrouprule/details/<selectId>")
@requires_node
def bettingmarketgrouprule_details(selectId):
    formClass = forms.NewBettingMarketGroupRuleForm
    return genericUpdate(formClass, selectId, True)


@app.route("/bettingmarket/details/<selectId>")
@requires_node
def bettingmarket_details(selectId):
    formClass = forms.NewBettingMarketForm
    return genericUpdate(formClass, selectId, True)


@app.route("/event/start/<selectId>", methods=['post', 'get'])
@unlocked_wallet_required
def event_start(selectId=None):
    return redirect(url_for('overview'))


@app.route("/event/finish/<selectId>", methods=['post', 'get'])
@unlocked_wallet_required
def event_finish(selectId=None):
    return redirect(url_for('overview'))


@app.route("/bettingmarket/grade/<selectId>", methods=['post', 'get'])
@unlocked_wallet_required
def bettingmarket_grade(selectId=None):
    return redirect(url_for('overview'))


@app.route("/bettingmarketgroup/freeze/<selectId>", methods=['post', 'get'])
@unlocked_wallet_required
def bettingmarketgroup_freeze(selectId=None):
    return redirect(url_for('overview'))


# @app.route("/bettingmarketgroup/resolve/selectevent/<eventGroupId>", methods=['get'])
# @requires_node
# def bettingmarketgroup_resolve_selectevent(eventGroupId=None):
#     form = BettingMarketGroupResolveForm()
#     form.initEvents(eventGroupId)
# 
#     return render_template_menuinfo("generic.html", **locals())


@app.route("/bettingmarketgroup/resolve/selectgroup/<eventId>", methods=['get', 'post'])
@requires_node
def bettingmarketgroup_resolve_selectgroup(eventId=None):
    form = BettingMarketGroupResolveForm()

    selectedEvent = Node().getEvent(eventId)

    form.initEvents(selectedEvent['event_group_id'], eventId)
    form.event.render_kw = {"disabled": True}

    form.initGroups(selectedEvent)
#     form.bettingmarketgroup.render_kw = {'onclick': "document.getElementById('bettingMarketGroupResolveForm').submit()"}

    if form.validate_on_submit():
        return redirect(url_for('bettingmarketgroup_resolve',
                        selectId=form.bettingmarketgroup.data))

    return render_template_menuinfo("generic.html", **locals())


@app.route("/bettingmarketgroup/resolve/<selectId>", methods=['post', 'get'])
@requires_node
@unlocked_wallet_required
def bettingmarketgroup_resolve(selectId=None):
    form = BettingMarketGroupResolveForm()
    bettingMarketGroupId = selectId
    selectedBMG = Node().getBettingMarketGroup(bettingMarketGroupId)

    form.initEvents(selectedBMG.event['event_group_id'])
    form.initGroups(selectedBMG['event_id'])

    if not form.submit.data:
        form.fillMarkets(bettingMarketGroupId)

        form.event.data = selectedBMG['event_id']
        form.bettingmarketgroup.data = bettingMarketGroupId

        form.event.render_kw = {"disabled": True}
        form.bettingmarketgroup.render_kw = {"disabled": True}

        # todo: this is weird, i dont understand why data is filled
        for market in form.bettingmarkets:
            market.resolution.data = None

    if form.validate_on_submit():
        resultList = []
        for market in form.bettingmarkets:
            resultList.append([market.identifier.data, market.resolution.data])
        Node().resolveBettingMarketGroup(bettingMarketGroupId, resultList)

    return render_template_menuinfo("generic.html", **locals())


@app.route("/bettingmarketgroup/unfreeze/<selectId>", methods=['post', 'get'])
@unlocked_wallet_required
def bettingmarketgroup_unfreeze(selectId=None):
    return redirect(url_for('overview'))
