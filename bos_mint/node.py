from . import wrapper

from functools import wraps
from peerplays.account import Account
from peerplays.sport import Sport, Sports
from peerplays.eventgroup import EventGroups, EventGroup
from peerplays.event import Events, Event
from peerplays.bettingmarketgroup import BettingMarketGroup, BettingMarketGroups
from peerplays.bettingmarket import BettingMarkets, BettingMarket
from peerplays.rule import Rules, Rule
from peerplays.proposal import Proposals

from peerplays.instance import shared_peerplays_instance
from peerplays.asset import Asset
from bookied_sync.lookup import Lookup


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
        from . import utils

        self.ensureProposal()
        res = func(self, *arg, **kw)
        # investigate this
        res.__repr__()
        # the operation in the transaction must be a
        # proposal
        if utils.isProposal(res):
            if type(res) == dict:
                # extract relative identifier
                operations = utils.getProposalOperations(res)
                # last is last added
                return operations[len(operations) - 1]
            else:
                return None
        else:
            # should never happen
            raise NodeException("Received transaction is not a proposal")
        return res

    return wrapper


class Node(object):
    #: The static connection
    pendingProposal = None

    def __init__(self):
        """ This class is a singelton and makes sure that only one
            connection to the node is established and shared among
            flask threads.
        """

    def get_node(self):
        return shared_peerplays_instance()

    @proposedOperation
    def sync(self, chain_name):
        w = Lookup(peerplays_instance=self.get_node(),
                   network=chain_name,
                   proposing_account=self.getProposerAccountName(),
                   approving_account=self.getProposerAccountName())
        Lookup.proposal_buffer = Node.pendingProposal
        w.sync_bookiesports()
        return Node.pendingProposal

    def isInSync(self, chain_name):
        Lookup.data = dict()
        w = Lookup(peerplays_instance=self.get_node(), network=chain_name)
        return w.is_bookiesports_in_sync()

    def getAccount(self, name):
        try:
            return Account(name, peerplays_instance=self.get_node())
        except Exception as ex:
            raise NodeException(ex.__class__.__name__ + ": " + str(ex))

    def validateAccount(self, privateKey):
        try:
            return self.get_node().wallet.getAccountFromPrivateKey(privateKey)
        except Exception as ex:
            raise NodeException(ex.__class__.__name__ + ": " + str(ex))

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
            raise NodeException(ex.__class__.__name__ + ": " + str(ex))

    def getAccounts(self, idList):
        accounts = []
        try:
            for accountId in idList:
                accounts.append(Account(accountId,
                                        peerplays_instance=self.get_node()))
            return accounts
        except Exception as ex:
            raise NodeException(ex.__class__.__name__ + ": " + str(ex))

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
            raise NodeException(ex.__class__.__name__ + ": " + str(ex))

    def getAllAccountsOfWallet(self):
        try:
            # so far default is always active
            return self.get_node().wallet.getAccounts()
        except Exception as ex:
            raise NodeException(ex.__class__.__name__ + ": " + str(ex))

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
            raise NodeException(ex.__class__.__name__ + ": " + str(ex))

    def getSelectedAccountName(self):
        try:
            # so far default is always active
            return self.get_node().config["default_account"]
        except Exception as ex:
            raise NodeException(ex.__class__.__name__ + ": " + str(ex))

    def getAllProposals(self, accountName="witness-account"):
        try:
            return Proposals(accountName, peerplays_instance=self.get_node())
        except Exception as ex:
            raise NodeException(ex.__class__.__name__ + ": " + str(ex))

    def getPendingProposal(self):
        try:
            # so far default is pendingProposal
            return Node.pendingProposal
        except Exception as ex:
            raise NodeException(ex.__class__.__name__ + ": " + str(ex))

    def getPendingTransaction(self):
        try:
            # so far default is pendingProposal
            return Node.pendingProposal
        except Exception as ex:
            raise NodeException(ex.__class__.__name__ + ": " + str(ex))

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

    def _get_exception_message(self, ex):
        return ex.__class__.__name__ + ": " + str(ex)

    def getAsset(self, name_or_id):
        try:
            return Asset(name_or_id, peerplays_instance=self.get_node())
        except Exception as ex:
            raise NodeException(
                "Asset (id={}) could not be loaded: {}".format(name_or_id, self._get_exception_message(ex)))

    def getSport(self, name):
        try:
            # select sport
            sport = Sport(name, peerplays_instance=self.get_node())
            # create wrappe
            return wrapper.Sport(**dict(sport))
        except Exception as ex:
            raise NodeException(
                "Sport (id={}) could not be loaded: {}".format(name, self._get_exception_message(ex)))

    def getEventGroup(self, sportId):
        try:
            return EventGroup(sportId, peerplays_instance=self.get_node())
        except Exception as ex:
            raise NodeException(
                "EventGroups could not be loaded: {}".format(self._get_exception_message(ex)))

    def getSportAsList(self, name):
        try:
            sport = Sport(name, peerplays_instance=self.get_node())
            return [(sport["id"], sport["name"][0][1])]
        except Exception as ex:
            raise NodeException(
                "EventGroups could not be loaded: {}".format(self._get_exception_message(ex)))

    def getEvent(self, eventId):
        try:
            return Event(eventId, peerplays_instance=self.get_node())
        except Exception as ex:
            raise NodeException(
                "Event could not be loaded: {}".format(self._get_exception_message(ex)))

    def getBettingMarketGroup(self, bmgId):
        try:
            return BettingMarketGroup(bmgId,
                                      peerplays_instance=self.get_node())
        except Exception as ex:
            raise NodeException(
                "BettingMarketGroup could not be loaded: {}".format(self._get_exception_message(ex)))

    def getBettingMarket(self, bmId):
        try:
            return BettingMarket(bmId, peerplays_instance=self.get_node())
        except Exception as ex:
            raise NodeException(
                "BettingMarkets could not be loaded: {}".format(self._get_exception_message(ex)))

    def getBettingMarketGroupRule(self, bmgrId):
        try:
            return Rule(bmgrId, peerplays_instance=self.get_node())
        except Exception as ex:
            raise NodeException(
                "BettingMarkets could not be loaded: {}".format(self._get_exception_message(ex)))

    def getSports(self):
        try:
            return Sports(peerplays_instance=self.get_node()).sports
        except Exception as ex:
            raise NodeException("Sports could not be loaded: {}".format(self._get_exception_message(ex)))

    def getSportsAsList(self):
        try:
            sports = Sports(peerplays_instance=self.get_node()).sports
            return [(x["id"], x["name"][0][1]) for x in sports]
        except Exception as ex:
            raise NodeException("Sports could not be loaded: {}".format(self._get_exception_message(ex)))

    def getEventGroups(self, sportId):
        if not sportId:
            raise NonScalableRequest
        try:
            return EventGroups(sportId,
                               peerplays_instance=self.get_node()).eventgroups
        except Exception as ex:
            raise NodeException(
                "EventGroups could not be loaded: {}".format(self._get_exception_message(ex)))

    def getEvents(self, eventGroupId):
        if not eventGroupId:
            raise NonScalableRequest
        try:
            return Events(eventGroupId,
                          peerplays_instance=self.get_node()).events
        except Exception as ex:
            raise NodeException(
                "Events could not be loaded: {}".format(self._get_exception_message(ex)))

    def getBettingMarketGroupRules(self):
        try:
            return Rules(peerplays_instance=self.get_node()).rules
        except Exception as ex:
            raise NodeException(
                "BettingMarketGroupRules could not be loaded:{}".format(self._get_exception_message(ex)))

    def getBettingMarketGroups(self, eventId):
        if not eventId:
            raise NonScalableRequest
        try:
            return BettingMarketGroups(
                eventId,
                peerplays_instance=self.get_node()).bettingmarketgroups
        except Exception as ex:
            raise NodeException(
                "BettingMarketGroup could not be loaded: {}".format(self._get_exception_message(ex)))

    def getBettingMarkets(self, bettingMarketGroupId):
        if not bettingMarketGroupId:
            raise NonScalableRequest
        try:
            return BettingMarkets(
                bettingMarketGroupId,
                peerplays_instance=self.get_node()).bettingmarkets
        except Exception as ex:
            raise NodeException(
                "BettingMarkets could not be loaded: {}".format(self._get_exception_message(ex)))

    @proposedOperation
    def createSport(self, istrings):
        try:
            return self.get_node().sport_create(
                istrings,
                account=self.getSelectedAccountName(),
                append_to=self.getPendingProposal())
        except Exception as ex:
            raise NodeException(ex.__class__.__name__ + ": " + str(ex))

    @proposedOperation
    def createEventGroup(self, istrings, sportId):
        try:
            return self.get_node().event_group_create(istrings, sportId, account=self.getSelectedAccountName(), append_to=self.getPendingProposal())
        except Exception as ex:
            raise NodeException(ex.__class__.__name__ + ": " + str(ex))

    @proposedOperation
    def createEvent(self, name, season, startTime, eventGroupId):
        try:
            return self.get_node().event_create(name, season, startTime, eventGroupId, account=self.getSelectedAccountName(), append_to=self.getPendingProposal())
        except Exception as ex:
            raise NodeException(ex.__class__.__name__ + ": " + str(ex))

    @proposedOperation
    def createBettingMarketGroup(self, description, eventId, bettingMarketRuleId, asset):
        try:
            return self.get_node().betting_market_group_create(description, eventId, bettingMarketRuleId, asset, account=self.getSelectedAccountName(), append_to=self.getPendingProposal())
        except Exception as ex:
            raise NodeException(ex.__class__.__name__ + ": " + str(ex))

    @proposedOperation
    def createBettingMarket(self, payoutCondition, description, bettingMarketGroupId):
        try:
            return self.get_node().betting_market_create(payoutCondition, description, bettingMarketGroupId, account=self.getSelectedAccountName(), append_to=self.getPendingProposal())
        except Exception as ex:
            raise NodeException(ex.__class__.__name__ + ": " + str(ex))

    @proposedOperation
    def createBettingMarketGroupRule(self, name, description):
        try:
            return self.get_node().betting_market_rules_create(name, description, account=self.getSelectedAccountName(), append_to=self.getPendingProposal())
        except Exception as ex:
            raise NodeException(ex.__class__.__name__ + ": " + str(ex))

    @proposedOperation
    def updateSport(self, sportId, istrings):
        try:
            return self.get_node().sport_update(sportId, istrings, account=self.getSelectedAccountName(), append_to=self.getPendingProposal())
        except Exception as ex:
            raise NodeException(ex.__class__.__name__ + ": " + str(ex))

    @proposedOperation
    def updateEventGroup(self, eventGroupId, istrings, sportId):
        try:
            return self.get_node().event_group_update(eventGroupId, istrings, sportId, account=self.getSelectedAccountName(), append_to=self.getPendingProposal())
        except Exception as ex:
            raise NodeException(ex.__class__.__name__ + ": " + str(ex))

    @proposedOperation
    def updateEvent(self, eventId, name, season, startTime, eventGroupId, status):
        try:
            return self.get_node().event_update(eventId, name, season, startTime, eventGroupId, status, account=self.getSelectedAccountName(), append_to=self.getPendingProposal())
        except Exception as ex:
            raise NodeException(ex.__class__.__name__ + ": " + str(ex))

    @proposedOperation
    def updateEventStatus(self, eventId, status, scores=[]):
        try:
            return self.get_node().event_update_status(eventId, status, scores, account=self.getSelectedAccountName(), append_to=self.getPendingProposal())
        except Exception as ex:
            raise NodeException(ex.__class__.__name__ + ": " + str(ex))

    @proposedOperation
    def updateBettingMarketGroup(self, bmgId, description, eventId, rulesId, status):
        try:
            return self.get_node().betting_market_group_update(bmgId, description, eventId, rulesId, status, account=self.getSelectedAccountName(), append_to=self.getPendingProposal())
        except Exception as ex:
            raise NodeException(ex.__class__.__name__ + ": " + str(ex))

    @proposedOperation
    def updateBettingMarketGroupRule(self, bmgrId, name, description):
        try:
            return self.get_node().betting_market_rules_update(bmgrId, name, description, account=self.getSelectedAccountName(), append_to=self.getPendingProposal())
        except Exception as ex:
            raise NodeException(ex.__class__.__name__ + ": " + str(ex))

    @proposedOperation
    def updateBettingMarket(self, bmId, payout_condition, descriptions, bmgId):
        try:
            return self.get_node().betting_market_update(bmId, payout_condition, descriptions, bmgId, account=self.getSelectedAccountName(), append_to=self.getPendingProposal())
        except Exception as ex:
            raise NodeException(ex.__class__.__name__ + ": " + str(ex))

    def startEvent(self, eventId):
        return self.updateEventStatus(eventId, "in_progress")

    def freezeEvent(self, eventId):
        return self.updateEventStatus("frozen")

    def cancelEvent(self, eventId):
        return self.updateEventStatus(eventId, "canceled")

    @proposedOperation
    def freezeBettingMarketGroup(self, bmgId):
        try:
            return self.get_node().betting_market_group_update(bmgId, status="frozen", account=self.getSelectedAccountName(), append_to=self.getPendingProposal())
        except Exception as ex:
            raise NodeException(ex.__class__.__name__ + ": " + str(ex))

    @proposedOperation
    def unfreezeBettingMarketGroup(self, bmgId):
        raise Exception("Unfreezing is no longer supported, please update and select the desired status manually.")
        try:
            return self.get_node().betting_market_group_update(bmgId, status="in_play", account=self.getSelectedAccountName(), append_to=self.getPendingProposal())
        except Exception as ex:
            raise NodeException(ex.__class__.__name__ + ": " + str(ex))

    @proposedOperation
    def cancelBettingMarketGroup(self, bmgId):
        try:
            return self.get_node().betting_market_group_update(bmgId, status="canceled", account=self.getSelectedAccountName(), append_to=self.getPendingProposal())
        except Exception as ex:
            raise NodeException(ex.__class__.__name__ + ": " + str(ex))

    def discardPendingTransaction(self):
        try:
            if Node.pendingProposal:
                self.get_node().clear()
                Node.pendingProposal = []
        except Exception as ex:
            raise NodeException(ex.__class__.__name__ + ": " + str(ex))

    def broadcastPendingTransaction(self):
        try:
            if Node.pendingProposal:
                returnV = self.get_node().broadcast()
                self.get_node().clear()
                Node.pendingProposal = []
                return returnV
        except Exception as ex:
            raise NodeException(ex.__class__.__name__ + ": " + str(ex))

    def acceptProposal(self, proposalId):
        try:
            return self.get_node().approveproposal(
                [proposalId],
                self.getSelectedAccountName(),
                self.getSelectedAccountName())
        except Exception as ex:
            raise NodeException(ex.__class__.__name__ + ": " + str(ex))

    def rejectProposal(self, proposalId):
        try:
            return self.get_node().disapproveproposal(
                [proposalId],
                self.getSelectedAccountName(),
                self.getSelectedAccountName())
        except Exception as ex:
            raise NodeException(ex.__class__.__name__ + ": " + str(ex))

    @proposedOperation
    def resolveBettingMarketGroup(self, bettingMarketGroupId, resultList):
        try:
            return self.get_node().betting_market_resolve(
                bettingMarketGroupId,
                resultList,
                self.getSelectedAccountName(),
                append_to=self.getPendingProposal())
        except Exception as ex:
            raise NodeException(ex.__class__.__name__ + ": " + str(ex))
