from peerplays import PeerPlays
from peerplays.account import Account
from peerplays.sport import Sport, Sports
from . import config
from functools import wraps
from peerplays.eventgroup import EventGroups, EventGroup
from peerplays.event import Events, Event
from peerplays.bettingmarketgroup import BettingMarketGroup, BettingMarketGroups
from peerplays.bettingmarket import BettingMarkets, BettingMarket
from peerplays.rule import Rules, Rule
from peerplays.proposal import Proposals
from app import wrapper


class NodeException(Exception):
    pass


class NonScalableRequest(NodeException):
    def __init__(self):
        NodeException.__init__(
            self,
            'This request would mean to select all objects of this type, please select a parent'
        )


class BroadcastActiveOperationsExceptions(NodeException):
    def __init__(self):
        NodeException.__init__(self, 'Broadcast or cancel the pending operations first')


class ApiServerDown(NodeException):
    pass


def proposedOperation(func):
    @wraps(func)
    def wrapper(self, *arg, **kw):
        from app import utils

        self.ensureProposal()
        res = func(self, *arg, **kw)
        # investigate this
        res.__repr__()
        # the operation in the transaction must be a
        # proposal
        if utils.isProposal(res):
            # extract relative identifier
            operations = utils.getProposalOperations(res)
            # last is last added
            return operations[len(operations) - 1]
        else:
            # should never happen
            raise NodeException("Received transaction is not a proposal")
        return res

    return wrapper


class Node(object):
    #: The static connection
    node = None
    pendingProposal = None

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
        except Exception:
            raise ApiServerDown

    def getAccount(self, name):
        try:
            return Account(name, peerplays_instance=self.get_node())
        except Exception as ex:
            raise NodeException(cause=ex)

    def validateAccount(self, privateKey):
        try:
            return self.get_node().wallet.getAccountFromPrivateKey(privateKey)
        except Exception as ex:
            raise NodeException(cause=ex)

    def ensureProposal(self):
        # deprecated code, can be removed with next peerplays update
        if not Node.pendingProposal:
            # no active proposal, create one
            Node.pendingProposal = self.get_node().proposal(
                proposer=self.getProposerAccountName())

    def getSelectedAccount(self):
        # so far default is always active
        try:
            return Account(
                self.get_node().config["default_account"],
                peerplays_instance=self.get_node()
            )
        except Exception as ex:
            raise NodeException(cause=ex)

    def getAccounts(self, idList):
        accounts = []
        try:
            for accountId in idList:
                accounts.append(Account(accountId,
                                        peerplays_instance=self.get_node()))
            return accounts
        except Exception as ex:
            raise NodeException(cause=ex)

    def selectAccount(self, accountId):
        # if there are any pending operations the user need to finish
        # that first
        if self.getPendingTransaction() and len(self.getPendingTransaction().list_operations()) > 0:
            raise BroadcastActiveOperationsExceptions
        try:
            account = Account(accountId, peerplays_instance=self.get_node())
            self.get_node().config["default_account"] = account['name']
            return account['id'] + ' - ' + account['name']
        except Exception as ex:
            raise NodeException(cause=ex)

    def getAllAccountsOfWallet(self):
        try:
            # so far default is always active
            return self.get_node().wallet.getAccounts()
        except Exception as ex:
            raise NodeException(cause=ex)

    def addAccountToWallet(self, privateKey):
        try:
            # ensure public key belongs to an account
            self.validateAccount(privateKey),
            self.get_node().wallet.addPrivateKey(privateKey)

            if self.get_node().config["default_account"] is None:
                accounts = self.getAllAccountsOfWallet()
                if len(accounts):
                    self.get_node().config["default_account"] = (
                        accounts[0]["name"]
                    )
                    self.selectAccount(accounts[0]["account"]["id"])

        except Exception as ex:
            raise NodeException(message=str(ex), cause=ex)

    def getSelectedAccountName(self):
        try:
            # so far default is always active
            return self.get_node().config["default_account"]
        except Exception as ex:
            raise NodeException(cause=ex)

    def getAllProposals(self, accountName="witness-account"):
        try:
            return Proposals(accountName, peerplays_instance=self.get_node())
        except Exception as ex:
            raise NodeException(cause=ex)

    def getPendingProposal(self):
        try:
            # so far default is pendingProposal
            return Node.pendingProposal
        except Exception as ex:
            raise NodeException(cause=ex)

    def getPendingTransaction(self):
        try:
            # so far default is pendingProposal
            return Node.pendingProposal
        except Exception as ex:
            raise NodeException(cause=ex)

    def getProposerAccountName(self):
        return self.getSelectedAccountName()

    def wallet_exists(self):
        return self.get_node().wallet.created()

    def wallet_create(self, pwd):
        return self.get_node().wallet.create(pwd)

    def unlock(self, pwd):
        return self.get_node().wallet.unlock(pwd)

    def lock(self):
        return self.get_node().wallet.lock()

    def locked(self):
        return self.get_node().wallet.locked()

    def getSport(self, name):
        try:
            # select sport
            sport = Sport(name, peerplays_instance=self.get_node())
            # create wrappe
            return wrapper.Sport(**dict(sport))
        except Exception as ex:
            raise NodeException(
                message="Sport (id={}) could not be loaded".format(name),
                cause=ex)

    def getEventGroup(self, sportId):
        try:
            return EventGroup(sportId, peerplays_instance=self.get_node())
        except Exception as ex:
            raise NodeException(
                message="EventGroups could not be loaded", cause=ex)

    def getSportAsList(self, name):
        try:
            sport = Sport(name, peerplays_instance=self.get_node())
            return [(sport["id"], sport["name"][0][1])]
        except Exception as ex:
            raise NodeException(
                message="EventGroups could not be loaded", cause=ex)

    def getEvent(self, eventId):
        try:
            return Event(eventId, peerplays_instance=self.get_node())
        except Exception as ex:
            raise NodeException(message="Event could not be loaded", cause=ex)

    def getBettingMarketGroup(self, bmgId):
        try:
            return BettingMarketGroup(bmgId,
                                      peerplays_instance=self.get_node())
        except Exception as ex:
            raise NodeException(
                message="BettingMarketGroup could not be loaded", cause=ex)

    def getBettingMarket(self, bmId):
        try:
            return BettingMarket(bmId, peerplays_instance=self.get_node())
        except Exception as ex:
            raise NodeException(
                message="BettingMarkets could not be loaded", cause=ex)

    def getBettingMarketGroupRule(self, bmgrId):
        try:
            return Rule(bmgrId, peerplays_instance=self.get_node())
        except Exception as ex:
            raise NodeException(
                message="BettingMarkets could not be loaded", cause=ex)

    def getSports(self):
        try:
            return Sports().sports
        except Exception as ex:
            raise NodeException(message="Sports could not be loaded", cause=ex)

    def getSportsAsList(self):
        try:
            sports = Sports().sports
            return [(x["id"], x["name"][0][1]) for x in sports]
        except Exception as ex:
            raise NodeException(message="Sports could not be loaded", cause=ex)

    def getEventGroups(self, sportId):
        if not sportId:
            raise NonScalableRequest
        try:
            return EventGroups(sportId,
                               peerplays_instance=self.get_node()).eventgroups
        except Exception as ex:
            raise NodeException(
                message="EventGroups could not be loaded", cause=ex)

    def getEvents(self, eventGroupId):
        if not eventGroupId:
            raise NonScalableRequest
        try:
            return Events(eventGroupId,
                          peerplays_instance=self.get_node()).events
        except Exception as ex:
            raise NodeException(
                message="Events could not be loaded", cause=ex)

    def getBettingMarketGroupRules(self):
        try:
            return Rules(peerplays_instance=self.get_node()).rules
        except Exception as ex:
            raise NodeException(
                message="BettingMarketGroupRules could not be loaded",
                cause=ex)

    def getBettingMarketGroups(self, eventId):
        if not eventId:
            raise NonScalableRequest
        try:
            return BettingMarketGroups(
                eventId,
                peerplays_instance=self.get_node()).bettingmarketgroups
        except Exception as ex:
            raise NodeException(
                message="BettingMarketGroup could not be loaded", cause=ex)

    def getBettingMarkets(self, bettingMarketGroupId):
        if not bettingMarketGroupId:
            raise NonScalableRequest
        try:
            return BettingMarkets(
                bettingMarketGroupId,
                peerplays_instance=self.get_node()).bettingmarkets
        except Exception as ex:
            raise NodeException(message="BettingMarkets could not be loaded",
                                cause=ex)

    @proposedOperation
    def createSport(self, istrings):
        try:
            return self.get_node().sport_create(
                istrings,
                account=self.getSelectedAccountName(),
                append_to=self.getPendingProposal())
        except Exception as ex:
            raise NodeException(cause=ex)

    @proposedOperation
    def createEventGroup(self, istrings, sportId):
        try:
            return self.get_node().event_group_create(istrings, sportId, self.getSelectedAccountName(), append_to=self.getPendingProposal())
        except Exception as ex:
            raise NodeException(cause=ex)

    @proposedOperation
    def createEvent(self, name, season, startTime, eventGroupId):
        try:
            return self.get_node().event_create(name, season, startTime, eventGroupId, self.getSelectedAccountName(), append_to=self.getPendingProposal())
        except Exception as ex:
            raise NodeException(cause=ex)

    @proposedOperation
    def createBettingMarketGroup(self, description, eventId, bettingMarketRuleId, asset):
        try:
            return self.get_node().betting_market_group_create(description, eventId, bettingMarketRuleId, asset, self.getSelectedAccountName(), append_to=self.getPendingProposal())
        except Exception as ex:
            raise NodeException(cause=ex)

    @proposedOperation
    def createBettingMarket(self, payoutCondition, description, bettingMarketGroupId):
        try:
            return self.get_node().betting_market_create(payoutCondition, description, bettingMarketGroupId, self.getSelectedAccountName(), append_to=self.getPendingProposal())
        except Exception as ex:
            raise NodeException(cause=ex)

    @proposedOperation
    def createBettingMarketGroupRule(self, name, description):
        try:
            return self.get_node().betting_market_rules_create(name, description, self.getSelectedAccountName(), append_to=self.getPendingProposal())
        except Exception as ex:
            raise NodeException(cause=ex)

    @proposedOperation
    def updateSport(self, sportId, istrings):
        try:
            return self.get_node().sport_update(sportId, istrings, self.getSelectedAccountName(), append_to=self.getPendingProposal())
        except Exception as ex:
            raise NodeException(cause=ex)

    @proposedOperation
    def updateEventGroup(self, eventGroupId, istrings, sportId):
        try:
            return self.get_node().event_group_update(eventGroupId, istrings, sportId, self.getSelectedAccountName(), append_to=self.getPendingProposal())
        except Exception as ex:
            raise NodeException(cause=ex, message=ex.__str__())

    @proposedOperation
    def updateEvent(self, eventId, name, season, startTime, eventGroupId):
        try:
            return self.get_node().event_update(eventId, name, season, startTime, eventGroupId, self.getSelectedAccountName(), append_to=self.getPendingProposal())
        except Exception as ex:
            raise NodeException(cause=ex, message=ex.__str__())

    @proposedOperation
    def updateBettingMarketGroup(self, bmgId, description, eventId, rulesId, freeze=False, delayBets=False):
        try:
            return self.get_node().betting_market_group_update(bmgId, description, eventId, rulesId, freeze, delayBets, self.getSelectedAccountName(), append_to=self.getPendingProposal())
        except Exception as ex:
            raise NodeException(cause=ex, message=ex.__str__())

    @proposedOperation
    def updateBettingMarketGroupRule(self, bmgrId, name, description):
        try:
            return self.get_node().betting_market_rules_update(bmgrId, name, description, self.getSelectedAccountName(), append_to=self.getPendingProposal())
        except Exception as ex:
            raise NodeException(cause=ex, message=ex.__str__())

    @proposedOperation
    def updateBettingMarket(self, bmId, payout_condition, descriptions, bmgId):
        try:
            return self.get_node().betting_market_update(bmId, payout_condition, descriptions, bmgId, self.getSelectedAccountName(), append_to=self.getPendingProposal())
        except Exception as ex:
            raise NodeException(cause=ex, message=ex.__str__())

    def discardPendingTransaction(self):
        try:
            if Node.pendingProposal:
                self.get_node().clear()
                Node.pendingProposal = []
        except Exception as ex:
            raise NodeException(cause=ex)

    def broadcastPendingTransaction(self):
        try:
            if Node.pendingProposal:
                returnV = self.get_node().broadcast()
                self.get_node().clear()
                Node.pendingProposal = []
                return returnV
        except Exception as ex:
            raise NodeException(cause=ex)

    def acceptProposal(self, proposalId):
        try:
            return self.get_node().approveproposal(
                [proposalId],
                self.getSelectedAccountName(),
                self.getSelectedAccountName())
        except Exception as ex:
            raise NodeException(cause=ex)

    def rejectProposal(self, proposalId):
        try:
            return self.get_node().disapproveproposal(
                [proposalId],
                self.getSelectedAccountName(),
                self.getSelectedAccountName())
        except Exception as ex:
            raise NodeException(cause=ex)

    def resolveBettingMarketGroup(self, bettingMarketGroupId, resultList):
        try:
            return self.get_node().betting_market_resolve(
                bettingMarketGroupId,
                resultList,
                self.getSelectedAccountName(),
                append_to=self.getPendingProposal())
        except Exception as ex:
            raise NodeException(cause=ex)
