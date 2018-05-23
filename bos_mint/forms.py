from flask_wtf import FlaskForm
from wtforms import (
    TextField,
    PasswordField,
    ValidationError,
    StringField,
    BooleanField,
    SubmitField,
    HiddenField,
    SelectField,
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
    Optional
)
from peerplays.event import Event
from peerplays.bettingmarketgroup import BettingMarketGroup
from peerplays.eventgroup import EventGroup
from peerplays.bettingmarket import BettingMarket
from peerplaysbase.objects import EventStatus, BettingMarketGroupStatus,\
    BettingMarketStatus

from .istring import InternationalizedString, LanguageNotFoundException
from .node import Node
import datetime
from . import utils, wrapper, tostring, config


def selectDictToList(sourceDictionary):
    return [(x['id'], x['toString']) for x in sourceDictionary]


def buildUpdateForm(typeName, selectChoices, newFormClass, selected=None):
    # All objects have their own Form for their creation. This reuses those
    # forms and adds a selection field
    class _UpdateForm(FlaskForm):
        pass

    selectChoices = selectDictToList(selectChoices)

    # select is the preselected default. if set, choice field gets disabled
    if not selected:
        select = SelectField(label=utils.getTitle(typeName),
                             validators=[DataRequired()],
                             choices=selectChoices)
    else:
        select = SelectField(label=utils.getTitle(typeName),
                             validators=[DataRequired()],
                             choices=selectChoices,
                             render_kw={"disabled": True})

    if selected:
        select.data = selected

    setattr(_UpdateForm, 'select', select)

    # readjust creation counter for display ordering of fields
    baseCounter = select.creation_counter

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
        from peerplays.wallet import WrongMasterPasswordException
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
    country = SelectField("Language",
                          validators=[DataRequired()],
                          choices=InternationalizedString.getChoices())
    text = StringField('Text', validators=[DataRequired()],)


class TranslatedFieldForm(FlaskForm):
    translations = FieldList(FormField(InternationalizedStringForm, label=""),
                             min_entries=1,
                             label="")
    addLanguage = SubmitField("Add translation")

    def fill(self, translationsList):
        # empty the fieldlist
        while len(self.translations) > 0:
            self.translations.pop_entry()

        for country, text in translationsList:
            try:
                lng = InternationalizedString(country, text)
            except LanguageNotFoundException:
                # append an entry indicating the unknown language
                lng = InternationalizedString(InternationalizedString.UNKNOWN, country + " - " + text)

            # append entry to a FieldList creates forms from dictionary!
            self.translations.append_entry(lng.getForm())


class UnlockForm(FlaskForm):
    password = PasswordField('Password', validators['unlock'])
    submit = SubmitField("Unlock wallet")


class NewWalletForm(FlaskForm):
    password_confirm = PasswordField('Password', validators=[ DataRequired() ])
    password = PasswordField('Confirm password', validators['password'])
    submit = SubmitField("Create new wallet")


class GetAccountForm(FlaskForm):
    name = TextField('Name', validators=[Optional()])
    password = PasswordField('Password', validators=[Optional()])
    role = TextField('Role', validators=[Optional()], default='active', render_kw={'disabled': True})

    privateKey = TextField('Private Key (will be calculated from above information if not given)', validators=[Optional()])
    submit = SubmitField("Add accounts")

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
    name = FormField(TranslatedFieldForm)
    submit = SubmitField("Submit")

    @classmethod
    def getTypeName(cls):
        return 'sport'

    def init(self, selectedObject, defaultSelectedId=None):
        pass

    def fill(self, selectedObject):
        self.name.fill(selectedObject['name'])

    def create(self):
        return Node().createSport(
            InternationalizedString.parseToList(self.name.translations))

    def update(self, selectedId):
        return Node().updateSport(
            selectedId,
            InternationalizedString.parseToList(self.name))


class NewEventGroupForm(FlaskForm):
    sport = SelectField("Sport", validators=[DataRequired()],
                        choices=None)
    name = FormField(TranslatedFieldForm)
    submit = SubmitField("Submit")

    @classmethod
    def getTypeName(cls):
        return 'eventgroup'

    def init(self, selectedObject, default=None):
        self.sport.choices = selectDictToList(
            utils.getComprisedTypesGetter('sport')(None))
        if default:
            self.sport.data = default['parentId']

    def fill(self, selectedObject):
        self.sport.data = selectedObject['sport_id']
        self.name.fill(selectedObject['name'])

    def create(self):
        return Node().createEventGroup(
            InternationalizedString.parseToList(self.name), self.sport.data)

    def update(self, selectedId):
        return Node().updateEventGroup(
            selectedId,
            InternationalizedString.parseToList(self.name), self.sport.data)


class NewEventForm(FlaskForm):
    eventgroup = SelectField("Event group",
                             validators=[DataRequired()], choices=None)
    name = FormField(TranslatedFieldForm, label="Name")
    status = SelectField("Status",
                         validators=[DataRequired()],
                         choices=None)
    season = FormField(TranslatedFieldForm, label="Season")
    start = DateTimeField("Start (Format 'year-month-day hour:minute:secondZ' UTC)", format='%Y-%m-%d %H:%M:%SZ',
                          default=datetime.datetime.utcnow(),
                          validators=[DataRequired()])
    submit = SubmitField("Submit")

    @classmethod
    def getTypeName(cls):
        return 'event'

    def init(self, selectedObject, default=None):
        self.status.choices = utils.filterOnlyAllowed(EventStatus, "create")

        sportId = None
        if isinstance(selectedObject, EventGroup):
            sportId = selectedObject['sport_id']
        elif isinstance(selectedObject, Event):
            sportId = selectedObject.eventgroup.sport['id']
            self.status.choices = utils.filterOnlyAllowed(EventStatus, selectedObject['status'])
        elif isinstance(selectedObject, wrapper.EventGroup):
            sportId = selectedObject.get('parentId')

        # choices need to be filled at all times
        self.eventgroup.choices = selectDictToList(
            utils.getComprisedTypesGetter('eventgroup')(sportId))

        if default:
            self.eventgroup.data = default['parentId']

    def fill(self, selectedObject):
        self.eventgroup.data = selectedObject.eventgroup['id']
        self.name.fill(selectedObject['name'])
        self.season.fill(selectedObject['season'])

        # fill status choices on selection
        self.status.choices = utils.filterOnlyAllowed(EventStatus, selectedObject['status'])
        self.status.label.text = self.status.label.text + " (" + selectedObject['status'] + ")"
        self.status.data = selectedObject['status']

        self.start.data = utils.string_to_date(selectedObject['start_time'] + "Z")

    def create(self):
        return Node().createEvent(
            InternationalizedString.parseToList(self.name),
            InternationalizedString.parseToList(self.season),
            self.start.data,
            self.eventgroup.data)

    def update(self, selectedId):
        # only send state if changed
        old_status = Node().getEvent(selectedId)['status']

        if not old_status == self.status.data:
            new_state = self.status.data
        else:
            new_state = None

        return Node().updateEvent(
            selectedId,
            InternationalizedString.parseToList(self.name),
            InternationalizedString.parseToList(self.season),
            self.start.data,
            self.eventgroup.data,
            new_state)


class EventStatusForm(FlaskForm):
    """
    This is not representing an actual object on the blockchain, since status and score are all part of
    event. due to the fact that the normal event_update backend call does not support setting a score,
    only the event_status_update method does, we need a second form here for it.
    """
    eventgroup = SelectField("Event group",
                             validators=[DataRequired()],
                             choices=None,
                             render_kw={'disabled': True})
#     name = FormField(TranslatedFieldForm, label="Name", render_kw={'disabled': True})
    status = SelectField("Status (will always be set to finished)",
                         validators=[DataRequired()],
                         choices=None,
                         render_kw={'disabled': True})
    scores = StringField('Scores (semi-colon seperated list)', validators=[DataRequired()])

    submit = SubmitField("Submit")

    @classmethod
    def getTypeName(cls):
        return 'event_status'

    def init(self, selectedObject, default=None):
        self.status.choices = utils.filterOnlyAllowed(EventStatus, "create")

        sportId = None
        if isinstance(selectedObject, EventGroup):
            sportId = selectedObject['sport_id']
        elif isinstance(selectedObject, Event):
            sportId = selectedObject.eventgroup.sport['id']
            self.status.choices = utils.filterOnlyAllowed(EventStatus, selectedObject['status'])
        elif isinstance(selectedObject, wrapper.EventGroup):
            sportId = selectedObject.get('parentId')

        # choices need to be filled at all times
        self.eventgroup.choices = selectDictToList(
            utils.getComprisedTypesGetter('eventgroup')(sportId))
        if default:
            self.eventgroup.data = default['parentId']

    def fill(self, selectedObject):
        self.eventgroup.data = selectedObject.eventgroup['id']
#         self.name.fill(selectedObject['name'])
        self.status.data = "finished"
        if selectedObject['scores']:
            self.scores.data = ";".join(selectedObject['scores'])

    def create(self):
        return NotImplementedError("Event status creation not supported, subset of event!")

    def update(self, selectedId):
        commaseplist = self.scores.data.split(";")

        return Node().updateEventStatus(
            selectedId,
            self.status.data,
            commaseplist)


class NewBettingMarketGroupForm(FlaskForm):
    event = SelectField("Event", validators=[DataRequired()], choices=None)
    description = FormField(TranslatedFieldForm)
    status = SelectField("Status",
                         choices=None)
    bettingmarketrule = SelectField(
        "Betting market group rule",
        validators=[DataRequired()],
        choices=None)
    asset = SelectField("Asset",
                        validators=[DataRequired()],
                        choices=[(x, x) for x in config.get("allowed_assets")])
    submit = SubmitField("Submit")

    @classmethod
    def getTypeName(cls):
        return 'bettingmarketgroup'

    def init(self, selectedObject, default=None):
        self.status.choices = utils.filterOnlyAllowed(BettingMarketGroupStatus, "create")

        # choices need to be filled at all times
        eventGroupId = None
        if isinstance(selectedObject, Event):
            eventGroupId = selectedObject['event_group_id']
        elif isinstance(selectedObject, BettingMarketGroup):
            eventGroupId = selectedObject.event['event_group_id']
            self.status.choices = utils.filterOnlyAllowed(BettingMarketGroupStatus, selectedObject['status'])
        elif isinstance(selectedObject, wrapper.Event):
            eventGroupId = selectedObject.get('parentId')

        # choices need to be filled at all times
        self.event.choices = selectDictToList(
            utils.getComprisedTypesGetter('event')(eventGroupId))

        if default:
            self.event.data = default['parentId']

        self.bettingmarketrule.choices = selectDictToList(
            utils.getComprisedTypesGetter('bettingmarketgrouprule')(None))

        if self.asset.data == "None":
            self.asset.data = config.get("allowed_assets")[0]

    def fill(self, selectedObject):
        self.event.data = selectedObject['event_id']
        self.bettingmarketrule.data = selectedObject['rules_id']
        self.description.fill(selectedObject['description'])

        # fill status choices on selection
        self.status.choices = utils.filterOnlyAllowed(BettingMarketGroupStatus, selectedObject['status'])
        self.status.label.text = self.status.label.text + " (" + selectedObject['status'] + ")"
        self.status.data = selectedObject['status']

        self.asset.data = Node().getAsset(selectedObject["asset_id"])["symbol"]

    def create(self):
        return Node().createBettingMarketGroup(
            InternationalizedString.parseToList(self.description),
            self.event.data,
            self.bettingmarketrule.data,
            self.asset.data)

    def update(self, selectedId):
        # only send state if changed
        old_status = Node().getBettingMarketGroup(selectedId)['status']

        if not old_status == self.status.data:
            new_state = self.status.data
        else:
            new_state = None

        return Node().updateBettingMarketGroup(
            selectedId,
            InternationalizedString.parseToList(self.description),
            self.event.data,
            self.bettingmarketrule.data,
            new_state)


class NewBettingMarketForm(FlaskForm):
    bettingmarketgroup = SelectField(
        "Betting market group",
        validators=[DataRequired()],
        choices=None)
    description = FormField(TranslatedFieldForm, label="Description")
    payoutCondition = FormField(TranslatedFieldForm, label="Payout condition")
    status = SelectField("Status",
                         choices=None)
    submit = SubmitField("Submit")

    @classmethod
    def getTypeName(cls):
        return 'bettingmarket'

    def init(self, selectedObject, default=None):
        self.status.choices = utils.filterOnlyAllowed(BettingMarketStatus, "create")

        eventId = None
        if isinstance(selectedObject, BettingMarketGroup):
            eventId = selectedObject['event_id']
        elif isinstance(selectedObject, BettingMarket):
            eventId = selectedObject.bettingmarketgroup['event_id']
            self.status.choices = utils.filterOnlyAllowed(BettingMarketStatus, selectedObject['status'])
        elif isinstance(selectedObject, wrapper.BettingMarketGroup):
            eventId = selectedObject.get('parentId')

        self.bettingmarketgroup.choices = selectDictToList(
            utils.getComprisedTypesGetter('bettingmarketgroup')(eventId))

        if default:
            self.bettingmarketgroup.data = default['parentId']

    def fill(self, selectedObject):
        self.bettingmarketgroup.data = selectedObject['group_id']
        self.payoutCondition.fill(selectedObject['payout_condition'])
        self.description.fill(selectedObject['description'])

        # fill status choices on selection
        self.status.choices = utils.filterOnlyAllowed(BettingMarketStatus, selectedObject['status'])
        self.status.label.text = self.status.label.text + " (" + selectedObject['status'] + ")"
        self.status.data = selectedObject['status']

    def create(self):
        return Node().createBettingMarket(
            InternationalizedString.parseToList(self.payoutCondition),
            InternationalizedString.parseToList(self.description),
            self.bettingmarketgroup.data)

    def update(self, selectedId):
        # only send state if changed
        old_status = Node().getBettingMarket(selectedId)['status']

        if not old_status == self.status.data:
            raise NotImplementedError()

        return Node().updateBettingMarket(
            selectedId,
            InternationalizedString.parseToList(self.payoutCondition),
            InternationalizedString.parseToList(self.description),
            self.bettingmarketgroup.data)


class NewBettingMarketGroupRuleForm(FlaskForm):
    name = FormField(TranslatedFieldForm, label="Name")
    description = FormField(TranslatedFieldForm, label="Description")
    submit = SubmitField("Submit")

    @classmethod
    def getTypeName(cls):
        return 'bettingmarketgrouprule'

    def init(self, selectedObject, default=None):
        pass

    def fill(self, selectedObject):
        self.name.fill(selectedObject['name'])
        self.description.fill(selectedObject['description'])

    def create(self):
        return Node().createBettingMarketGroupRule(
            InternationalizedString.parseToList(self.name),
            InternationalizedString.parseToList(self.description))

    def update(self, selectedId):
        return Node().updateBettingMarketGroupRule(
            selectedId,
            InternationalizedString.parseToList(self.name),
            InternationalizedString.parseToList(self.description))


class ApprovalForm(FlaskForm):
    approve = BooleanField()


class SynchronizationForm(FlaskForm):
    chain_id = StringField('Connected to chain', render_kw={'readonly': True})
    bookiesports_name = StringField('Bookiesports chain', render_kw={'readonly': True})
    status = StringField('Synchronization status', render_kw={'readonly': True})
    submit = SubmitField("Synchronize now")


class BettingMarketResolveForm(FlaskForm):
    identifier = HiddenField('Identifier')
    description = StringField('Description',
                              render_kw={'readonly': True})
    resolution = SelectField(
        "Resolution",
        validators=[DataRequired()],
        choices=[("win", "win"),
                 ("not_win", "not_win"),
                 ("cancel", "cancel")]
    )


class BettingMarketGroupResolveForm(FlaskForm):
    event = SelectField("Event", validators=[DataRequired()], choices=None)

    event_status = StringField('Event status',
                               render_kw={'disabled': True})

    event_scores = StringField('Event score',
                               render_kw={'disabled': True})

    bettingmarketgroup = SelectField("Betting market group",
                                     validators=[DataRequired()],
                                     choices=None)

    bettingmarkets = FieldList(FormField(BettingMarketResolveForm, label=""),
                               min_entries=0,
                               label="Betting markets")

    submit = SubmitField("Submit")

    def __init__(self, title="Betting market group resolution"):
        super(BettingMarketGroupResolveForm, self).__init__()
        self.mytitle = title

    @property
    def title(self):
        return self.mytitle

    @property
    def id(self):
        return "bettingMarketGroupResolveForm"

    def initEvents(self, selectedObject, default=None):
        # choices need to be filled at all times
        eventGroupId = None
        if isinstance(selectedObject, str):
            eventGroupId = selectedObject
        elif isinstance(selectedObject, Event):
            eventGroupId = selectedObject['event_group_id']
        elif isinstance(selectedObject, BettingMarketGroup):
            eventGroupId = selectedObject.event['event_group_id']
        elif isinstance(selectedObject, wrapper.Event):
            eventGroupId = selectedObject.get('parentId')

        self.event.choices = selectDictToList(
            utils.getComprisedTypesGetter('event')(eventGroupId))

        if default:
            self.event.data = default

    def initGroups(self, selectedObject, default=None):
        eventId = None
        if isinstance(selectedObject, str):
            eventId = selectedObject
        elif isinstance(selectedObject, BettingMarketGroup):
            eventId = selectedObject['event_id']
        elif isinstance(selectedObject, BettingMarket):
            eventId = selectedObject.bettingmarketgroup['event_id']
        elif isinstance(selectedObject, wrapper.BettingMarketGroup):
            eventId = selectedObject.get('parentId')
        elif isinstance(selectedObject, Event):
            eventId = selectedObject['id']
        elif isinstance(selectedObject, wrapper.Event):
            eventId = selectedObject.get('id')

        self.bettingmarketgroup.choices = selectDictToList(
            utils.getComprisedTypesGetter('bettingmarketgroup')(eventId))
        if default:
            self.bettingmarketgroup.data = default

    def fillMarkets(self, selectedBettingMargetGroup):
        bettingMarketGroupId = None
        if isinstance(selectedBettingMargetGroup, str):
            bettingMarketGroupId = selectedBettingMargetGroup

        bettingMarkets = Node().getBettingMarkets(bettingMarketGroupId)

        for market in bettingMarkets:
            tmpForm = BettingMarketResolveForm()
            tmpForm.identifier = market['id']
            tmpForm.description = tostring.findEnglishOrFirst(
                market['description'])
            self.bettingmarkets.append_entry(tmpForm)

    def fillEvent(self, selectedObject):
        self.event.data = selectedObject['id']
        self.event_status.data = selectedObject["status"]
        self.event_scores.data = ";".join(selectedObject["scores"])


class AmountForm(FlaskForm):
    symbol = TextField(
        label='Asset',
        validators=[DataRequired()],
        render_kw={'disabled': True})


class AccountForm(FlaskForm):
    id = TextField(label='Id',
                   validators=[DataRequired()],
                   render_kw={'disabled': True})
    name = TextField(label='Name',
                     validators=[DataRequired()],
                     render_kw={'disabled': True})
    balances = FieldList(FormField(AmountForm, label=''),
                         label='Balances',
                         min_entries=0)

    def fill(self, account):
        self.id.data = account['id']
        self.name.data = account['name']

        # self.membershipExpirationDate.data = account['membership_expiration_date']

        for balance in account.balances:
            tmpForm = AmountForm()
            tmpForm.symbol = str(balance.amount) + ' ' + balance.symbol
            self.balances.append_entry(tmpForm)
