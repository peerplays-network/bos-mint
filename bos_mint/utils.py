# -*- coding: utf-8 -*-
import pkg_resources
from flask import redirect, flash, url_for, request, render_template
from functools import wraps
from datetime import datetime, timedelta
from peerplaysbase.operationids import getOperationNameForId

from .node import Node, NodeException
from . import wrapper, tostring, __VERSION__
import strict_rfc3339
from . import config
import logging
from bos_mint import Config

# dictionary to configure types (Sport, EventGroup, etc.)
#  title: human readable title
TYPENAMES = {
    'sport': {'title': 'Sport'},
    'eventgroup': {'title': 'Event group'},
    'event': {'title': 'Event'},
    'event_status': {'title': 'Event (only status)'},
    'bettingmarketgroup': {'title': 'Betting market group'},
    'bettingmarket': {'title': 'Betting market'},
    'bet': {'title': 'Bet'},
    'bettingmarketgrouprule': {'title': 'Betting market group rule'}
}

# get list of objects for typename, containing id, typeName and toString field
TYPE_GET_ALL = {
    'sport': lambda unusedId: [
        wrapper.Sport(**x) for x in Node().getSports()
    ],
    'eventgroup': lambda tmpSportId: [
        wrapper.EventGroup(**x) for x in Node().getEventGroups(tmpSportId)
    ],
    'event': lambda tmpEventGroupId: [
        wrapper.Event(**x) for x in Node().getEvents(tmpEventGroupId)
    ],
    'event_status': lambda tmpEventGroupId: [
        wrapper.Event(**x) for x in Node().getEvents(tmpEventGroupId)
    ],
    'bettingmarketgroup': lambda tmpEventId: [
        wrapper.BettingMarketGroup(**x) for x in Node().getBettingMarketGroups(tmpEventId)
    ],
    'bettingmarket': lambda tmpBMGId: [
        wrapper.BettingMarket(**x) for x in Node().getBettingMarkets(tmpBMGId)
    ],
    'bettingmarketgrouprule': lambda unusedId: [
        wrapper.BettingMarketGroupRule(**x) for x in Node().getBettingMarketGroupRules() if x is not None
    ],
    'bet': lambda tmpBMGId: [],  # not implemented yet
}

# get list of objects for typename, containing id, typeName and toString field
TYPE_GET = {
    'sport': lambda tmpId: Node().getSport(tmpId),
    'eventgroup': lambda tmpId: Node().getEventGroup(tmpId),
    'event': lambda tmpId: Node().getEvent(tmpId),
    'event_status': lambda tmpId: Node().getEvent(tmpId),
    'bettingmarketgroup': lambda tmpId: Node().getBettingMarketGroup(tmpId),
    'bettingmarketgrouprule': lambda tmpId: Node().getBettingMarketGroupRule(tmpId),
    'bettingmarket': lambda tmpId: Node().getBettingMarket(tmpId),
    'bet': lambda tmpId: None,  # not implemented yet
}

# get object for typename, containing id of parent object
PARENTTYPE_GET = {
    'sport': lambda tmpId: None,
    'eventgroup': lambda tmpId: Node().getEventGroup(tmpId).sport.identifier,
    'event': lambda tmpId: Node().getEvent(tmpId).eventgroup.identifier,
    'event_status': lambda tmpId: Node().getEvent(tmpId).eventgroup.identifier,
    'bettingmarketgroup': lambda tmpId: Node().getBettingMarketGroup(tmpId).event.identifier,
    'bettingmarketgrouprule': lambda tmpId: None,
    'bettingmarket': lambda tmpId: Node().getBettingMarket(tmpId).bettingmarketgroup.identifier,
    'bet': lambda tmpId: tmpId,
}

# which type does it cascade to
CHILD_TYPE = {
    'sport': 'eventgroup',
    'eventgroup': 'event',
    'event': 'bettingmarketgroup',
    'event_status': 'bettingmarketgroup',
    'bettingmarketgroup': 'bettingmarket',
    'bettingmarketgrouprule': None,
    'bettingmarket': 'bet'
}

# which type does it come from
PARENT_TYPE = {
    'sport': None,
    'eventgroup': 'sport',
    'event': 'eventgroup',
    'bettingmarketgroup': 'event',
    'bettingmarketgrouprule': None,
    'bettingmarket': 'bettingmarketgroup',
    'bet': 'bettingmarket'
}

TYPENAME_TO_NEWOP_MAP = {
    'sport': 'sport_create',
    'eventgroup': 'event_group_create',
    'event': 'event_create',
    'event_status': None,
    'bettingmarketgroup': 'betting_market_group_create',
    'bettingmarketgrouprule': 'betting_market_rules_create',
    'bettingmarket': 'betting_market_create',
    'bet': 'bet_create',
}

TYPENAME_TO_UPDATEOP_MAP = {
    'sport': 'sport_update',
    'eventgroup': 'event_group_update',
    'event': 'event_update',
    'event_status': 'event_update_status',
    'bettingmarketgroup': 'betting_market_group_update',
    'bettingmarketgrouprule': 'betting_market_rules_update',
    'bettingmarket': 'betting_market_update'
}

UPDATEOP_TO_TYPENAME_MAP = {
    'sport_update': 'sport',
    'event_group_update': 'eventgroup',
    'event_update': 'event',
    'event_update_status': 'event_status',
    'betting_market_group_update': 'bettingmarketgroup',
    'betting_market_rules_update': 'bettingmarketgrouprule',
    'betting_market_update': 'bettingmarket',
    'betting_market_group_resolve': 'bettingmarketgroup'
}


def filterOnlyAllowed(enumClazz, currentStatus):
    allowed = config.get("allowed_transitions", {}).get(enumClazz.__name__, {})

    return [(x, x) for x in enumClazz.options if "COUNT" not in x and (x in allowed.get(currentStatus, []) or x == currentStatus)]


def toString(toBeFormatted):
    raise Exception


def getComprisedParentByIdGetter(typeName):
    def doGet(parentId):
        # unifies objects on the blockchain and in the cache
        if parentId and parentId.startswith('0.0'):
            return getParentByIdFromPendingProposalGetter(typeName)(parentId)
        else:
            return getParentByIdGetter(typeName)(parentId)

    return doGet


def getParentByIdFromPendingProposalGetter(typeName):
    parentTypeName = PARENT_TYPE.get(typeName)

    def doGet(parentId):
        bufferedObjects = getProposalOperations(Node().get_node().tx())

        for bufferedObject in bufferedObjects:
            if bufferedObject['typeName'] == parentTypeName\
                    and bufferedObject['id'] == parentId:
                return bufferedObject

        raise NodeException("There was no creation operation found for a " +
                            PARENT_TYPE.get(typeName) + " with identifier=" +
                            str(parentId))

    return doGet


def getParentByIdGetter(typeName):
    parentTypeName = PARENT_TYPE.get(typeName)
    if parentTypeName:
        return TYPE_GET.get(parentTypeName)

    return None


def getChildType(typeName):
    return CHILD_TYPE.get(typeName)


def getParentType(typeName):
    return PARENT_TYPE.get(typeName)


def getParentTypeGetter(typeName):
    return PARENTTYPE_GET.get(typeName)


def getComprisedParentTypeGetter(typeName):
    def doGet(selectedId):
        # unifies objects on the blockchain and in the cache
        if selectedId and selectedId.startswith('0.0'):
            bufferedObjects = getProposalOperations(Node().get_node().tx())
            for bufferedObject in bufferedObjects:
                if bufferedObject['id'] == selectedId:
                    return bufferedObject['parentId']
            else:
                return selectedId
        else:
            return getParentTypeGetter(typeName)(selectedId)

    return doGet


def getTypeGetter(typeName):
    return TYPE_GET.get(typeName)


def getTypesGetter(typeName):
    return TYPE_GET_ALL.get(typeName)


def getComprisedTypesGetter(typeName):

    def doGet(parentId):
        # unifies objects on the blockchain and in the cache
        if parentId and parentId.startswith('0.0'):
            get1 = []
        else:
            get1 = getTypesGetter(typeName)(parentId)

        get2 = getTypesFromPendingProposalGetter(typeName)(parentId)

        # allow cache to override
        bufferDict = {item['id']: item for item in get1 + get2}
        return bufferDict.values()

    return doGet


def getTypesFromPendingProposalGetter(typeName):
    def doGet(parentId):
        inBuffer = []

        bufferedObjects = getProposalOperations(Node().get_node().tx())

        for bufferedObject in bufferedObjects:
            if bufferedObject['typeName'] == typeName and\
                    (not parentId or bufferedObject['parentId'] == parentId or not bufferedObject['parentId']):
                inBuffer.append(bufferedObject)

        return inBuffer

    return doGet


def getTitle(typeName):
    # insert configurable translation here
    return TYPENAMES[typeName]['title']


def strfdelta(time, fmt):
    if not hasattr(time, "days"):  # dirty hack
        now = datetime.now()
        if isinstance(time, str):
            time = datetime.strptime(time, '%Y-%m-%dT%H:%M:%S')
        time = abs(now - time)

    d = {"days": time.days}
    d["hours"], rem = divmod(time.seconds, 3600)
    d["minutes"], d["seconds"] = divmod(rem, 60)
    return fmt.format(**d)


def wallet_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not Node().wallet_exists():
            flash(
                "No wallet has been created yet. You need to do that and "
                "import your witness active key"
            )
            return redirect(url_for('newwallet', next=request.url))
        return f(*args, **kwargs)
    return decorated_function


def unlocked_wallet_required(f):
    @wraps(f)
    @wallet_required
    def decorated_function(*args, **kwargs):
        if Node().locked():
            flash(
                "In order to access this functionality, you need "
                "to unlock your wallet first!"
            )
            return redirect(url_for('unlock', next=request.url))
        return f(*args, **kwargs)
    return decorated_function


def render_template_menuinfo(tmpl_name, **kwargs):
    """
    If there is a general error in rendering, simply return a 500 error.
    Must be robust to connection lost.

    :param tmpl_name: name of the template to be rendered
    :type tmpl_name: str
    """
    menuInfo = getMenuInfo()
    return render_template(tmpl_name, menuInfo=menuInfo, **kwargs)


def getMenuInfo():
    logging.getLogger(__name__).debug("getMenuInfo init")
    try:
        account = Node().getSelectedAccount()
        accountDict = {
            'id': account.identifier,
            'name': account.name,
            'toString': tostring.toString(account)}
    except NodeException:
        try:
            any_account = len(Node().getAllAccountsOfWallet()) > 0
        except Exception:
            any_account = False
        if any_account:
            accountDict = {'id': '-', 'name': '-', 'toString': 'Please select an account'}
        else:
            accountDict = {'id': '-', 'name': '-', 'toString': 'Please add an account'}

    numberOfOpenTransactions = 0
    try:
        currentTransaction = Node().getPendingTransaction()
        if currentTransaction:
            numberOfOpenTransactions = len(Node().getPendingTransaction().ops)
    except NodeException:
        pass

    numberOfVotableProposals = 0
    try:
        numberOfVotableProposals = len(Node().getAllProposals())
    except NodeException:
        pass

    walletLocked = True
    try:
        walletLocked = Node().locked()
    except Exception:
        pass

    versions = {}
    for name in ["bos-incidents", "peerplays", "bookiesports"]:  # "bos-auto", 
        try:
            versions[name] = pkg_resources.require(name)[0].version
        except pkg_resources.DistributionNotFound:
            versions[name] = "not installed"

    menuInfo = {
        'account': accountDict,
        'numberOfOpenTransactions': numberOfOpenTransactions,
        'numberOfVotableProposals': numberOfVotableProposals,
        'walletLocked': walletLocked,
        'version': __VERSION__,
        'versions': versions
    }

    allAccounts = []
    try:
        for account in Node().getAllAccountsOfWallet():
            if account['name']:
                allAccounts.append({
                    'id': account['account'].identifier,
                    'name': account['account'].name,
                    'publicKey': account['pubkey'],
                    'toString': account['account'].identifier + ' - ' + account['account'].name})
            else:
                allAccounts.append({
                    'id': 'None',
                    'name': 'This shouldnt happen',
                    'publicKey': 'None',
                    'toString': 'None - Error shouldnt happen' + account['pubkey']})
    except NodeException:
        pass
    menuInfo['allAccounts'] = allAccounts

    menuInfo['chain'] = {
        "name": Config.get("connection", "use"),
        "id": Node().get_node().rpc.chain_params["chain_id"]
    }

    logging.getLogger(__name__).debug("getMenuInfo done")

    return menuInfo


def processNextArgument(nextArg, default):
    if not nextArg:
        return url_for(default)

    if nextArg.startswith('/'):
        if nextArg:
            nextWords = nextArg.split(sep='/')

            if nextWords[1] == 'overview':
                try:
                    return url_for('overview',
                                   typeName=nextWords[2],
                                   identifier=nextWords[3])
                except Exception:
                    return url_for(default)
    else:
        return nextArg


def isProposal(res):
    if type(res).__name__ == "ProposalBuilder":
        return True
    else:
        return res['operations'][0][0] == 22


def getProposalOperations(tx):
    convertedOperations = []

    if tx.get('operations', None):
        if isProposal(tx):
            # its a proposal, proceed
            for idx, operation in enumerate(
                tx['operations'][0][1]['proposed_ops']
            ):
                operation = operation['op']
                operationName = getOperationNameForId(operation[0])
                typeName = 'unknown'
                for tmpTypeName, newOpName in TYPENAME_TO_NEWOP_MAP.items():
                    if newOpName == operationName:
                        typeName = tmpTypeName

                typeName = UPDATEOP_TO_TYPENAME_MAP.get(operationName, typeName)

                if typeName == 'unknown':
                    raise Exception
                # this is a hack. proper id construction __must__ be
                # provided by backend
                operationId = '0.0.' + str(idx)
                tmpData = operation[1].copy()
                tmpData.update({'operationName': operationName,
                                'operationId': operationId})

                bufferedObject = wrapper.mapOperationToObject(
                    typeName, tmpData)
                convertedOperations.append(bufferedObject)

    return convertedOperations


def date_to_string(date_object=None):
    """ rfc3339 conform string represenation of a date
        can also be given as str YYYY-mm-dd HH:MM:SS """
    if type(date_object) == int:
        if date_object < 365:
            date_object = datetime.utcnow() + timedelta(days=date_object)
        else:
            date_object = datetime.utcfromtimestamp(date_object)
    if type(date_object) == float:
        date_object = datetime.utcfromtimestamp(date_object)
    if type(date_object) == str:
        try:
            date_object = datetime.strptime(date_object + "+0000",
                                                     '%Y-%m-%d %H:%M:%S%z')
        except ValueError:
            date_object = string_to_date(date_object)
    if not date_object:
        return strict_rfc3339.now_to_rfc3339_utcoffset()
    else:
        return strict_rfc3339.timestamp_to_rfc3339_utcoffset(
            date_object.timestamp())


def string_to_date(date_string):
    """ assumes rfc3339 conform string and creates date object """
    if type(date_string) == str:
        if len(date_string) == 8:
            date_string = date_string[0:4] + "-" + date_string[4:6] + "-" + date_string[6:8] + "T00:00:00Z"
        return datetime.utcfromtimestamp(
            strict_rfc3339.rfc3339_to_timestamp(date_string))
    raise Exception("Only string covnersion supported")

