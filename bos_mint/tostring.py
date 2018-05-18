# Global to string method for centralized visualization
from .istring import InternationalizedString


def findEnglishOrFirst(listOfIStrings, desiredLanguage='en'):
    return InternationalizedString.listToDict(listOfIStrings).get(
        desiredLanguage, listOfIStrings[0][1])


def toString(toBeFormatted, object=None):

    if type(object).__name__ == "Event":
        if isinstance(toBeFormatted.get('name'), list):
            name = findEnglishOrFirst(toBeFormatted.get('name'))
        else:
            name = toBeFormatted.get('name')

        displayName = str(toBeFormatted["start_time"]) + "Z" + ":\n" + name
        if toBeFormatted.get("id", None) is not None:
            displayName = displayName + ' (' + toBeFormatted['id'] + ')'
    elif toBeFormatted.get('name') and toBeFormatted.get('id'):
        if isinstance(toBeFormatted.get('name'), list):
            name = findEnglishOrFirst(toBeFormatted.get('name'))
        else:
            name = toBeFormatted.get('name')

        displayName = name + ' (' + toBeFormatted.get('id') + ')'
    elif toBeFormatted.get('description') and toBeFormatted.get('id'):
        if isinstance(toBeFormatted.get('description'), list):
            name = findEnglishOrFirst(toBeFormatted.get('description'))
        else:
            name = toBeFormatted.get('description')

        displayName = name + ' (' + toBeFormatted.get('id') + ')'
    elif toBeFormatted.get('id'):
        displayName = '(' + toBeFormatted.get('id') + ')'
        if object:
            displayName = object.__class__.__name__ + " " + displayName
    else:
        raise Exception

    if toBeFormatted.get('pendingOperationId'):
        displayName = displayName + '*(' +\
            toBeFormatted.get('pendingOperationId') + ')'

    return displayName
