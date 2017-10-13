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
    
class UnlockForm(FlaskForm):
    password = PasswordField('Password', validators['unlock'])
    submit = SubmitField("Unlock")

class SportNewForm(FlaskForm):
    names  = FieldList(FormField(InternationalizedStringForm), min_entries=1, label="List of translations")
    submit = SubmitField("Submit")
    addLanguage = SubmitField("Add new language")
    
class SportUpdateForm(FlaskForm):
    sport  = SelectField("Sport", [Required()], choices=None)
    names  = FieldList(FormField(InternationalizedStringForm), min_entries=1, label="List of translations")
    submit = SubmitField("Submit")
    addLanguage = SubmitField("Add new language")
    
class SportSelectForm(FlaskForm):
    # this form is only for selction, choices can be loaded always
    sport  = SelectField("Sport", [Required()], choices=Node().getSportsAsList())
    submit = SubmitField("Submit")
    
class NewForm(FlaskForm):
    names  = FieldList(FormField(InternationalizedStringForm), min_entries=1, label="List of translations")
    submit = SubmitField("Submit")
    addLanguage = SubmitField("Add new language")
    
#     def __init__(self, list_title="List of translations", *args, **kwargs):
#         self.names = FieldList(FormField(InternationalizedStringForm), min_entries=1, label=list_title)
#         super(FlaskForm, self).__init__(*args, **kwargs)
    
class OperationForm(FlaskForm):
    name  = StringField('Name', render_kw = { 'disabled' : True }) 
    
class PendingOperationsForms(FlaskForm):
    operations = FieldList(FormField(OperationForm), min_entries=0, label="List of operations")
    submit = SubmitField("Broadcast")
    