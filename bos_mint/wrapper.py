from . import tostring


class BlockchainIdentifiable(dict):
    @classmethod
    def translateOperation(cls, operationData):
        pass

    def __init__(self, **kwargs):
        self.id = self.kwGet(kwargs, 'id', None)
        # todo: properly initilize dict here
        self.__dict__ = kwargs
        dict.__init__(self, kwargs)

        if not kwargs.get('toString'):
            self.toString = tostring.toString(self.__dict__, object=self)
            self['toString'] = self.toString

#     def create(self):
#         pass
#
#     def update(self):
#         pass
#
#     @classmethod
#     def filterByParentId(self, parentId):
#         pass

    def kwGet(self, kwargs, name, default=None):
        if default:
            return kwargs.get(name, default)
        else:
            return kwargs[name]


class Sport(BlockchainIdentifiable):

    @classmethod
    def translateOperation(cls, operationData):
        if operationData.get('operationName', None) == 'sport_create':
            return {'id': operationData['operationId'],
                    'name': operationData['name']}
        elif operationData.get('operationName', None) == 'sport_update':
            return {'pendingOperationId': operationData['operationId'],
                    'id': operationData['sport_id'],
                    'name': operationData['new_name']}
        else:
            from .node import NodeException
            raise NodeException(
                'Trying to instantiate a new sport from unknown operation')

    def __init__(self, **kwargs):
        kwargs['typeName'] = 'sport'
        kwargs['parentId'] = None
        BlockchainIdentifiable.__init__(self, **kwargs)
        self.name = self.kwGet(kwargs, 'name')


class EventGroup(BlockchainIdentifiable):

    @classmethod
    def translateOperation(cls, operationData):
        if operationData.get('operationName', None) == 'event_group_create':
            return {'id': operationData['operationId'],
                    'name': operationData['name'],
                    'sport_id': operationData['sport_id']}
        elif operationData.get('operationName', None) == 'event_group_update':
            return {'pendingOperationId': operationData['operationId'],
                    'id': operationData['event_group_id'],
                    'name': operationData['new_name'],
                    'sport_id': operationData['new_sport_id']}
        else:
            from .node import NodeException
            raise NodeException(
                'Trying to instantiate a new EventGroup from unknown operation')

    def __init__(self, **kwargs):
        kwargs['typeName'] = 'eventgroup'
        kwargs['parentId'] = self.kwGet(kwargs, 'sport_id')
        BlockchainIdentifiable.__init__(self, **kwargs)
        self.name = self.kwGet(kwargs, 'name')
        self.sport_id = self.kwGet(kwargs, 'sport_id')


class Event(BlockchainIdentifiable):

    @classmethod
    def translateOperation(cls, operationData):
        if operationData.get('operationName', None) == 'event_create':
            return {'id': operationData['operationId'],
                    'name': operationData['name'],
                    'season': operationData['season'],
                    'start_time': operationData['start_time'],
                    'event_group_id': operationData['event_group_id']}
        elif operationData.get('operationName', None) == 'event_update':
            return {'pendingOperationId': operationData['operationId'],
                    'id': operationData['event_id'],
                    'status': operationData.get('new_status', None),
                    'name': operationData.get('new_name', None),
                    'season': operationData.get('new_season', None),
                    'start_time': operationData.get('new_startTime', None),
                    'event_group_id': operationData.get('new_event_group_id', None),
                    'score': operationData.get('score', None)}
        elif operationData.get('operationName', None) == 'event_update_status':
            return {'pendingOperationId': operationData['operationId'],
                    'id': operationData['event_id'],
                    'status': operationData['status'],
                    'name': None,
                    'season': None,
                    'start_time': None,
                    'event_group_id': None,
                    'score': operationData.get('score', None)}
        else:
            from .node import NodeException
            raise NodeException(
                'Trying to instantiate a new Event from unknown operation')

    def __init__(self, **kwargs):
        kwargs['typeName'] = 'event'
        kwargs['parentId'] = self.kwGet(kwargs, 'event_group_id')
        BlockchainIdentifiable.__init__(self, **kwargs)
        self.name = self.kwGet(kwargs, 'name')
        self.season = self.kwGet(kwargs, 'season')
        self.start_time = self.kwGet(kwargs, 'start_time')
        self.event_group_id = self.kwGet(kwargs, 'event_group_id')


class BettingMarketGroup(BlockchainIdentifiable):

    @classmethod
    def translateOperation(cls, operationData):
        if operationData.get('operationName', None) ==\
                'betting_market_group_create':
            return {'id': operationData['operationId'],
                    'description': operationData['description'],
                    'event_id': operationData['event_id'],
                    'rules_id': operationData['rules_id']}
        elif operationData.get('operationName', None) ==\
                'betting_market_group_update':
            return {'pendingOperationId': operationData['operationId'],
                    'id': operationData['betting_market_group_id'],
                    'description': operationData.get('new_description', None),
                    'event_id': operationData.get('new_event_id', None),
                    'rules_id': operationData.get('new_rules_id', None),
                    'status': operationData.get('status', None)}
        elif operationData.get('operationName', None) ==\
                'betting_market_group_resolve':
            return {'pendingOperationId': operationData['operationId'],
                    'id': operationData['betting_market_group_id'],
                    'description': None,
                    'event_id': None,
                    'rules_id': None,
                    'status': None}
        else:
            from .node import NodeException
            raise NodeException(
                'Trying to instantiate a new BettingMarketGroup from unknown operation')

    def __init__(self, **kwargs):
        kwargs['typeName'] = 'bettingmarketgroup'
        kwargs['parentId'] = self.kwGet(kwargs, 'event_id')
        BlockchainIdentifiable.__init__(self, **kwargs)
        self.description = self.kwGet(kwargs, 'description')
        self.event_id = self.kwGet(kwargs, 'event_id')
        self.rules_id = self.kwGet(kwargs, 'rules_id')
        self.asset = self.kwGet(kwargs, 'asset', 'PPY')


class BettingMarketGroupRule(BlockchainIdentifiable):

    @classmethod
    def translateOperation(cls, operationData):
        if operationData.get('operationName', None) == 'betting_market_rules_create':
            return {'id': operationData['operationId'],
                    'name': operationData['name'],
                    'description': operationData['name']}
        elif operationData.get('operationName', None) == 'betting_market_rules_update':
            return {'pendingOperationId': operationData['operationId'],
                    'id': operationData['betting_market_rules_id'],
                    'name': operationData['new_name'],
                    'description': operationData['new_description']}
        else:
            from .node import NodeException
            raise NodeException('Trying to instantiate a new BettingMarketGroupRule from unknown operation')

    def __init__(self, **kwargs):
        kwargs['typeName'] = 'bettingmarketgrouprule'
        kwargs['parentId'] = None
        BlockchainIdentifiable.__init__(self, **kwargs)
        self.name = self.kwGet(kwargs, 'name')
        self.description = self.kwGet(kwargs, 'description')


class BettingMarket(BlockchainIdentifiable):

    @classmethod
    def translateOperation(cls, operationData):
        if operationData.get('operationName', None) == 'betting_market_create':
            return {'id': operationData['operationId'],
                    'payout_condition': operationData['payout_condition'],
                    'description': operationData['description'],
                    'group_id': operationData['group_id']}
        elif operationData.get('operationName', None) == 'betting_market_update':
            return {'pendingOperationId': operationData['operationId'],
                    'id': operationData['betting_market_id'],
                    'payout_condition': operationData['new_payout_condition'],
                    'description': operationData['new_description'],
                    'group_id': operationData['new_group_id']}
        else:
            from .node import NodeException
            raise NodeException('Trying to instantiate a new sport from unknown operation')

    def __init__(self, **kwargs):
        kwargs['typeName'] = 'bettingmarket'
        kwargs['parentId'] = self.kwGet(kwargs, 'group_id')
        BlockchainIdentifiable.__init__(self, **kwargs)
        self.payout_condition = self.kwGet(kwargs, 'payout_condition')
        self.description = self.kwGet(kwargs, 'description')
        self.group_id = self.kwGet(kwargs, 'group_id')


class Bet(BlockchainIdentifiable):

    def __init__(self, **kwargs):
        kwargs['typeName'] = 'bet'
        kwargs['parentId'] = self.kwGet(kwargs, 'betting_market_id')
        BlockchainIdentifiable.__init__(self, **kwargs)


def mapOperationToObject(typeName, operation):
    typeOpjectMap = {
        'sport': Sport,
        'eventgroup': EventGroup,
        'event': Event,
        'event_status': Event,
        'bettingmarketgroup': BettingMarketGroup,
        'bettingmarket': BettingMarket,
        'bettingmarketgrouprule': BettingMarketGroupRule
    }
    clazz = typeOpjectMap[typeName]
    return clazz(**clazz.translateOperation(operation))
