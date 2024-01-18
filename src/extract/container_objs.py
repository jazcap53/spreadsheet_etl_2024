# file: src/extract/container_objs.py
# andrew jarcho
# 2017-01-21

# python: 3.5


import datetime
import re
from collections import namedtuple


def validate_segment(segment):
    """
    valid segments: 'b', time, ''
                    'b', time, str(float)
                    's', time, ''
                    'w', time, str(float)
    """
    if not any(segment) or not all(segment[0:2]):
        return False
    if not re.match(r'[012]?\d:\d{2}', segment[1]):
        return False
    if segment[2] and not re.match(r'[12]?\d\.\d{2}', segment[2]):
        return False
    if segment[0]:
        return check_segment_0(segment)  # this test must go last


def check_segment_0(segment):
    if segment[0][0] not in ('b', 's', 'w') or \
        segment[0][0] == 's' and segment[2] or \
            segment[0][0] == 'w' and not segment[2]:
        return False
    return True


class Event(namedtuple('EventTuple', 'action, mil_time, hours')):
    """
    Each EventTuple holds:
        action -- a character from the set {'b', 's', 'w'}
        mil_time -- a 24-hour time string as 'H:MM' or 'HH:MM'
        hours -- an interval expressed as str(float))
                 The interval may have one or two digits before
                 the decimal point, and will have exactly two digits
                 after. Its value may not be zero (0.00), but may be
                 the empty string.
    """
    pass


class Day(namedtuple('DayTuple', 'dt_date, events')):
    """
    Each DayTuple holds a datetime.date and a (possibly empty)
    list of Events
    """
    def __init__(self, d, e):
        """ Ctor used just to filter input """
        if not isinstance(d, datetime.date):
            raise TypeError('Day ctor called with non-date first arg')
        if not isinstance(e, list):
            raise TypeError('Day ctor called with non-list second arg')


class Week(namedtuple('WeekTuple',
                      'Sunday, Monday, Tuesday, Wednesday, Thursday, Friday,'
                      ' Saturday')):
    """ Each WeekTuple holds seven named Day tuples """
    def __init__(self, *day_list):
        """ Ctor used just to filter input """
        self.day_list = day_list
        for ix, p in enumerate(self.day_list):
            if not isinstance(p, Day):
                raise TypeError('Week ctor with non-Day in param list')
            if not ix and p.dt_date.weekday() != 6:
                raise ValueError('Week ctor called with non-Sunday start'
                                 'date')
