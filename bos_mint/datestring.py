from datetime import datetime, timedelta
import strict_rfc3339
import pytz


def date_to_string(date_object=None):
    """ rfc3339 conform string represenation of a date
        can also be given as str YYYY-mm-dd HH:MM:SS """
    if type(date_object) == int:
        if date_object < 365:
            date_object = datetime.utcnow() + timedelta(days=date_object)
        else:
            date_object = datetime.utcfromtimestamp(date_object)
    if type(date_object) == float:
        date_object = datetime.utcfromtimestamp(date_object)
    if type(date_object) == str:
        try:
            date_object = datetime.strptime(date_object + "+0000",
                                            '%Y-%m-%d %H:%M:%S%z')
        except ValueError:
            date_object = string_to_date(date_object)
    if not date_object:
        return strict_rfc3339.now_to_rfc3339_utcoffset()
    else:
        if date_object.tzinfo is None:
            return strict_rfc3339.timestamp_to_rfc3339_utcoffset(
                pytz.UTC.localize(date_object).timestamp())
        else:
            return strict_rfc3339.timestamp_to_rfc3339_utcoffset(
                date_object.timestamp())


def string_to_date(date_string=None):
    """ assumes rfc3339 conform string and creates date object """
    if date_string is None:
        date_time_object = datetime.utcnow()
        return pytz.utc.localize(date_time_object)
    if type(date_string) == str:
        if len(date_string) == 8:
            date_string = date_string[0:4] + "-" + date_string[4:6] + "-" + date_string[6:8] + "T00:00:00Z"
        if len(date_string) == 10:
            date_string = date_string + "T00:00:00Z"
        if len(date_string) == 19:
            date_string = date_string + "Z"
        if len(date_string) == 18 and date_string[10:11] == "t":
            date_string = date_string[0:10] + "T" + date_string[11:13] + ":" + date_string[13:15] + ":" + date_string[15:17] + "Z"
        date_time_object = datetime.utcfromtimestamp(
            strict_rfc3339.rfc3339_to_timestamp(date_string))
        return pytz.utc.localize(date_time_object)
    raise Exception("Only string covnersion supported")
