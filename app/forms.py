import re
from flask import current_app
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
    class _UpdateForm(FlaskForm):
        pass
    
    selectChoices = selectDictToList(selectChoices)

    if not selected:
        select = SelectField(label=utils.getTitle(typeName), validators=[DataRequired()], choices=selectChoices)
    else:
        select = SelectField(label=utils.getTitle(typeName), validators=[DataRequired()], choices=selectChoices, render_kw={"disabled": True})
    
    if selected:   
        select.data = selected
        
    setattr(_UpdateForm, 'select', select)
    
    baseCounter = select.creation_counter;
    
    for idx, entry in enumerate(newFormClass.__dict__.items()):
        if not entry[0].startswith('_'):
            if (not selected and entry[0].startswith('submit')) or selected:
                entry[1].creation_counter = baseCounter + idx + 1
                setattr(_UpdateForm, entry[0], entry[1]) 
    
    form = _UpdateForm()
    return form


class UnlockPassword(object):
    def __init__(self, message="Invalid Unlock Password!"):
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
    submit = SubmitField("Unlock")
            
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
    
class OperationForm(FlaskForm):
    name  = StringField(label='Name', render_kw = { 'disabled' : True }) 
    
class PendingOperationsForms(FlaskForm):
    operations = FieldList(FormField(OperationForm, label=""), min_entries=0, label="List of operations")
    submit     = SubmitField("Broadcast")
    
    