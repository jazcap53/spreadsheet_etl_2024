# file: src/extract/read_fns.py
# andrew jarcho
# 2017-01-25


# TODO: rewrite read_fns.py docstring
"""
SUMMARY:
=======
Class Extract in read_fns.py reads the raw input, extracts and formats
the data of interest, discards incomplete data, and writes the remaining data
of interest to stdout.

DETAIL:
======

The Task
---------

The input, a .csv file, is structured in lines as:

    w              Sun   Mon  Tue  Wed  Thu  Fri  Sat
    Sunday Date                    x    x    x    x
                                   x         x    x
                                   x              x
                                                  x


    Sunday Date    x     x    x    x    x    x    x
                   x          x    x         x    x
                              x    x         x
                              x              x
                              x

.
.
.

where each 'x' is a data item we care about (the 'w' at the start of
the file is noise).

A central problem is to extract data from the .csv file so that data
relating to each calendar day are grouped together.

A second problem is that the database cares about 'nights', which may
begin and end with arbitrary data points 'x'. Each night is associated
with a calendar day in the db.

A third problem is that we must discard data points 'x' that are part
of a 'night' for which we do not have complete data.


Principal methods
-----------------

lines_in_weeks_out() structures the data into an intermediate format
consisting of Weeks, Days, and Events. A Week has 7 consecutive (calendar)
Days, beginning with a Sunday. The Events from each Day are grouped
together.

_manage_output_buffer() converts the Weeks, Days, and Events into strings,
and puts the strings into the output buffer one Week at a time.

_write_or_discard_night() makes sure that only complete nights are written
to output


Week, Day, Event
----------------

Each Event has either 2 or 3 fields; each field is a key/value pair. The
key of the first field of each Event is 'action'. If the value for an
'action' field is 'b', then that Event starts a night.

The first two fields of any <'action': 'b'> Event hold data for
the night being started. If a third field is present, this
indicates that the data for the *preceding* night (if there was one)
are complete.

If an <'action: b'> event has NO third field, then the data for the
preceding night or nights are NOT complete. In that case, events are
discarded *in reverse order* starting with the event before the current
<'action: b'> event, up to and including the most recent <'action: b'>
event string that *does* have a third field.

Event strings not discarded, along with header strings for each calendar
week and day, are written to sys.stdout by default.
"""
import datetime
import re
import logging
import sys
from typing import Tuple, Optional, Union, List
from datetime import date

from container_objs import validate_segment, Week, Day, Event
# from tests.file_access_wrappers import FileReadAccessWrapper
from io import TextIOWrapper


read_logger = logging.getLogger('extract.read_fns')
read_logger.setLevel('DEBUG')


def open_infile(filename) -> TextIOWrapper:
    """
    Open input file.
    Left outside class so Extract.__init__() may accept an open file handle
    Called by: client code
    """
    return filename.open()


class Extract:
    SUNDAY = 6
    DAYS_IN_A_WEEK = 7

    def __init__(self, infile: TextIOWrapper) -> None:
        """infile: open for read"""
        self.infile = infile
        # self.sunday_date = None
        self.new_week = None
        self.line_as_list = []
        self.in_missing_data = False  # TODO: new 2019-09-03

    def lines_in_weeks_out(self) -> None:
        """
        Read lines from .csv file; output weeks, days, and events

        Called by: client code
        """
        in_week = False
        out_buffer = []
        for line in self.infile:
            self.line_as_list = line.strip().split(',')[:22]
            self.line_as_list = (
                    self.line_as_list[:1] + [item.strip() for item in
                                             self.line_as_list[1:]])
            date_match_obj = self._re_match_date(self.line_as_list[0])
            if not in_week:
                self.new_week = None
                if date_match_obj:
                    in_week = self._look_for_week(date_match_obj)
            if in_week:  # 'if' is correct here
                # output good data and discard bad data
                in_week = self._handle_week(out_buffer)
        # handle any data left in buffer
        if out_buffer:
            self._handle_leftovers(out_buffer)

    @staticmethod
    def _re_match_date(field: str) -> re.match:
        """
        Check for a date at start of param 'field'.

        Called by: lines_in_weeks_out()
        """
        return re.match(r'(\d{1,2})/(\d{1,2})/(\d{4})', field)

    def _look_for_week(self, date_match_obj: re.match) -> \
            bool:
        """
        Does current input line represent the start of a week?

        Called by: lines_in_weeks_out()
        """
        sunday_date = self._match_obj_to_date(date_match_obj)
        if self._is_a_sunday(sunday_date):
            # set up a Week
            day_list = self._make_day_list(sunday_date)
            self.new_week = Week(*day_list)
        else:
            read_logger.warning('Non-Sunday date {} found in input'.
                                format(sunday_date))
        return bool(self.new_week)

    @staticmethod
    def _is_a_sunday(dt_date: Optional[datetime.datetime]) -> Union[int, bool]:
        """
        Tell whether the parameter represents a Sunday

        Called by: _look_for_week()
        """
        return dt_date.weekday() == Extract.SUNDAY if dt_date else False

    @staticmethod
    def _make_day_list(sunday_date: date) -> List[Day]:
        """
        Make a week's worth of Day objects

        Called by: _look_for_week()
        """
        return [Day(sunday_date +
                    datetime.timedelta(days=x),
                    [])  # [] will hold Event list for Day
                for x in range(Extract.DAYS_IN_A_WEEK)]

    def _handle_week(self, out_buffer: list) -> bool:
        """
        if there are valid events in self.line_as_list:
            call self._get_events() to store them as Event objects in Week
            object new_week
        else:
            call self._manage_output_buffer() to write good data, discard
            incomplete data from self.output_buffer
        return False iff our week is over

        Called by: lines_in_weeks_out()
        """
        have_events = False
        if any(self.line_as_list):
            have_events = self._get_events()  # adds events to Week
        else:  # we saw a blank line: our week has ended
            self._manage_output_buffer(out_buffer)
        return have_events

    def _handle_leftovers(self, out_buffer: list) -> None:
        """
        If there is data left in output_buffer, calls
                self._manage_output_buffer().

        Called by: lines_in_weeks_out()
        """
        self._manage_output_buffer(out_buffer)

    @staticmethod
    def _match_obj_to_date(m: re.match) -> Optional[date]:
        """
        Convert a successful regex match to a datetime.date object

        Called by: lines_in_weeks_out()
        """
        if m:
            # group(3) is the year, group(1) is the month, group(2) is the day
            dt = [int(m.group(x)) for x in (3, 1, 2)]
            return datetime.date(dt[0], dt[1], dt[2])  # year, month, day
        else:
            return None

    def _get_events(self) -> bool:
        """
        Add each valid event in self.line_as_list to self.new_week.

        return True iff we successfully read at least one event
                       from self.line_as_list
        Called by: _handle_week()
        """
        shorter_line = self.line_as_list[1:]
        have_events = False
        for ix in range(7):
            # a segment is a list of 3 consecutive fields from the .csv file
            segment = shorter_line[3 * ix: 3 * ix + 3]
            segment = [seg.strip() for seg in segment]
            if validate_segment(segment):
                an_event = Event(*segment)
            # elif [seg.strip() for seg in segment] == ['', '', '']:
            elif segment == ['', '', '']:
                an_event = None
            else:
                read_logger.warning('segment {} not valid in _get_events()\n'
                                    '\tsegment date is {}'.
                                    format(segment,
                                           self.new_week[ix].dt_date))
                continue
            if self.new_week and an_event and an_event.action:
                self.new_week[ix].events.append(an_event)
                have_events = True
        return have_events

    # TODO: explain
    def _manage_output_buffer(self, out_buffer: list) -> None:
        """
        Convert the Events in self.new_week into strings, place the strings
        into output buffer, and pass output buffer to _write_or_discard_night()

        :return: None
        Called by: _handle_leftovers(), _handle_week()
        """
        if self.new_week:  # a Week of 7 Days beginning with a Sunday
            out_buffer.append(self._get_week_header())
            for day in self.new_week:
                out_buffer.append(self._get_day_header(day))
                for event in day.events:
                    event_str = 'action: {}, time: {}'.format(event.action,
                                                              event.mil_time)
                    if event.hours:
                        event_str += ', hours: {:.2f}'.format(float(event.hours))
                    if event.action == 'b':
                        self._write_or_discard_night(event, day.dt_date, out_buffer)
                    out_buffer.append(event_str)

    def _get_week_header(self) -> str:
        """

        Called by: _manage_output_buffer()
        """
        wk_header = '\nWeek of Sunday, {}:'.format(self.new_week[0].dt_date)
        wk_header += '\n' + '=' * (len(wk_header) - 2)
        return wk_header

    @staticmethod
    def _get_day_header(day: Day) -> str:
        """

        Called by: _manage_output_buffer()
        """
        return '    {}'.format(day.dt_date)  # four leading spaces

    def _write_or_discard_night(self, action_b_event: Event,
                                datetime_date: date,
                                out_buffer: list,
                                outfile: TextIOWrapper = sys.stdout) -> None:
        """
        Write (only) complete nights from out_buffer to outfile.

        action_b_event is the first Event for some night. It will have an
        'hours' field iff we have complete data for the preceding night.
        Called by: _manage_output_buffer()
        """
        if action_b_event.hours:  # we have complete data for preceding night
            self._write_complete_night(out_buffer, outfile)
        else:
            read_logger.info('Incomplete night(s) before {}'.
                             format(datetime_date))
            self._discard_incomplete_night(out_buffer, outfile)

    def _write_complete_night(self, out_buffer: list, outfile: TextIOWrapper) \
            -> None:
        """
        Write a complete night from output buffer to outfile
        # TODO: break this into 2 functions (?)  CHECK LINE THAT CAUSES ERROR
        Called by: _write_or_discard_night()
        """
        for line in out_buffer:
            if self.in_missing_data:
                if line.startswith('action: b'):
                    line = line.replace('b', 'Y', 1)  # TODO: CHECK THIS !!!
                    self.in_missing_data = False
            print(line, file=outfile)
        out_buffer.clear()

    def _discard_incomplete_night(self, out_buffer: list,
                                  outfile: TextIOWrapper) -> None:
        """

        Called by: _write_or_discard_night()
        """
        # pop incomplete data from end of output buffer
        for buf_ix in range(len(out_buffer) - 1, -1, -1):
            this_line = out_buffer[buf_ix]
            # if we see a 3-element 'b' event, there's good data before it
            if self._match_complete_b_event_line(this_line):
                no_data_line = self._get_no_data_line(out_buffer, buf_ix)
                print(no_data_line, file=outfile)
            elif self._match_event_line(this_line):  # pop only Event lines
                out_buffer.pop(buf_ix)  # leave headers in buffer
        self.in_missing_data = True

    @staticmethod
    def _match_complete_b_event_line(line: str) -> re.match:
        """
        Called by: _write_or_discard_night()
        """
        return re.match(r'action: b, time: \d{1,2}:\d{2},'
                        r' hours: \d{1,2}\.\d{2}$', line)

    # TODO: fix docstring
    @staticmethod
    def _get_no_data_line(out_buffer: list, buf_ix: int) -> str:
        """

        :param out_buffer:
        :param buf_ix:
        :return:
        Called by: _discard_incomplete_night()
        """
        line = out_buffer.pop(buf_ix).replace('b', 'N', 1)
        if line.count(',') == 2:
            pos = line.rfind(',')
            line = line[:pos]
        return line

    @staticmethod
    def _match_event_line(line: str) -> re.match:
        """
        Called by: _write_or_discard_night()
        """
        # b events may have 2 or 3 elements
        match_line = r'(?:action: b, time: \d{1,2}:\d{2})' \
                     r'(?:, hours: \d{1,2}\.\d{2})?$'
        # s events must have 2 elements
        match_line += r'|(?:action: s, time: \d{1,2}:\d{2}$)'
        # w events must have 3 elements
        match_line += r'|(?:action: w, time: \d{1,2}:\d{2}, ' \
                      r'hours: \d{1,2}\.\d{2}$)'
        return re.match(match_line, line)
