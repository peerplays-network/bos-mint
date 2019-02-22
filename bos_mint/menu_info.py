# -*- coding: utf-8 -*-
import pkg_resources
from datetime import timedelta
import logging

from bos_mint import Config

from .node import Node, NodeException
from . import tostring, __VERSION__
from . import datestring

from .dataproxy_link.ping import Ping

from flask import (
    flash
)

CACHE_VERSIONS = None
CACHE_ACCOUNTS = None


def clear_accounts_cache():
    global CACHE_ACCOUNTS
    CACHE_ACCOUNTS = None


def getMenuInfo():
    info_less = Config.get("notifications", "accountLessThanCoreInfo", 1000)
    warning_less = Config.get("notifications", "accountLessThanCoreWarning", 200)

    try:
        witnessAccount = Node().getWitnessAccount()
        for balance in witnessAccount.balances:
            if balance.asset["id"] == "1.3.0":
                if float(balance) < warning_less:
                    flash("Account witness-account has only " + str(float(balance)) + " " + balance.asset["symbol"] + ", please replenish immediately", category="warning")
                elif float(balance) < info_less:
                    flash("Account witness-account has only " + str(float(balance)) + " " + balance.asset["symbol"] + ", please replenish")
    except NodeException:
        pass

    try:
        account = Node().getSelectedAccount()
        for balance in account.balances:
            if balance.asset["id"] == "1.3.0":
                if float(balance) < warning_less:
                    flash("Account " + account.name + " has only " + str(float(balance)) + " " + balance.asset["symbol"] + ", please replenish immediately", category="warning")
                elif float(balance) < info_less:
                    flash("Account " + account.name + " has only " + str(float(balance)) + " " + balance.asset["symbol"] + ", please replenish")
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

    global CACHE_VERSIONS
    if CACHE_VERSIONS is None:
        CACHE_VERSIONS = {}
        for name in ["bos-incidents", "peerplays", "bookiesports"]:
            try:
                CACHE_VERSIONS[name] = pkg_resources.require(name)[0].version
            except pkg_resources.DistributionNotFound:
                CACHE_VERSIONS[name] = "not installed"

    menuInfo = {
        'account': accountDict,
        'numberOfOpenTransactions': numberOfOpenTransactions,
        'numberOfVotableProposals': numberOfVotableProposals,
        'walletLocked': walletLocked,
        'version': __VERSION__,
        'versions': CACHE_VERSIONS
    }

    global CACHE_ACCOUNTS
    if CACHE_ACCOUNTS is None:
        CACHE_ACCOUNTS = []
        try:
            for account in Node().getAllAccountsOfWallet():
                if account['name']:
                    CACHE_ACCOUNTS.append({
                        'id': account['account'].identifier,
                        'name': account['account'].name,
                        'publicKey': account['pubkey'],
                        'toString': account['account'].identifier + ' - ' + account['account'].name})
                else:
                    CACHE_ACCOUNTS.append({
                        'id': 'None',
                        'name': 'This shouldnt happen',
                        'publicKey': 'None',
                        'toString': 'None - Error shouldnt happen' + account['pubkey']})
        except NodeException:
            pass

    menuInfo['allAccounts'] = CACHE_ACCOUNTS

    try:
        menuInfo['chain'] = {
            "name": Config.get("connection", "use"),
            "id": Node().get_node().rpc.chain_params["chain_id"],
            "block": Node().get_node().rpc.get_object("2.1.0")["head_block_number"],
            "time": Node().get_node().rpc.get_object("2.1.0")["time"] + "Z"
        }
    except Exception as e:
        menuInfo['chain'] = {
            "name": Config.get("connection", "use"),
            "id": str(e),
            "block": "-",
            "time": datestring.date_to_string()
        }

    if (datestring.string_to_date() - timedelta(seconds=30) > datestring.string_to_date(menuInfo["chain"]["time"])):
        menuInfo["chain"]["out_of_sync"] = True

    try:
        menuInfo['incidents'] = {
            "dataproxy_link": Ping().get_status()
        }
    except Exception:
        pass

    menuInfo["advanced_features"] = Config.get("advanced_features", False)

    logging.getLogger(__name__).debug("getMenuInfo done")

    return menuInfo
