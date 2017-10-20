import re

from flask import current_app, url_for
from flask_wtf import FlaskForm
from wtforms import (
    TextField,
    PasswordField,
    ValidationError,
    StringField,
    BooleanField,
    SubmitField,
    TextAreaField,
    HiddenField,
    SelectField,
    IntegerField,
    FieldList,
    DateTimeField,
    FormField
)
from wtforms.validators import (
    Required,
    DataRequired,
    Email,
    Length,
    Regexp,
    EqualTo,
    Optional,
    NumberRange
)
from app.models import InternationalizedString, LanguageNotFoundException
from app.node import Node
import datetime
from app import views, utils
from peerplays.event import Event
from peerplays.bettingmarketgroup import BettingMarketGroup
from peerplays.eventgroup import EventGroup

def selectDictToList(sourceDictionary):
    return [ (x['id'], x['toString']) for x in sourceDictionary ]
    
def buildUpdateForm(typeName, selectChoices, newFormClass, selected=None):
    # All objects have their own Form for their creation. This reuses those forms and adds 
    # a selection field
    class _UpdateForm(FlaskForm):
        pass
    
    selectChoices = selectDictToList(selectChoices)

    # select is the preselected default. if set, choice field gets disabled
    if not selected:
        select = SelectField(label=utils.getTitle(typeName), validators=[DataRequired()], choices=selectChoices)
    else:
        select = SelectField(label=utils.getTitle(typeName), validators=[DataRequired()], choices=selectChoices, render_kw={"disabled": True})
    
    if selected:   
        select.data = selected
        
    setattr(_UpdateForm, 'select', select)
    
    # readjust creation counter for display ordering of fields
    baseCounter = select.creation_counter;
    
    for idx, entry in enumerate(newFormClass.__dict__.items()):
        if not entry[0].startswith('_'):
            if (not selected and entry[0].startswith('submit')) or selected:
                entry[1].creation_counter = baseCounter + idx + 1
                setattr(_UpdateForm, entry[0], entry[1]) 
    
    form = _UpdateForm()
    return form


class UnlockPassword(object):
    def __init__(self, message="Invalid password to unlock the wallet!"):
        self.message = message

    def __call__(self, form, field):
        from .node import Node
        from peerplays.wallet import NoWalletException, WrongMasterPasswordException
        try:
            Node().unlock(field.data)
        except WrongMasterPasswordException:
            raise ValidationError(self.message)
        except Exception as e:
            raise ValidationError(str(e))

validators = {
    'email': [
        Required(),
        Email(),
    ],
    'password': [
        Required(),
        Length(min=6, max=50),
        EqualTo('password_confirm', message='Passwords must match'),
        Regexp(r'[A-Za-z0-9@#$%^&+=]',
               message='Password contains invalid characters')
    ],
    'unlock': [
        UnlockPassword()
    ]
}

class InternationalizedStringForm(FlaskForm):
    country = SelectField("Language", validators=[DataRequired()], choices=InternationalizedString.getChoices())
    text    = StringField('Text', validators=[DataRequired()],)
    
class TranslatedFieldForm(FlaskForm):
    translations = FieldList(FormField(InternationalizedStringForm, label=""), min_entries=1, label="")
    addLanguage  = SubmitField("Add translation")
    
    def fill(self, translationsList):
        # empty the fieldlist
        while len(self.translations) > 0:
            self.translations.pop_entry()
            
        for country,text in translationsList:
            try:
                lng = InternationalizedString( country, text )
            except LanguageNotFoundException:
                # append an entry indicating the unknown language
                lng = InternationalizedString( InternationalizedString.UNKNOWN, country + " - " + text )

            # append entry to a FieldList creates forms from dictionary!                            
            self.translations.append_entry( lng.getForm() )
    
class UnlockForm(FlaskForm):
    password = PasswordField('Password', validators['unlock'])
    submit = SubmitField("Unlock wallet")
    
class NewWalletForm(FlaskForm):
    password_confirm = PasswordField('Password', validators=[ DataRequired() ])
    password = PasswordField('Confirm password', validators['password'])
    submit = SubmitField("Create new wallet")
    
class GetAccountForm(FlaskForm):
    name     = TextField('Name', validators=[Optional()])
    password = PasswordField('Password', validators=[Optional()])
    role     = TextField('Role', validators=[Optional()])
    
    privateKey     = TextField('Private Key (will be calculated from above information if not given)', validators=[Optional()])
    submit = SubmitField("Login")

    def validate(self):
        if not FlaskForm.validate(self):
            return False
        if self.name.data and self.password.data and self.role.data:
            from peerplaysbase.account import PasswordKey 
            pkey = PasswordKey(self.name.data, self.password.data, self.role.data)
            self.privateKey.data = pkey.get_private_key()
            
        if self.privateKey.data:
            try:
                Node().validateAccount(self.privateKey.data),
                return True
            except Exception:
                self.privateKey.errors.append("No account connected to this private key")
                return False
        else:
            return False
            
class NewSportForm(FlaskForm):
    name   = FormField(TranslatedFieldForm)
    submit = SubmitField("Submit")
    
    @classmethod
    def getTypeName(cls):
        return 'sport'
    
    def init(self, selectedObject, defaultSelectedId=None):
        pass
        
    def fill(self, selectedObject):
        self.name.fill( selectedObject['name'] )
        
    def create(self):
        return Node().createSport( InternationalizedString.parseToList(self.name.translations) )
        
    def update(self, selectedId):
        return Node().updateSport( selectedId, InternationalizedString.parseToList(self.name) )

class NewEventGroupForm(FlaskForm):
    sport  = SelectField("Sport", validators=[DataRequired()], choices=Node().getSportsAsList())
    name   = FormField(TranslatedFieldForm)
    submit = SubmitField("Submit")
    
    @classmethod
    def getTypeName(cls):
        return 'eventgroup'
    
    def init(self, selectedObject, default=None):
        if default:
            self.sport.data = default['parentId']
        
    def fill(self, selectedObject):
        self.sport.data = selectedObject.sport['id']
        self.name.fill( selectedObject['name'] )
        
    def create(self):
        return Node().createEventGroup( InternationalizedString.parseToList(self.name), self.sport.data )
        
    def update(self, selectedId):
        return Node().updateEventGroup( selectedId, InternationalizedString.parseToList(self.name), self.sport.data )
        
    
class NewEventForm(FlaskForm):
    eventgroup = SelectField("Event group", validators=[DataRequired()], choices=None)
    name   = FormField(TranslatedFieldForm, label="Name")
    season = FormField(TranslatedFieldForm, label="Season")
    start  = DateTimeField("Start", format='%Y-%m-%d %H:%M:%S', default=datetime.datetime.now(), validators=[DataRequired()])
    submit = SubmitField("Submit")
    
    @classmethod
    def getTypeName(cls):
        return 'event'
    
    def init(self, selectedObject, default=None):
        sportId = None
        if isinstance( selectedObject, EventGroup ):
            sportId = selectedObject['sport_id']
        else:
            sportId = selectedObject.eventgroup.sport['id']
            
        # choices need to be filled at all times
        self.eventgroup.choices = selectDictToList(utils.getTypesGetter('eventgroup')(sportId))
        if default:
            self.eventgroup.data = default['parentId']
        
    def fill(self, selectedObject):
        self.eventgroup.data = selectedObject.eventgroup['id']
        self.name.fill( selectedObject['name'] )
        self.season.fill( selectedObject['season'] )
        
    def create(self):
        return Node().createEvent(InternationalizedString.parseToList(self.name), 
                                  InternationalizedString.parseToList(self.season),
                                  self.start.data,
                                  self.eventgroup.data )
        
    def update(self, selectedId):
        return Node().updateEvent(selectedId, 
                                  InternationalizedString.parseToList(self.name), 
                                  InternationalizedString.parseToList(self.season),
                                  self.start.data,
                                  self.eventgroup.data)
    
class NewBettingMarketGroupForm(FlaskForm):
    event = SelectField("Event", validators=[DataRequired()], choices=None)
    description   = FormField(TranslatedFieldForm)
    bettingmarketrule = SelectField("Betting market rule", validators=[DataRequired()], choices=selectDictToList(utils.getTypesGetter('bettingmarketrule')(None)))
    asset = TextField(label='Asset', render_kw={'disabled': True})
    submit = SubmitField("Submit")
    
    @classmethod
    def getTypeName(cls):
        return 'bettingmarketgroup'
    
    def init(self, selectedObject, default=None):
        # choices need to be filled at all times
        eventGroupId = None
        if isinstance( selectedObject, Event ):
            eventGroupId = selectedObject['event_group_id']
        else:
            eventGroupId = selectedObject.event['event_group_id']
            
        self.event.choices = selectDictToList(utils.getTypesGetter('event')(eventGroupId))
        if default:
            self.event.data = default['parentId']
            
        self.asset.data = 'PPY'
        
    def fill(self, selectedObject):
        self.event.data    = selectedObject['event_id']
        self.bettingmarketrule.data = selectedObject['rules_id']
        self.description.fill( selectedObject['description'] )
        
    def create(self):
        return Node().createBettingMarketGroup(InternationalizedString.parseToList(self.description), 
                                               self.event.data,
                                               self.bettingmarketrule.data, 
                                               self.asset.data)
        
    def update(self, selectedId):
        return Node().updateBettingMarketGroup(selectedId, 
                                  InternationalizedString.parseToList(self.description), 
                                  self.event.data,
                                  self.bettingmarketrule.data)
    
class NewBettingMarketForm(FlaskForm):
    bettingmarketgroup = SelectField("Betting market group", validators=[DataRequired()], choices=None)
    description     = FormField(TranslatedFieldForm, label="Description")
    payoutCondition = FormField(TranslatedFieldForm, label="Payout condition")
    submit = SubmitField("Submit")
    
    @classmethod
    def getTypeName(cls):
        return 'bettingmarket'
    
    def init(self, selectedObject, default=None):
        eventId = None
        if isinstance( selectedObject, BettingMarketGroup ):
            eventId = selectedObject['event_id']
        else:
            eventId = selectedObject.bettingmarketgroup['event_id']
            
        self.bettingmarketgroup.choices = selectDictToList(
            utils.getTypesGetter('bettingmarketgroup')(eventId))
        if default:
            self.bettingmarketgroup.data = default['parentId']
        
    def fill(self, selectedObject):
        self.bettingmarketgroup.data    = selectedObject['group_id']
        self.payoutCondition.fill( selectedObject['payout_condition'] )
        self.description.fill( selectedObject['description'] )
        
    def create(self):
        return Node().createBettingMasrket(InternationalizedString.parseToList(self.payoutCondition),
                                  InternationalizedString.parseToList(self.description),  
                                  self.bettingmarketgroup.data)
        
    def update(self, selectedId):
        return Node().updateBettingMarket(selectedId, 
                                  InternationalizedString.parseToList(self.payoutCondition),
                                  InternationalizedString.parseToList(self.description),  
                                  self.bettingmarketgroup.data)
    
# class OperationForm(FlaskForm):
#     name  = StringField(label='Name', render_kw = { 'disabled' : True }) 
#     
# class OperationsContainerForm(FlaskForm):
# #     submit     = SubmitField("Broadcast")
#     pass
        
class AmountForm(FlaskForm):
    symbol = TextField(label='Asset', validators=[DataRequired()], render_kw={'disabled' : True})
    
class AccountForm(FlaskForm):
    id   = TextField(label='Id', validators=[DataRequired()], render_kw={'disabled' : True})
    name = TextField(label='Name', validators=[DataRequired()], render_kw={'disabled' : True})
    membershipExpirationDate = TextField(label='Membership expiration', validators=[DataRequired()], render_kw={'disabled' : True})
    
    balances = FieldList(FormField(AmountForm, label=''), label='Balances', min_entries=0)
    
    def fill(self, account):
        self.id.data = account['id']
        self.name.data = account['name']
        self.membershipExpirationDate.data = account['membership_expiration_date']
        
        for balance in account.balances:
            tmpForm = AmountForm()
            tmpForm.symbol  = str(balance.amount) + ' ' + balance.symbol
            self.balances.append_entry( tmpForm )

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
        
        tmpListItems = []
        if proposal.get('expiration_time'):
            tmpListItems.append( ( 'Expiration time', proposal['expiration_time']) )
        if proposal.get('review_period_time'):
            tmpListItems.append( ( 'Review period time', proposal['review_period_time']) )
        
        ocw = OperationsContainerWidget(
                title='Proposal ' + proposal['id'],
                listItems=tmpListItems,
                buttonNegative='Reject',
                buttonPositive='Accept',
                buttonNegativeURL=url_for('votable_proposals_accept', proposalId=proposal['id']), 
                buttonPositiveURL=url_for('votable_proposals_reject', proposalId=proposal['id'])
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
                buttonPositive='Broadcast',
                buttonNegativeURL=url_for('pending_operations_discard'),
                buttonPositiveURL=url_for('pending_operations_broadcast'),
            )
    
    tmp = transaction.get_parent().__repr__()
    for operation in transaction.get_parent()['operations']:
        ocw.addOperation( operation[0], operation[1] )
    
    return ocw   