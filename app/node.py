import re
from peerplays import PeerPlays
from peerplays.account import Account
from peerplays.sport import Sport, Sports
from . import config
from _ast import Try

class NodeException(Exception):
    """ All exceptions thrown by the underlying data service will be wrapped with this exception
    """
    def __init__(self, message=None, cause=None):
        Exception.__init__(self)
        self.cause   = cause
        
        if message: 
            self.message = message
        else:
            self.message = 'Error in the server communication'
        if cause:
            self.message = self.message + '. ' + cause.__repr__()

class ApiServerDown(NodeException):
    pass

def proposedOperation(func):
    def wrapper(self, *arg, **kw):
        self.setProposer( self.getProposerAccountName() )
        res = func(self, *arg, **kw) 
        self.setProposer( None ) 
        return res
    return wrapper

class Node(object):
    
    #: The static connection
    node = None

    def __init__(self, url=None, num_retries=1, **kwargs):
        """ This class is a singelton and makes sure that only one
            connection to the node is established and shared among
            flask threads. 
        """
        if not url:
            self.url = config.get("witness_node", None)
        else:
            self.url = url
        self.num_retries = num_retries
        self.kwargs = kwargs
        self.kwargs["num_retries"] = num_retries

    def get_node(self):
        if not Node.node:
            self.connect()
        return Node.node

    def connect(self):
        try:
            Node.node = PeerPlays(
                node=self.url,
                nobroadcast=config["nobroadcast"],
                **self.kwargs
            )
        except:
            raise ApiServerDown

    def getAccount(self, name):
        try:
            return Account(name, peerplays_instance=self.get_node())
        except Exception as ex:
            raise NodeException(cause=ex)
        
    def getActiveAccount(self):
        try:
            # so far default is always active
            return Account(self.get_node().config["default_account"], peerplays_instance=self.get_node())
        except Exception as ex:
            raise NodeException(cause=ex)
        
    def getActiveAccountName(self):
        try:
            # so far default is always active
            return self.get_node().config["default_account"]
        except Exception as ex:
            raise NodeException(cause=ex)
            
    def getProposerAccountName(self):
        return self.getActiveAccountName()
    
    def getSport(self, name):
        try:
            return Sport(name, peerplays_instance=self.get_node())
        except Exception as ex:
            raise NodeException(message="Sport (id=" + name + ") could not be loaded", cause=ex)
        
    def getSportAsList(self, name):
        try:
            sport = Sport(name, peerplays_instance=self.get_node())
            return [ (sport["id"], sport["name"][0][1]) ] 
        except Exception as ex:
            raise NodeException(message="Sport (id=" + name + ") could not be loaded", cause=ex)
        
    def getSports(self):
        try:
            return Sports().sports
        except Exception as ex:
            raise NodeException(message="Sports could not be loaded", cause=ex)
        
    def getSportsAsList(self):
        try:
            sports = Sports().sports
            return [ (x["id"], x["name"][0][1]) for x in sports ]
        except Exception as ex:
            raise NodeException(message="Sports could not be loaded", cause=ex)
            
    @proposedOperation
    def createSport(self, istrings):
        try:
            dummy = 'Mockup: Sport created';
            return dummy
#             return self.get_node().sport_create( istrings, self.getActiveAccountName() ) 
        except Exception as ex:
            raise NodeException(cause=ex) 
        
    @proposedOperation
    def updateSport(self, sportId, istrings):
        try:
            dummy = 'Mockup: Sport updated';
            return dummy
#             return self.get_node().sport_create( istrings, self.getActiveAccountName() ) 
        except Exception as ex:
            raise NodeException(cause=ex) 

    def wallet_exists(self):
        return self.get_node().wallet.created()

    def unlock(self, pwd):
        return self.get_node().wallet.unlock(pwd)

    def locked(self):
        return self.get_node().wallet.locked()
    
    def setProposer(self, accountName):
        self.get_node().proposer = accountName
    
    
        
