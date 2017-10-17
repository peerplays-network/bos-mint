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

class NewEventGroupForm(FlaskForm):
    sport  = SelectField("Sport", validators=[DataRequired()], choices=Node().getSportsAsList())
    name   = FormField(TranslatedFieldForm)
    submit = SubmitField("Submit")
    
class NewEventForm(FlaskForm):
    eventgroup = SelectField("Event group", validators=[DataRequired()], choices=None)
    name   = FormField(TranslatedFieldForm, label="Name")
    season = FormField(TranslatedFieldForm, label="Season")
    start  = DateTimeField("Start", format='%Y-%m-%d %H:%M:%S', default=datetime.datetime.now(), validators=[DataRequired()])
    submit = SubmitField("Submit")
    
class NewBettingMarketGroupForm(FlaskForm):
    event = SelectField("Event", validators=[DataRequired()], choices=None)
    description   = FormField(TranslatedFieldForm)
    bettingmarketrule = SelectField("Betting market rule", validators=[DataRequired()], choices=selectDictToList(utils.getTypesGetter('bettingmarketrule')(None)))
    submit = SubmitField("Submit")
    
class NewBettingMarketForm(FlaskForm):
    bettingmarketgroup = SelectField("Betting market group", validators=[DataRequired()], choices=None)
    description     = FormField(TranslatedFieldForm, label="Description")
    payoutCondition = FormField(TranslatedFieldForm, label="Payout condition")
    submit = SubmitField("Submit")
    
class OperationForm(FlaskForm):
    name  = StringField('Name', render_kw = { 'disabled' : True }) 
    
class PendingOperationsForms(FlaskForm):
    operations = FieldList(FormField(OperationForm), min_entries=0, label="List of operations")
    submit     = SubmitField("Broadcast")
    
    