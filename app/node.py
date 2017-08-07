import re
from peerplays import PeerPlays
from peerplays.account import Account
from . import config


class ApiServerDown(Exception):
    pass


class Node(object):

    #: The static connection
    node = None

    def __init__(self, node=None, num_retries=1, **kwargs):
        """ This class is a singelton and makes sure that only one
            connection to the node is established and shared among
            flask threads.
        """
        if not node:
            node = config.get("witness_node", None)
        self.node = node
        self.num_retries = num_retries
        self.kwargs = kwargs
        self.kwargs["num_retries"] = num_retries

    def get_node(self):
        if not Node.node:
            Node.node = self.connect()
        return Node.node

    def connect(self):
        try:
            return PeerPlays(
                node=self.node,
                nobroadcast=config["nobroadcast"],
                **self.kwargs
            )
        except:
            raise ApiServerDown

    def account(self, name):
        return Account(name, peerplays_instance=self.get_node())

    def wallet_exists(self):
        return self.get_node().wallet.created()

    def unlock(self, pwd):
        return self.get_node().wallet.unlock(pwd)

    def locked(self):
        return self.get_node().wallet.locked()
