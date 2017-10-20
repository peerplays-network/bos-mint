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


class RenderTemplateWidget(object):
    """
        Base template for every widget
        Enables the possibility of rendering a template
         inside a template with run time options
    """
    template = 'appbuilder/general/widgets/render.html'
    template_args = None

    def __init__(self, **kwargs):
        self.template_args = kwargs

    def  __repr__(self, **kwargs):  
        return self.__call__(**kwargs)   

    def __call__(self, **kwargs):
        from flask.globals import _request_ctx_stack
        ctx = _request_ctx_stack.top
        jinja_env = ctx.app.jinja_env

        template = jinja_env.get_template(self.template)
        args = self.template_args.copy()
        args.update(kwargs)
        return template.render(args)
    
class OperationsContainerWidget(RenderTemplateWidget):
    template = 'widgets/operationContainer.html'    
    
    def __init__(self, **kwargs):
        if not kwargs.get('operations'):
            kwargs['operations'] = []
        
        super(OperationsContainerWidget, self).__init__(**kwargs)
        
    def addOperation(self, operationId, data):
        ow = OperationWidget(operationId=operationId,data=data)
        self.template_args['operations'].append( ow )
        
class OperationWidget(RenderTemplateWidget):
    template = None
    
    def __init__(self, **kwargs):
        super(OperationWidget, self).__init__(**kwargs)
        
        if kwargs['operationId'] == 22:       
            self.template = 'widgets/operation_proposal.html'   
            
            # add child operations
            operation = kwargs['data']
            self.template_args['title']     = 'Proposal' 
            self.template_args['listItems'] = [ ( 'Fee', operation['fee']),
                                    ( 'Fee paying account', operation['fee_paying_account']),
                                    ( 'Expiration time', operation['expiration_time']) ]
                        
            for tmpOp in operation['proposed_ops']:
                self.addOperation( tmpOp['op'][0], tmpOp['op'][1] )
             
        elif kwargs['operationId'] == 47:
            self.template = 'widgets/operation_sport_create.html'
        elif kwargs['operationId'] == 49:            
            self.template = 'widgets/operation_event_group_create.html'
        elif kwargs['operationId'] == 51:
            self.template = 'widgets/operation_event_create.html'
        elif kwargs['operationId'] == 53:
            self.template = 'widgets/operation_betting_market_rule_create.html'
        elif kwargs['operationId'] == 55:
            self.template = 'widgets/operation_betting_market_group_create.html'
        elif kwargs['operationId'] == 56:
            self.template = 'widgets/operation_betting_market_create.html'
        
        else:
            self.template = 'widgets/operation_unknown.html'

    def addOperation(self, operationId, data):
        if not self.template_args.get('operations'):
            self.template_args['operations'] = []
        
        ow = OperationWidget(operationId=operationId,data=data)
        self.template_args['operations'].append( ow )

def prepareProposalsDataForRendering(proposals):
    tmpList = []
    for proposal in proposals:
        # ensure the parent expiration time is the shortest time
        if proposal['expiration_time'] < proposal['proposed_transaction']['expiration']:
            raise Exception('Expiration times are differing')
        
        ocw = OperationsContainerWidget(
                title='Proposal ' + proposal['id'],
                listItems=[ ( 'Expiration time', proposal['expiration_time']),
                             ( 'Review period time', proposal['review_period_time'])  ],
                buttonNegative='Reject',
                buttonPositive='Accept'
            )
        
        for operation in proposal['proposed_transaction']['operations']:
            ocw.addOperation( operation[0], operation[1] )
            
        tmpList.append(ocw)
        
    return tmpList

def prepareTransactionDataForRendering(transaction):
    # ensure the parent expiration time is the shortest time
    if transaction.proposal_expiration < transaction.proposal_review:
        raise Exception('Expiration times are differing')
    
    ocw = OperationsContainerWidget(
                title='Current transaction details',
                listItems=[ ( 'Proposer', transaction.proposer),
                            ( 'Expiration time', transaction.proposal_expiration) ],
                buttonNegative='Discard',
                buttonPositive='Broadcast'
            )
    
    tmp = transaction.get_parent().__repr__()
    for operation in transaction.get_parent()['operations']:
        ocw.addOperation( operation[0], operation[1] )
    
    return ocw

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
                         'toString': account.identifier + ' - ' + account.name },
            'numberOfOpenTransactions': len(operations),
            'numberOfVotableProposals': len(votableProposals)
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
                

class Singleton:
    """
    A non-thread-safe helper class to ease implementing singletons.
    This should be used as a decorator -- not a metaclass -- to the
    class that should be a singleton.

    The decorated class can define one `__init__` function that
    takes only the `self` argument. Also, the decorated class cannot be
    inherited from. Other than that, there are no restrictions that apply
    to the decorated class.

    To get the singleton instance, use the `Instance` method. Trying
    to use `__call__` will result in a `TypeError` being raised.

    """

    def __init__(self, decorated):
        self._decorated = decorated

    def Instance(self):
        """
        Returns the singleton instance. Upon its first call, it creates a
        new instance of the decorated class and calls its `__init__` method.
        On all subsequent calls, the already created instance is returned.

        """
        try:
            return self._instance
        except AttributeError:
            self._instance = self._decorated()
            return self._instance

    def __call__(self):
        raise TypeError('Singletons must be accessed through `Instance()`.')

    def __instancecheck__(self, inst):
        return isinstance(inst, self._decorated)
    