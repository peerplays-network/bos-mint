from flask import redirect, flash, url_for, request, render_template
from flask_security import current_user
from functools import wraps
from datetime import datetime
from app.node import Node
from tkinter.constants import CURRENT
from peerplays.cli.proposal import proposals

# dictionary to configure types (Sport, EventGroup, etc.) 
#  title: human readable title
TYPENAMES = {
                 'sport': {'title': 'Sport' },
                 'eventgroup': {'title': 'Event group' },
                 'event': {'title': 'Event' },
                 'bettingmarketgroup': {'title': 'Betting market group' },
                 'bettingmarket': {'title': 'Betting market' },
                 'bet': {'title': 'Bet' },
               }

    
TYPE_GET_ALL = { # get list of objects for typename, containing id, typeName and toString field
      'sport' :     lambda unusedId: [ { 
                               'id' : x["id"], 
                               'typeName': 'sport',
                               'toString': x["name"][0][1] + ' (' + x["id"] + ')',
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
      'bettingmarketrule': lambda unusedId: [ { 
                                          'id' : x["id"], 
                                          'typeName': 'bettingmarketrule',
                                          'toString': x["id"] + ' - ' + x["name"][0][1]  
                                         } for x in Node().getBettingMarketRules() if x is not None ],
      'bet': lambda tmpBMGId: [  ], # not implemented yet
    }

TYPE_GET = { # get list of objects for typename, containing id, typeName and toString field
      'sport'             : lambda tmpId: Node().getSport(tmpId),
      'eventgroup'        : lambda tmpId: Node().getEventGroup(tmpId),
      'event'             : lambda tmpId: Node().getEvent(tmpId), 
      'bettingmarketgroup': lambda tmpId: Node().getBettingMarketGroup(tmpId),
      'bettingmarket'     : lambda tmpId: Node().getBettingMarket(tmpId),
      'bet'               : lambda tmpId: None, # not implemented yet
    }

# get object for typename, containing id of parent object
PARENTTYPE_GET = {
  'sport'             : lambda tmpId: None,
  'eventgroup'        : lambda tmpId: Node().getEventGroup(tmpId).sport.identifier,
  'event'             : lambda tmpId: Node().getEvent(tmpId).eventgroup.identifier,
  'bettingmarketgroup': lambda tmpId: Node().getBettingMarketGroup(tmpId).event.identifier,
  'bettingmarket'     : lambda tmpId: Node().getBettingMarket(tmpId).bettingmarketgroup.identifier,
  'bet'               : lambda tmpId: tmpId,
}

# which type does it cascade to
CHILD_TYPE = {
                 'sport': 'eventgroup',
                 'eventgroup': 'event',
                 'event': 'bettingmarketgroup',
                 'bettingmarketgroup': 'bettingmarket',
                 'bettingmarket': 'bet'
               }

# which type does it come from
PARENT_TYPE = {
                 'sport': None,
                 'eventgroup': 'sport',
                 'event': 'eventgroup',
                 'bettingmarketgroup': 'event',
                 'bettingmarket': 'bettingmarketgroup',
                 'bet': 'bettingmarket'
               }

def toString(toBeFormatted):
    if toBeFormatted.get('name') and toBeFormatted.get('id'):
        return toBeFormatted.get('name') + ' (' + toBeFormatted.get('id') + ')'
    else:
        raise Exception 

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

def getTypeGetter(typeName):
    return TYPE_GET.get(typeName)

def getTypesGetter(typeName):
    return TYPE_GET_ALL.get(typeName)
    

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


def unlocked_wallet_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        from .node import Node
        if not Node().wallet_exists():
            flash(
                "No wallet has been created yet. You need to do that and "
                "import your witness active key"
            )
            return redirect(url_for('newwallet', next=request.url))
        if Node().locked():
            flash(
                "In order to access this functionality, you need "
                "to unlock your wallet first!"
            )
            return redirect(url_for('unlock', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

def render_template_menuinfo(tmpl_name, **kwargs):
    menuInfo = getMenuInfo()
    return render_template( tmpl_name, menuInfo=menuInfo, **kwargs)

def getMenuInfo():
    account = Node().getSelectedAccount();
    
    currentTransaction = Node().getPendingTransaction()
    if not currentTransaction:
        operations = []
    else:
        operations = Node().getPendingTransaction().ops
     
    votableProposals = Node().getAllProposals()
        
    menuInfo = { 
            'account': { 'id': account.identifier, 
                         'name': account.name, 
                         'toString': toString(account) },
            'numberOfOpenTransactions': len(operations),
            'numberOfVotableProposals': len(votableProposals),
            'walletLocked': Node().locked()
                }
    
    allAccounts = []
    for account in Node().getAllAccountsOfWallet():
        if account['name']:
            allAccounts.append({ 'id': account['account'].identifier, 
                           'name': account['account'].name, 
                      'publicKey': account['pubkey'],
                       'toString': account['account'].identifier + ' - ' + account['account'].name })
        else:
            allAccounts.append({ 'id': 'None', 
                           'name': 'This shouldnt happen', 
                      'publicKey': 'None',
                       'toString': 'None - Error shouldnt happen' + account['pubkey'] })
    
    menuInfo['allAccounts'] = allAccounts
    
    return menuInfo

def processNextArgument(nextArg, default):
    if not nextArg:
        return default
    
    if nextArg.startswith('/'):
        if nextArg:
            nextWords = nextArg.split(sep='/')
            
            if nextWords[1] == 'overview':
                try:
                    return url_for('overview', typeName=nextWords[2], identifier=nextWords[3])
                except:
                    return url_for(default)
    else:
        return nextArg
             