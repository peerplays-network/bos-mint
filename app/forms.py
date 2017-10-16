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
from app.models import InternationalizedString
from app.node import Node


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
    country = SelectField("Language", [Required()], choices=InternationalizedString.LANGUAGES)
    text    = StringField('Text', [Required()])
    
class TranslatedFieldForm(FlaskForm):
    translations = FieldList(FormField(InternationalizedStringForm, label=""), min_entries=1, label="")
    addLanguage  = SubmitField("Add translation")
    
class UnlockForm(FlaskForm):
    password = PasswordField('Password', validators['unlock'])
    submit = SubmitField("Unlock")
    
class SportUpdateForm(FlaskForm):
    sport  = SelectField("Sport", [Required()], choices=None)
    names  = FieldList(FormField(InternationalizedStringForm, label=""), min_entries=1, label="List of translations")
    submit = SubmitField("Submit")
    addLanguage = SubmitField("Add new language")
    
class SportSelectForm(FlaskForm):
    # this form is only for selction, choices can be loaded always
    sport  = SelectField("Sport", [Required()], choices=Node().getSportsAsList())
    submit = SubmitField("Submit")
    
class NewSportForm(FlaskForm):
    name   = FormField(TranslatedFieldForm)
    submit = SubmitField("Submit")
#     
class NewEventGroupForm(FlaskForm):
    sport  = SelectField("Sport", [Required()], choices=Node().getSportsAsList())
    name   = FormField(TranslatedFieldForm)
    submit = SubmitField("Submit")
    
class NewEventForm(FlaskForm):
    eventgroup = SelectField("Event group", [Required()], choices=Node().getSportsAsList())
    name   = FormField(TranslatedFieldForm, label="Name")
    season = FormField(TranslatedFieldForm, label="Season")
    start  = TextField("Start")
    submit = SubmitField("Submit")
    
class NewBettingMarketGroupForm(FlaskForm):
    event = SelectField("Event", [Required()], choices=Node().getSportsAsList())
    description   = FormField(TranslatedFieldForm)
    bettingMarketRule = SelectField("Betting market rule", [Required()], choices=Node().getSportsAsList())
    submit = SubmitField("Submit")
    
class NewBettingMarketForm(FlaskForm):
    bettingmarketgroup = SelectField("Betting market group", [Required()], choices=Node().getSportsAsList())
    description     = FormField(TranslatedFieldForm, label="Description")
    payoutCondition = FormField(TranslatedFieldForm, label="Payout condition")
    submit = SubmitField("Submit")
    
class OperationForm(FlaskForm):
    name  = StringField('Name', render_kw = { 'disabled' : True }) 
    
class PendingOperationsForms(FlaskForm):
    operations = FieldList(FormField(OperationForm), min_entries=0, label="List of operations")
    submit     = SubmitField("Broadcast")
    