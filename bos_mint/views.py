from flask import (
    redirect,
    request,
    session,
    flash,
    url_for,
    abort,
    jsonify,
    send_from_directory
)
from wtforms import FormField, SubmitField
from peerplays.exceptions import WalletExists

from . import app, forms, utils, widgets, Config
from .forms import (
    TranslatedFieldForm,
    NewWalletForm,
    GetAccountForm,
    ApprovalForm,
    BettingMarketGroupResolveForm,
    SynchronizationForm
)
from .models import (
    LocalProposal,
    ViewConfiguration
)
from .node import (
    Node,
    NodeException,
    BroadcastActiveOperationsExceptions
)
from .utils import (
    render_template_menuinfo,
    unlocked_wallet_required,
    wallet_required
)
import os
from bos_incidents import factory
from bos_incidents.exceptions import EventNotFoundException

from bookiesports import BookieSports


###############################################################################
# Homepage
###############################################################################


@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'),
                               'favicon.ico', mimetype='image/vnd.microsoft.icon')


@app.route('/')
def index():
    return redirect(url_for('overview'))


@app.route('/lock', methods=['GET', 'POST'])
@wallet_required
def lock():
    Node().lock()
    return redirect(url_for('overview'))


@app.route('/unlock', methods=['GET', 'POST'])
@wallet_required
def unlock():
    unlockForm = forms.UnlockForm()

    if unlockForm.validate_on_submit():
        return redirect(utils.processNextArgument(
            request.args.get('next'), 'overview'))

    return render_template_menuinfo('unlock.html', **locals())


@app.route('/account/info')
@wallet_required
def account_info():
    account = Node().getSelectedAccount()

    form = forms.AccountForm()
    form.fill(account)

    return render_template_menuinfo("account.html", **locals())


@app.route('/bookiesports/sync', methods=['GET', 'POST'])
@unlocked_wallet_required
def bookiesports_sync():
    form = SynchronizationForm()

    if form.validate_on_submit():
        flash("Blockchain has been synchronized with bookiesports and a new proposal has been created, ready to be broadcasted")
        Node().sync(Config.get("connection", "use"))
        return redirect(url_for("pending_operations"))
    else:
        form.chain_id.data = Config.get("connection", "use") + ":" + Node().get_node().rpc.chain_params["chain_id"]
        form.bookiesports_name.data = Config.get("connection", "use")
        try:
            bookieSports = BookieSports(
                chain=form.bookiesports_name.data
            )
            form.bookiesports_name.data = form.bookiesports_name.data + ":" + bookieSports.index.get("chain_id", None)

            if bookieSports.index.get("chain_id", None) is not None and\
                (bookieSports.index["chain_id"] == "*" or
                 bookieSports.index["chain_id"] == form.chain_id.data):
                if Node().isInSync(Config.get("connection", "use")):
                    form.status.data = "In sync!"
                else:
                    form.status.data = "NOT in sync! Needs syncing!"
            else:
                flash("Your bookiesports name and chain id do not match. Please make sure that the alias you use for the key connection.use within config-bos-mint.yaml matches the corresponding chain", category="error")
                form.status.data = "Your bookiesports name and chain id do not match."
                delattr(form, "submit")

        except AssertionError:
            flash("BookieSports uses the aliases " + str(BookieSports.list_chains()) + ", please use the same aliases in the key connection.use within config-bos-mint.yaml", category="error")
            delattr(form, "submit")

    return render_template_menuinfo('generic.html', **locals())


@app.route("/account/select/<accountId>", methods=['GET', 'POST'])
@wallet_required
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
def account_add():
    form = GetAccountForm()
    formTitle = "Add Account to wallet"

    if form.validate_on_submit():
        # submit checks if account exists
        try:
            Node().addAccountToWallet(form.privateKey.data)
            flash("Key and all underlying registered accounts imported!")
        except Exception as e:
            flash(
                'There was a problem adding the account to the wallet. ({})'.format(
                    str(e)),
                category='error')

        return redirect(url_for('overview'))

    return render_template_menuinfo('generic.html', **locals())


@app.route("/wallet/new", methods=['GET', 'POST'])
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
            return redirect(url_for('account_add'))
        except WalletExists as e:
            flash('There is already an open wallet.', category='error')
        except Exception as e:
            flash(e.__repr__(), category='error')

    return render_template_menuinfo('generic.html', **locals())


@app.route('/incidents')
@app.route('/incidents/<matching>')
@app.route('/incidents/<matching>/<use>')
def show_incidents(from_date=None, to_date=None, matching=None, use="mongodb"):
    if from_date is None:
        from_date = utils.string_to_date(utils.date_to_string(-14))
    if to_date is None:
        to_date = utils.string_to_date(utils.date_to_string(42))

    store = factory.get_incident_storage(use=use)

    unresolved_events = store.get_events(resolve=False)

    events = []
    # resort for provider view
    for event in unresolved_events:
        event_scheduled = utils.string_to_date(event["id_string"][0:20])
        if event_scheduled <= to_date and event_scheduled >= from_date and\
                (matching is None or matching.lower() in event["id_string"].lower()):
            store.resolve_event(event)
        else:
            continue
        for call in ["create", "in_progress", "finish", "result"]:
            try:
                incident_provider_dict = {}
                for incident in event[call]["incidents"]:
                    provider = incident["provider_info"]["name"]
                    try:
                        incident_list = incident_provider_dict[provider]
                    except KeyError:
                        incident_provider_dict[provider] = []
                        incident_list = incident_provider_dict[provider]
                    incident_provider_dict[provider].append(incident)
                event[call]["incidents_per_provider"] = incident_provider_dict
            except KeyError:
                pass
        events.append(event)

    from_date = utils.date_to_string(from_date)
    to_date = utils.date_to_string(to_date)

    if use == "mongodb":
        use = "bos-auto"

    if use == "auto":
        use = "bos-auto"

    return render_template_menuinfo('showIncidents.html', **locals())


@app.route('/incidents/details/<incident_id>/<call>')
@app.route('/incidents/details/<incident_id>/<call>/<use>')
def show_incidents_per_id(incident_id=None, call=None, use="dataproxy"):
    store = factory.get_incident_storage(use=use)
    try:
        event = store.get_event_by_id(incident_id, resolve=True)
    except EventNotFoundException:
        return jsonify("Event not found")

    # fetch them seperately, we want raw data
    incidents = store.get_incidents_by_id(incident_id, call)

    return jsonify(
        {
            "status": event.get(call, {"status": "empty"})["status"],
            "incidents": list(incidents)
        }
    )


@app.route('/overview')
@app.route('/overview/<typeName>')
@app.route('/overview/<typeName>/<identifier>')
def overview(typeName=None, identifier=None):
    # every exception will return to this view, thus this cannot break, otherwise endless loop!
    try:
        # selected ids
        selected = {}

        # same structure for all chain elements and list elements
        def buildListElements(tmpList):
            tmpList = sorted(tmpList, key=lambda k: k['toString']) 
            for entry in tmpList:
                if entry['typeName'] == 'event':
                    entry['extraLink'] = [{
                        'title': 'Start/Resume',
                        'link': 'event_start',
                        'icon': 'lightning'
                    }, {
                        'title': 'Finish',
                        'link': 'event_status_update',
                        'icon': 'flag checkered'
                    }, {
                        'title': 'Freeze',
                        'link': 'event_freeze',
                        'icon': 'snowflake'
                    }, {
                        'title': 'Cancel',
                        'link': 'event_cancel',
                        'icon': 'minus circle'
                    }]
                elif entry['typeName'] == 'bettingmarketgroup':
                    entry['extraLink'] = [{
                        'title': 'Freeze',
                        'link': 'bettingmarketgroup_freeze',
                        'icon': 'snowflake'
                    }, {
                        'title': 'Resolve',
                        'link': 'bettingmarketgroup_resolve',
                        'icon': 'money'
                    }, {
                        'title': 'Cancel',
                        'link': 'bettingmarketgroup_cancel',
                        'icon': 'minus circle'
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
        if typeName == 'bettingmarketgrouprule' and identifier:
            flash('Betting market group rules don''t have children to display')
            return redirect(url_for('overview', typeName='bettingmarketgrouprule'))

        # build reverse chain
        reverseChain = []
        if typeName and identifier:
            # if both type name and identifier are given, its the most currently
            # selected. we also want to list all the child elements then
            tmpTypeName = utils.getChildType(typeName)
        elif typeName and not identifier:
            # if only a typename is given, the user wants to have an overview of
            # all objects of that type.
            # This method is only viable for sports, since for other elements we
            # need the parent id for a scalable select.
            # Nevertheless, the API would support it if the methods are properly
            # implementing in Node.get<typeName>s(selectedParentId) for
            # selectedParentId=None
            if typeName != 'sport' and typeName != 'bettingmarketgrouprule':
                flash('Selecting all is only available for sports and rules due to' +
                      ' performance, please specify a parent id.')
                typeName = 'sport'

            tmpTypeName = typeName
        else:
            # Nothing specified? Show sports
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

            if not tmpChainElement["typeName"] == "bet":
                if isinstance(tmpChainElement, list):
                    for item in tmpChainElement:
                        reverseChain.append(item)
                else:
                    reverseChain.append(tmpChainElement)

        if tmpTypeName == 'sport':
            # sport doesnt loop through the former while,
            # thus set initial element
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
    except Exception as e:
        app.logger.exception(e)
        if 'NumRetriesReached' in str(e):
            flash("Blockchain connection might be lost: " + str(e))
        else:
            flash(str(e))
        try:
            return render_template_menuinfo('index.html')
        except Exception as e:
            app.logger.exception(e)
            abort(500)


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
            message = 'All pending operations have been broadcasted and the resulting proposal has been approved.'
            Node().acceptProposal(proposalId)
        else:
            message = 'All pending operations have been broadcasted.'
        if Node().get_node().nobroadcast:
            message += " But NoBroadcast config is set to true!"
        flash(message)
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
        containerList = [widgets.prepareTransactionDataForRendering(transaction)]
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
    except Exception:
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
def sport_new():
    return genericNewForm(forms.NewSportForm)


@app.route("/eventgroup/new", methods=['post', 'get'])
@app.route("/eventgroup/new/<parentId>", methods=['post', 'get'])
@unlocked_wallet_required
def eventgroup_new(parentId=None):
    return genericNewForm(forms.NewEventGroupForm, parentId)


@app.route("/event/new/<parentId>", methods=['post', 'get'])
@unlocked_wallet_required
def event_new(parentId):
    return genericNewForm(forms.NewEventForm, parentId)


@app.route("/bettingmarketgroup/new/<parentId>", methods=['post', 'get'])
@unlocked_wallet_required
def bettingmarketgroup_new(parentId):
    return genericNewForm(forms.NewBettingMarketGroupForm, parentId)


@app.route("/bettingmarketgrouprule/new", methods=['post', 'get'])
@unlocked_wallet_required
def bettingmarketgrouprule_new(parentId=None):
    return genericNewForm(forms.NewBettingMarketGroupRuleForm)


@app.route("/bettingmarket/new/<parentId>", methods=['post', 'get'])
@unlocked_wallet_required
def bettingmarket_new(parentId):
    return genericNewForm(forms.NewBettingMarketForm, parentId)


@app.route("/bet/new", methods=['post', 'get'])
@unlocked_wallet_required
def bet_new():
    flash("Bet creation not implemented")
    return render_template_menuinfo('index.html', **locals())


def genericUpdate(formClass, selectId, removeSubmits=False):
    typeName = formClass.getTypeName()

    selectFunction = utils.getTypeGetter(typeName)
    choicesFunction = utils.getTypesGetter(typeName)

    # maybe only query the selected object, if one is preselected,
    # saves traffic currently: always query all
    parentId = None
    if selectId:
        parentId = utils.getParentTypeGetter(typeName)(selectId)

    form = forms.buildUpdateForm(typeName,
                                 choicesFunction(parentId),
                                 formClass,
                                 selectId)

    typeNameTitle = utils.getTitle(typeName)

    if not selectId:
        if form.submit.data:
            return redirect(url_for(typeName + '_update',
                                    selectId=form.select.data))
        else:
            return render_template_menuinfo("update.html", **locals())

    # update was called with given id, make sure it exists
    if selectId:
        selectedObject = selectFunction(selectId)

    # help file present?
    if os.path.isfile("app/static/img/help/" + typeName + ".png"):
        help_file = "../../static/img/help/" + typeName + ".png"

    form.init(selectedObject)

    # user wants to add language?
    if findAndProcessTranslatons(form):
        return render_template_menuinfo("update.html", **locals())

    # first request? populate selected object
    if not form.submit.data:
        # preselect
        form.select.data = selectId
        form.fill(selectedObject)

    if removeSubmits:
        # remove submit button
        # todo: disable any and all user input
        typeNameAction = 'Details of'

        for fieldName in form._fields.copy().keys():
            # avoid mutating original set while iterating
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
def sport_update(selectId=None):
    return genericUpdate(forms.NewSportForm, selectId)


@app.route("/eventgroup/update", methods=['post', 'get'])
@app.route("/eventgroup/update/<selectId>", methods=['post', 'get'])
@unlocked_wallet_required
def eventgroup_update(selectId=None):
    formClass = forms.NewEventGroupForm

    return genericUpdate(formClass, selectId)


@app.route("/event/update", methods=['post', 'get'])
@app.route("/event/update/<selectId>", methods=['post', 'get'])
@unlocked_wallet_required
def event_update(selectId=None):
    formClass = forms.NewEventForm
    return genericUpdate(formClass, selectId)


@app.route("/event/finish", methods=['post', 'get'])
@app.route("/event/finish/<selectId>", methods=['post', 'get'])
@unlocked_wallet_required
def event_status_update(selectId=None):
    formClass = forms.EventStatusForm
    return genericUpdate(formClass, selectId)


@app.route("/bettingmarketgroup/update", methods=['post', 'get'])
@app.route("/bettingmarketgroup/update/<selectId>", methods=['post', 'get'])
@unlocked_wallet_required
def bettingmarketgroup_update(selectId=None):
    formClass = forms.NewBettingMarketGroupForm
    return genericUpdate(formClass, selectId)


@app.route("/bettingmarket/update", methods=['post', 'get'])
@app.route("/bettingmarket/update/<selectId>", methods=['post', 'get'])
@unlocked_wallet_required
def bettingmarket_update(selectId=None):
    formClass = forms.NewBettingMarketForm
    return genericUpdate(formClass, selectId)


@app.route("/bettingmarketgrouprule/update", methods=['post', 'get'])
@app.route("/bettingmarketgrouprule/update/<selectId>", methods=['post', 'get'])
@unlocked_wallet_required
def bettingmarketgrouprule_update(selectId=None):
    formClass = forms.NewBettingMarketGroupRuleForm
    return genericUpdate(formClass, selectId)


@app.route("/sport/details/<selectId>")
def sport_details(selectId):
    return genericUpdate(forms.NewSportForm, selectId, True)


@app.route("/eventgroup/details/<selectId>")
def eventgroup_details(selectId):
    formClass = forms.NewEventGroupForm
    return genericUpdate(formClass, selectId, True)


@app.route("/event/details/<selectId>")
def event_details(selectId):
    formClass = forms.NewEventForm
    return genericUpdate(formClass, selectId, True)


@app.route("/bettingmarketgroup/details/<selectId>")
def bettingmarketgroup_details(selectId):
    formClass = forms.NewBettingMarketGroupForm
    return genericUpdate(formClass, selectId, True)


@app.route("/bettingmarketgrouprule/details/<selectId>")
def bettingmarketgrouprule_details(selectId):
    formClass = forms.NewBettingMarketGroupRuleForm
    return genericUpdate(formClass, selectId, True)


@app.route("/bettingmarket/details/<selectId>")
def bettingmarket_details(selectId):
    formClass = forms.NewBettingMarketForm
    return genericUpdate(formClass, selectId, True)


@app.route("/event/start/<selectId>", methods=['post', 'get'])
@unlocked_wallet_required
def event_start(selectId):
    Node().startEvent(selectId)
    return redirect(utils.processNextArgument(
                    request.args.get('next'), 'index'))


@app.route("/event/freeze/<selectId>", methods=['post', 'get'])
@unlocked_wallet_required
def event_freeze(selectId=None):
    Node().freezeEvent(selectId)
    return redirect(utils.processNextArgument(
                    request.args.get('next'), 'index'))


@app.route("/event/cancel/<selectId>", methods=['post', 'get'])
@unlocked_wallet_required
def event_cancel(selectId=None):
    Node().cancelEvent(selectId)
    return redirect(utils.processNextArgument(
                    request.args.get('next'), 'index'))


@app.route("/bettingmarketgroup/freeze/<selectId>", methods=['post', 'get'])
@unlocked_wallet_required
def bettingmarketgroup_freeze(selectId=None):
    Node().freezeBettingMarketGroup(selectId)
    return redirect(utils.processNextArgument(
                    request.args.get('next'), 'index'))


@app.route("/bettingmarketgroup/resolve/selectgroup/<eventId>", methods=['get', 'post'])
def bettingmarketgroup_resolve_selectgroup(eventId=None):
    form = BettingMarketGroupResolveForm("Betting market group resolution - select a group to resolve")

    selectedEvent = Node().getEvent(eventId)

    form.initEvents(selectedEvent['event_group_id'], eventId)
    form.event.render_kw = {"disabled": True}

    form.initGroups(selectedEvent)
#     form.bettingmarketgroup.render_kw = {'onclick': "document.getElementById('bettingMarketGroupResolveForm').submit()"}

    if not form.submit.data:
        form.fillEvent(selectedEvent)
        form.event.render_kw = {"disabled": True}

    if form.validate_on_submit():
        return redirect(url_for('bettingmarketgroup_resolve',
                        selectId=form.bettingmarketgroup.data))

    return render_template_menuinfo("generic.html", **locals())


@app.route("/bettingmarketgroup/resolve/<selectId>", methods=['post', 'get'])
@unlocked_wallet_required
def bettingmarketgroup_resolve(selectId=None):
    form = BettingMarketGroupResolveForm()
    bettingMarketGroupId = selectId
    selectedBMG = Node().getBettingMarketGroup(bettingMarketGroupId)

    form.initEvents(selectedBMG.event['event_group_id'])
    form.initGroups(selectedBMG['event_id'])

    if not form.submit.data:
        form.fillMarkets(bettingMarketGroupId)

        form.fillEvent(Node().getEvent(selectedBMG['event_id']))
        form.event.render_kw = {"disabled": True}

        form.bettingmarketgroup.data = bettingMarketGroupId
        form.bettingmarketgroup.render_kw = {"disabled": True}

        # todo: this is weird, i dont understand why data is filled
        for market in form.bettingmarkets:
            market.resolution.data = None

    if form.validate_on_submit():
        resultList = []
        for market in form.bettingmarkets:
            resultList.append([market.identifier.data, market.resolution.data])
        Node().resolveBettingMarketGroup(bettingMarketGroupId, resultList)
        flash("An update proposal to resolve Betting market group " + str(bettingMarketGroupId) +
              " was created.")
        return redirect(utils.processNextArgument(
                        request.args.get('next'), 'index'))

    return render_template_menuinfo("generic.html", **locals())


@app.route("/bettingmarketgroup/unfreeze/<selectId>", methods=['post', 'get'])
@unlocked_wallet_required
def bettingmarketgroup_unfreeze(selectId=None):
    Node().unfreezeBettingMarketGroup(selectId)
    return redirect(utils.processNextArgument(
                    request.args.get('next'), 'index'))


@app.route("/bettingmarketgroup/unfreeze/<selectId>", methods=['post', 'get'])
@unlocked_wallet_required
def bettingmarketgroup_cancel(selectId=None):
    Node().cancelBettingMarketGroup(selectId)
    return redirect(utils.processNextArgument(
                    request.args.get('next'), 'index'))
