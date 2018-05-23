from flask import url_for
from peerplaysbase import operationids
import os.path
from .node import Node
from . import tostring


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

    def __repr__(self, **kwargs):
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

    @property
    def id(self):
        return self.template_args['id']

    def addOperation(self, operationId, data):
        ow = OperationWidget(
            operationId=operationId,
            operationName=operationids.getOperationNameForId(operationId),
            data=data
        )
        self.template_args['operations'].append(ow)


class OperationWidget(RenderTemplateWidget):
    template = None

    def __init__(self, **kwargs):
        super(OperationWidget, self).__init__(**kwargs)

        name = operationids.getOperationNameForId(kwargs['operationId'])
        file = 'widgets' + os.sep + 'operation_' + name + '.html'

        if kwargs['operationId'] == 22:
            self.template = 'widgets' + os.sep + 'operation_proposal.html'

            # add child operations
            operation = kwargs['data']
            self.template_args['title'] = 'Proposal'
            self.template_args['listItems'] = [
                ('Fee paying account', operation['fee_paying_account']),
                ('Expiration time', operation['expiration_time'])
            ]

            for tmpOp in operation['proposed_ops']:
                self.addOperation(tmpOp['op'][0], tmpOp['op'][1])
        elif os.path.isfile('bos_mint' + os.sep + 'templates' + os.sep + file):
            self.template = file
        elif os.path.isfile('templates' + os.sep + file):
            self.template = file
        else:
            self.template = 'widgets/operation_unknown.html'

    def addOperation(self, operationId, data):
        if not self.template_args.get('operations'):
            self.template_args['operations'] = []

        ow = OperationWidget(
            operationId=operationId,
            operationName=operationids.getOperationNameForId(operationId),
            data=data
        )
        self.template_args['operations'].append(ow)


def prepareProposalsDataForRendering(proposals, accountId=None):
    tmpList = []
    for proposal in proposals:
        # ensure the parent expiration time is the shortest time
        if proposal['expiration_time'] < proposal['proposed_transaction']['expiration']:
            raise Exception('Expiration times are differing')

        tmpListItems = []
        if proposal.get('expiration_time'):
            tmpListItems.append(('Expiration time', proposal['expiration_time']))
        if proposal.get('review_period_time'):
            tmpListItems.append(('Review period time', proposal['review_period_time']))
        if proposal.get('available_active_approvals'):
            tmpListItems.append(('Available active approvals', [
                tostring.toString(x) for x in Node().getAccounts(proposal['available_active_approvals'])]))
        if proposal.get('required_active_approvals'):
            approvalAccounts = Node().getAccounts(proposal['required_active_approvals'])
            # special handling for witness account
            accountList = []
            for account in approvalAccounts:
                if account["id"] == "1.2.1":
                    for authAccount in account["active"]["account_auths"]:
                        accountList.append(
                            tostring.toString(
                                Node().getAccount(authAccount[0])
                            )
                        )
                else:
                    accountList.append(tostring.toString(x))

            tmpListItems.append(('Required approvals', accountList))

        ocw = OperationsContainerWidget(
            title='Proposal ' + proposal['id'],
            id=proposal['id'],
            listItems=tmpListItems,
            buttonNegative='Reject',
            buttonPositive='Approve',
            buttonNegativeURL=url_for('votable_proposals_reject',
                                      proposalId=proposal['id']),
            buttonPositiveURL=url_for('votable_proposals_accept',
                                      proposalId=proposal['id'])
        )

        for operation in proposal['proposed_transaction']['operations']:
            ocw.addOperation(operation[0], operation[1])

        tmpList.append(ocw)

    return tmpList


def prepareTransactionDataForRendering(transaction):
    # ensure the parent expiration time is the shortest time
    if transaction.proposal_expiration < transaction.proposal_review:
        raise Exception('Expiration times are differing')

    ocw = OperationsContainerWidget(
        title='Current transaction details',
        listItems=[
            ('Proposer', transaction.proposer),
            ('Expiration time', transaction.proposal_expiration)
        ],
        buttonNegative='Discard',
        buttonPositive='Broadcast',
        buttonNegativeURL=url_for('pending_operations_discard'),
        buttonPositiveURL=url_for('pending_operations_broadcast'),
    )

    for operation in transaction.get_parent()['operations']:
        ocw.addOperation(operation[0], operation[1])

    return ocw
