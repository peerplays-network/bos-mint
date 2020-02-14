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
import requests
import re

from . import app, forms, utils, widgets, Config
from .menu_info import clear_accounts_cache
from .forms import (
    TranslatedFieldForm,
    NewWalletForm,
    GetAccountForm,
    ReplayForm,
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
from .dataproxy_link.ping import Ping

import os
from bos_incidents import factory
from bos_incidents.exceptions import EventNotFoundException,\
    IncidentStorageLostException

from bookiesports import BookieSports
from strict_rfc3339 import InvalidRFC3339Error
from bos_mint.istring import InternationalizedString
from datetime import timedelta
from bos_incidents.format import get_reconstruct_string
from time import sleep
from threading import Thread
from datetime import datetime
from peerplays.event import Events
from bos_mint.datestring import string_to_date
from pprint import pformat, pprint
import json


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


@app.route('/account/info', methods=['GET', 'POST'])
@unlocked_wallet_required
def account_info():
    form = forms.AccountForm()

    if form.validate_on_submit():
        if Config.get("advanced_features", default=False):
            ViewConfiguration.set('synchronous_operations', 'enabled', form.synchronous_operations.data)
            Node().get_node().blocking = ViewConfiguration.get('synchronous_operations', 'enabled', False)
            message = "Synchronous operations is set to " + str(ViewConfiguration.get('synchronous_operations', 'enabled', False))
            if ViewConfiguration.get('synchronous_operations', 'enabled', False):
                message = message + " Calls are now blocking."
            flash(message)
        else:
            flash("Updating account settings is currently disabled")
    else:
        account = Node().getSelectedAccount()
        form.fill(account)
        form.synchronous_operations.data = ViewConfiguration.get('synchronous_operations', 'enabled', False)

    return render_template_menuinfo("account.html", **locals())


@app.route('/bookiesports/sync', methods=['GET', 'POST'])
@unlocked_wallet_required
def bookiesports_sync():
    if not Config.get("advanced_features", default=False):
        raise Exception("Sync currently disabled")

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
                 bookieSports.index["chain_id"] == Node().get_node().rpc.chain_params["chain_id"]):
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
            clear_accounts_cache()
            flash("Key and all underlying registered accounts imported!")
        except Exception as e:
            flash(
                'There was a problem adding the account to the wallet. ({})'.format(
                    str(e)),
                category='error')

        return redirect(url_for('overview'))

    return render_template_menuinfo('generic.html', **locals())


@app.route("/incidents/replay", methods=['GET', 'POST'])
@app.route("/incidents/replay/<filter>", methods=['GET', 'POST'])
@app.route("/incidents/replay/<filter>/<use>", methods=['GET', 'POST'])
@unlocked_wallet_required
def replay(filter=None, use="mongodb"):
    if use == "bos-auto":
        use = "mongodb"
    if not Config.get("advanced_features", False):
        abort(404)

    form = ReplayForm()
    form.chain.data = Config.get("connection", "use")
    formTitle = "Replay incidents"
    formMessages = []

    proxy_incidents = None

    if not form.back.data and form.validate_on_submit():
        if form.check.data:
            from .dataproxy_link import control
            # query dataproxy
            try:
                proxy_incidents = control.get_replayable_incidents(form.unique_string.data, form.dataproxy.data, form.chain.data, form.witness.data)

                form.replay.render_kw = {'disabled': False}

                del form.check

                formMessages.append(str(len(proxy_incidents)) + " incidents found on dataproxy")
                for _tmp in proxy_incidents:
                    if type(_tmp) == dict:
                        formMessages.append(" - " + _tmp["unique_string"] + " provider: " + _tmp["provider_info"]["name"])
                    else:
                        formMessages.append(" - " + _tmp)
            except Exception as e:
                del form.back
                flash(str(e), category="error")
        if form.replay.data:
            del form.back
            from .dataproxy_link import control
            try:
                proxy_incidents = control.replay_incidents(form.unique_string.data, form.dataproxy.data, form.chain.data, form.witness.data)

                formMessages = ["Replay has been triggered"]
                formMessages.append("")
                formMessages.append(str(len(proxy_incidents)) + " incidents found on dataproxy")
                for _tmp in proxy_incidents:
                    if type(_tmp) == dict:
                        formMessages.append(" - " + _tmp["unique_string"] + " provider: " + _tmp["provider_info"]["name"])
                    else:
                        formMessages.append(" - " + _tmp)
            except Exception as e:
                flash(str(e), category="error")
    else:
        if filter is not None:
            form.unique_string.data = filter
        form.witness.data = "All"
        del form.back

    if form.unique_string.data is not None and not form.unique_string.data.strip() == "":
        store = factory.get_incident_storage(use=use)
        incidents = list(store.get_incidents(filter_dict=dict(
            unique_string={"$regex": ".*" + form.unique_string.data + ".*"}
        )))
        if len(formMessages) > 0:
            formMessages.append("")
        formMessages.append(str(len(incidents)) + " incidents found locally for " + str(form.unique_string.data))
        for _tmp in incidents:
            formMessages.append(" - " + _tmp["unique_string"] + " provider: " + _tmp["provider_info"]["name"])

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


@app.route('/mainnet')
def mainnet():
    formMessage = "This MINT instance is connected to the peerplays mainnet (alice). Be vigilant!"
    return render_template_menuinfo('generic.html', formMessage=formMessage)


@app.route('/witnesses')
@unlocked_wallet_required
def witnesses():
    if not Config.get("advanced_features", False):
        abort(404)

    expected_version = Config.get("witnesses_versions", []).copy()

    def _forward_to_beacons():
        witnesses = Config.get("witnesses")
        responses = {}
        threads = []
        for witness in witnesses:
            def _call_beacon(_responses, _beacon, _name):
                try:
                    response = requests.get(_beacon, timeout=10)
                    if response.status_code == 200 and response.json() is not None:
                        _responses[_name] = response.json()
                    else:
                        sleep(0.2)
                        response = requests.get(_beacon, timeout=10)
                        if response.status_code == 200 and response.json() is not None:
                            _responses[_name] = response.json()
                        else:
                            _responses[_name] = "HTTP response " + str(response.status_code)
                except Exception as e:
                    try:
                        sleep(0.2)
                        response = requests.get(_beacon, timeout=10)
                        if response.status_code == 200 and response.json() is not None:
                            _responses[_name] = response.json()
                        else:
                            _responses[_name] = "HTTP response " + str(response.status_code)
                    except Exception as e:
                            _responses[_name] = "Errored, " + str(e)

            threads.append(Thread(target=_call_beacon, args=(responses, witness["url"] + "/isalive", witness["name"])))
            threads[len(threads) - 1].start()

        for i in range(len(threads)):
            threads[i].join()

        return responses

    responses = _forward_to_beacons()

    for key, value in responses.items():
        if type(value) == str:
            responses[key] = value
            continue
        ok = "NA"
        if value["queue"]["status"].get("default", None) is not None:
            ok = value["queue"]["status"]["default"]["count"]
        nok = "NA"
        if value["queue"]["status"].get("failed", None) is not None:
            nok = value["queue"]["status"]["failed"]["count"]
        scheduler = False
        if (value.get("background", None) is not None and
                value["background"].get("scheduler", None) is not None and
                value["background"]["scheduler"].get("running", None) is not None):
            scheduler = value["background"]["scheduler"]["running"]
        responses[key] = {
            "qeue": str(ok) + "/" + str(nok)
        }
        if not scheduler:
            responses[key]["scheduler"] = scheduler
        _version = (
            value["versions"]["bookiesports"] +
            "/" + value["versions"]["bos-auto"] +
            "/" + value["versions"]["bos-sync"] +
            "/" + value["versions"]["bos-incidents"] +
            "/" + value["versions"]["peerplays"]
        )
        if _version not in expected_version:
            responses[key]["deviating_versions"] = _version

    expected_version.append("<bookiesports>/<bos-auto>/<bos-sync>/<bos-incidents>/<peerplays>")
    responses["<witness_name>"] = {
        "queue": "<pending_incidents>/<failed_incidents>",
        "allowed_versions": expected_version
    }

    response_dict = {
        "time": str(datetime.now()),
        "reponses": responses
    }

    preformatted_string = json.dumps(
        response_dict,
        sort_keys=True,
        indent=4
    )

    return render_template_menuinfo('generic.html', preformatted_string=preformatted_string)


@app.route('/cancel')
@app.route('/cancel/<event_ids>')
@app.route('/cancel/<event_ids>/<chain>')
@unlocked_wallet_required
def cancel(event_ids=None, chain=None):
    if not Config.get("advanced_features", False):
        abort(404)

    if chain is None:
        chain = "beatrice"
    if event_ids is None:
        all_events = Node().getEvents("all")
        all_events = sorted(all_events, key=lambda k: k["start_time"])
        legacy_events_list = []
        legacy_events = {}
        legacy_events["details"] = []
        legacy_events["event_ids"] = ""
        for event in all_events:
            if string_to_date(event["start_time"]) < string_to_date():
                legacy_events["details"].append(
                    "event_id=" + event["id"] + "; start_time=" + event["start_time"]
                )
                legacy_events_list.append(event)

        legacy_events_list = sorted(legacy_events_list, key=lambda k: k["id"])
        for event in legacy_events_list:
            legacy_events["all_event_ids"] = legacy_events["event_ids"] + event["id"] + ","

        legacy_events["usage"] = "To cancel a specific event (or several): Dryrun with '/cancel/<comma-separated-list-of-ids>', execute with '/cancel/<comma-separated-list-of-ids>/send'"

        preformatted_string = json.dumps(
            legacy_events,
            sort_keys=True,
            indent=4
        )
    else:
        responses = []
        urls_to_call = {}
        for event_id in event_ids.split(","):
            event = Node().getEvent(event_id)
            teams = [x[1] for x in event["name"] if x[0] == 'en'][0]
            if " v " in teams:
                teams = teams.split(" v ")
            if " @ " in teams:
                teams = teams.split(" @ ")
                teams = [teams[1], teams[0]]

            id_string = event["start_time"] + "Z" \
                + '__' + [x[1] for x in event.eventgroup.sport["name"] if x[0] == 'en'][0] \
                + '__' + [x[1] for x in event.eventgroup["name"] if x[0] == 'en'][0] \
                + '__' + teams[0] \
                + '__' + teams[1]
            call = "canceled__None"

            proxies = Ping().get_status()

            for key, value in proxies.items():
                url = value["replay"] + "&manufacture=" + id_string + "__" + call
                if chain == "send":
                    url = re.sub('&only_report=True', '', url)
                urls_to_call[url] = url
            for url in urls_to_call.keys():
                response = requests.get(url, timeout=1000)
                if response.status_code == 200:
                    responses.append(requests.get(url, timeout=1000).json())

        preformatted_string = json.dumps(
            {
                "responses": responses,
                "urls_to_call": list(urls_to_call.keys())
            },
            sort_keys=True,
            indent=4
        )

    return render_template_menuinfo('generic.html', preformatted_string=preformatted_string)


@app.route('/incidents')
@app.route('/incidents/<matching>')
@app.route('/incidents/<matching>/<use>')
def show_incidents(from_date=None, to_date=None, matching=None, use="mongodb"):
    if request.args.get("matching_today", None) is not None:
        return redirect(url_for("show_incidents", matching=utils.date_to_string()[0:10]))

    if matching is not None:
        try:
            match_date = utils.string_to_date(matching[0:20])
            if from_date is None:
                from_date = match_date - timedelta(days=3)
            if to_date is None:
                to_date = match_date + timedelta(days=3)
        except InvalidRFC3339Error:
            pass

    if type(matching) == str:
        matching = matching.split(",")

    if from_date is None:
        from_date = request.args.get("from_date", None)
        if from_date is None:
            from_date = utils.date_to_string(-7)
        if type(from_date) == str:
            from_date = utils.string_to_date(from_date)
    if to_date is None:
        to_date = request.args.get("to_date", None)
        if to_date is None:
            to_date = utils.date_to_string(21)
        if type(to_date) == str:
            to_date = utils.string_to_date(to_date)

    store = None
    unresolved_events = None
    try:
        store = factory.get_incident_storage(use=use)
        unresolved_events = store.get_events(resolve=False)
    except IncidentStorageLostException:
        flash("BOS-mint could not find an incident store, or connection failed. Is a BOS-auto instance running alongside that grants access?")
        return redirect(url_for('overview'))

    events = []
    # resort for provider view
    for event in unresolved_events:
        try:
            event_scheduled = utils.string_to_date(event["id_string"][0:18])
        except InvalidRFC3339Error:
            try:
                event_scheduled = utils.string_to_date(event["id_string"][0:20])
            except InvalidRFC3339Error:
                event_scheduled = utils.string_to_date(event["id_string"][0:23])

        if event_scheduled <= to_date and event_scheduled >= from_date and\
                (matching is None or all([x.lower() in event["id_string"].lower() for x in matching])):
            store.resolve_event(event)
        else:
            continue
        for call in ["create", "in_progress", "finish", "result", "dynamic_bmgs", "canceled"]:
            try:
                incident_provider_dict = {}
                for incident in event[call]["incidents"]:
                    provider = incident["provider_info"]["name"]
                    try:
                        incident_dict = incident_provider_dict[provider]
                    except KeyError:
                        incident_provider_dict[provider] = {"incidents": [],
                                                            "replay_links": {}}
                        incident_dict = incident_provider_dict[provider]

                    incident_provider_dict[provider]["incidents"].append(incident)

                    try:
                        replay_url = Ping().get_replay_url(provider, incident, call)
                        if replay_url is not None:
                            incident_dict["replay_links"][incident["unique_string"]] = replay_url
                    except Exception as e:
                        pass

                event[call]["incidents_per_provider"] = incident_provider_dict
            except KeyError:
                pass
        event["reconstruct_string"] = get_reconstruct_string(event["id"])
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
def show_incidents_per_id(incident_id=None, call=None, use="mongodb"):
    if use == "bos-auto":
        use = "mongodb"

    store = factory.get_incident_storage(use=use)
    try:
        event = store.get_event_by_id(incident_id, resolve=True)
    except EventNotFoundException:
        return jsonify("Event not found")

    for key in list(event.keys()):
        if not (key == call or key == "id" or key == "id_string"):
            event.pop(key)

    return jsonify(event)


@app.route("/event/incidents/<selectId>", methods=['get'])
@wallet_required
def event_incidents(selectId=None):
    event = Node().getEvent(selectId)
    incident_id = (event["start_time"] + "Z-" +
                   InternationalizedString.listToDict(event.eventgroup.sport["name"])["identifier"] + "-" +
                   InternationalizedString.listToDict(event.eventgroup["name"])["identifier"])

    return redirect(url_for("show_incidents", matching=incident_id))


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
                        'title': 'Show incidents',
                        'link': 'event_incidents',
                        'icon': 'unhide'
                    }, {
                        'title': 'divider',
                    }, {
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
        if Config.get("advanced_features", default=False):
            Node().get_node().blocking = True
        else:
            flash("Automatic approval currently not supported", category="warning")

    try:
        answer = Node().broadcastPendingTransaction()

        if ViewConfiguration.get('automatic_approval', 'enabled', False):
            try:
                proposalId = answer['trx']['operation_results'][0][1]
                message = 'All pending operations have been broadcasted and the resulting proposal has been approved.'
                Node().acceptProposal(proposalId)
            except Exception as e:
                message = 'All pending operations have been broadcasted, but the resulting proposal could not be approved automatically (' + e.__class__.__name__ + ':' + str(e) + ')'
        else:
            message = 'All pending operations have been broadcasted.'
        if Node().get_node().nobroadcast:
            message += " But NoBroadcast config is set to true!"
        flash(message)
        return redirect(url_for('pending_operations'))
    except Exception as e:
        raise e
    finally:
        Node().get_node().blocking = ViewConfiguration.get('synchronous_operations', 'enabled', False)


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
    proposals = Node().getAllProposals()
    for proposal in proposals:
        operations = proposal['proposed_transaction']['operations']
        if len(operations) > 0:
            operation = operations[0][1]
            if 'betting_market_group_id' in operation.keys():
                #  print('operation', operation)
                bmgId = operation['betting_market_group_id']
                #  print('bmgId', bmgId)
                bmg = Node().get_node().rpc.get_object(bmgId)
                if isinstance(bmg, dict):
                    if 'event_id' in bmg.keys():
                        event = Node().get_node().rpc.get_object(
                            bmg['event_id'])
                        proposal['event'] = str(event)

        for operation in operations:
            operation = operation[1]
            if 'resolutions' in operation.keys():                                                                                                                                                        
                resolutions = operation['resolutions']
                for resolution in resolutions:
                    bmId = resolution[0]
                    try:
                        bm = Node().get_node().rpc.get_object(bmId)
                        if isinstance(bm, dict):
                            bmName = bm['description'][0][1]
                            resolution[0] = bmName
                    except:
                        #  These print lines are for detecting a few error cases, which I couldn't reproduce, Jemshid
                        print('-------line 864, view.py, bmId')
                        print(bmId)

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
              utils.getTitle(typeName) + " has been added to your shopping cart and will be" +
              " displayed with a relative id in the overview.")
        if operation is None:
            return redirect(url_for('overview'))
        else:
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


def genericUpdate(formClass, selectId, removeSubmits=False, details=False):
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
                                 selectId,
                                 details)

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
    if os.path.isfile("bos_mint/static/img/help/" + typeName + ".png"):
        help_file = "../../static/img/help/" + typeName + ".png"
    elif os.path.isfile(os.path.join(
            os.path.dirname(os.path.realpath(__file__)),
            'static',
            'img',
            'help',
            typeName + ".png"
    )):
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
              " (id=" + selectId + ") has been added to your shopping cart.")
        return redirect(utils.processNextArgument(
            request.args.get('next'), 'index'))

    return render_template_menuinfo("update.html", **locals())

def proposal_awaiting_approval(pendingUpdate=None):
    proposals = Node().getAllProposals()
    # Should not update proposal when the proposal of same id is pending for approval
    approve = False
    for proposal in proposals:
        for operation in proposal['proposed_transaction']['operations']:
            for d in operation[1:]:
                for k,v in d.items():
                    if k in pendingUpdate.keys() and v in pendingUpdate.values():
                       approve = True
        del operation

    return approve


@app.route("/sport/update", methods=['post', 'get'])
@app.route("/sport/update/<selectId>", methods=['post', 'get'])
@unlocked_wallet_required
def sport_update(selectId=None):
    dict1 = {'sport_id' : selectId}
    if not proposal_awaiting_approval(dict1):
        return genericUpdate(forms.NewSportForm, selectId)
    else:
        flash("Current Sport update is not allowed, Proposal is pending for approval")
        return genericUpdate(forms.SportFormDetails, selectId, True, True)


@app.route("/eventgroup/update", methods=['post', 'get'])
@app.route("/eventgroup/update/<selectId>", methods=['post', 'get'])
@unlocked_wallet_required
def eventgroup_update(selectId=None):
    dict1 = {'event_group_id' : selectId}
    if not proposal_awaiting_approval(dict1):
        formClass = forms.NewEventGroupForm
        return genericUpdate(formClass, selectId)
    else:
        flash("Current EventGroup update is not allowed, Proposal is pending for approval")
        formClass = forms.EventGroupFormDetails
        return genericUpdate(formClass, selectId, True, True) 


@app.route("/event/update", methods=['post', 'get'])
@app.route("/event/update/<selectId>", methods=['post', 'get'])
@unlocked_wallet_required
def event_update(selectId=None):
    dict1 = {'event_id' : selectId}
    if not proposal_awaiting_approval(dict1):
        formClass = forms.NewEventForm
        return genericUpdate(formClass, selectId)
    else:
        flash("Current Event update is not allowed, Proposal is pending for approval")
        formClass = forms.EventFormDetails
        return genericUpdate(formClass, selectId, True, True)


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
    dict1 = {'betting_market_group_id' : selectId}
    if not proposal_awaiting_approval(dict1):
        formClass = forms.NewBettingMarketGroupForm
        return genericUpdate(formClass, selectId)
    else:
        flash("Current BettingMarketGroup update is not allowed, Proposal is pending for approval")
        formClass = forms.BettingMarketGroupFormDetails
        return genericUpdate(formClass, selectId, True, True)

@app.route("/bettingmarket/update", methods=['post', 'get'])
@app.route("/bettingmarket/update/<selectId>", methods=['post', 'get'])
@unlocked_wallet_required
def bettingmarket_update(selectId=None):
    dict1 = {'betting_market_id' : selectId}
    if not proposal_awaiting_approval(dict1):
        formClass = forms.NewBettingMarketForm
        return genericUpdate(formClass, selectId)
    else:
        flash("Current BettingMarket update is not allowed, Proposal is pending for approval")
        formClass = forms.BettingMarketFormDetails
        return genericUpdate(formClass, selectId, True, True)

@app.route("/bettingmarketgrouprule/update", methods=['post', 'get'])
@app.route("/bettingmarketgrouprule/update/<selectId>", methods=['post', 'get'])
@unlocked_wallet_required
def bettingmarketgrouprule_update(selectId=None):
    dict1 = {'betting_market_rules_id' : selectId}
    if not proposal_awaiting_approval(dict1):
        formClass = forms.NewBettingMarketGroupRuleForm
        return genericUpdate(formClass, selectId)
    else:
        flash("Current BettingMarketGroupRule update is not allowed, Proposal is pending for approval")
        formClass = forms.BettingMarketGroupRuleFormDetails
        return genericUpdate(formClass, selectId, True, True)

@app.route("/sport/details/<selectId>")
def sport_details(selectId):
    return genericUpdate(forms.SportFormDetails, selectId, True, True)


@app.route("/eventgroup/details/<selectId>")
def eventgroup_details(selectId):
    formClass = forms.EventGroupFormDetails
    return genericUpdate(formClass, selectId, True, True)


@app.route("/event/details/<selectId>")
def event_details(selectId):
    formClass = forms.EventFormDetails
    return genericUpdate(formClass, selectId, True, True)


@app.route("/bettingmarketgroup/details/<selectId>")
def bettingmarketgroup_details(selectId):
    formClass = forms.BettingMarketGroupFormDetails
    return genericUpdate(formClass, selectId, True, True)


@app.route("/bettingmarketgrouprule/details/<selectId>")
def bettingmarketgrouprule_details(selectId):
    formClass = forms.BettingMarketGroupRuleFormDetails
    return genericUpdate(formClass, selectId, True, True)


@app.route("/bettingmarket/details/<selectId>")
def bettingmarket_details(selectId):
    formClass = forms.BettingMarketFormDetails
    return genericUpdate(formClass, selectId, True, True)


@app.route("/event/start/<selectId>", methods=['post', 'get'])
@unlocked_wallet_required
def event_start(selectId):
    if Node().getEvent(selectId).get("status") == "in_progress":
        flash("Event is already in 'in_progress' state")
    else:
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
              " has been added to your shopping cart.")
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
