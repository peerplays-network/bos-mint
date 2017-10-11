import re
from peerplays import PeerPlays
from peerplays.account import Account
from peerplays.sport import Sport
from . import config
from _ast import Try

class NodeException(Exception):
    """ All exceptions thrown by the underlying data service will be wrapped with this exception
    """
    def __init__(self, message=None, cause=None):
        Exception.__init__(self)
        self.cause   = cause
        self.message = 'Error in the server communication'
        
        if message: 
            self.message = self.message + ': ' + message
        if cause:
            self.message = self.message + '. ' + cause.__class__.__name__ 

class ApiServerDown(NodeException):
    pass

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
    
    def getSport(self, name):
        try: 
            return Sport(name, peerplays_instance=self.get_node())
        except Exception as ex:
            raise NodeException(cause=ex)

    def wallet_exists(self):
        return self.get_node().wallet.created()

    def unlock(self, pwd):
        return self.get_node().wallet.unlock(pwd)

    def locked(self):
        return self.get_node().wallet.locked()
