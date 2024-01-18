#!/usr/bin/python3


# file: src/transform/do_transform.py
# andrew jarcho
# 2017-03-16


"""
Read lines from stdin, transform to a db-friendly format, and write to stdout.

The output will be usable by the database with a minimum of further
processing, and will hold all relevant data from the input.
"""

import sys
import fileinput
import logging
import logging.handlers
import re


class Transform:
    transform_logger = logging.getLogger('transform.do_transform')
    transform_logger.setLevel('DEBUG')

    def __init__(self, data_source=fileinput):
        """
        The data source will be a file or FakeFileReadWrapper object
        if either is passed as a ctor argument. Otherwise the
        data source will be stdin, which is tied to stdout from the
        'extract' phase subprocess.
        """
        self.data_source = data_source
        self.out_val = None
        self.last_date = ''
        self.last_sleep_time = ''
        self.date_checker = None

    def read_each_line(self):
        """
        Read a line at a time from data_source; write to stdout.

        Not necessary to filter input as it's coming directly from
        extract process stdout:
        https://docs.python.org/3/library/subprocess.html#security-considerations

        Called by: __main__()
        """
        self.date_checker = re.compile(r' {4}\d{4}-\d{2}-\d{2}')
        with self.data_source.input() as infile:
            for curr_line in infile:
                self.process_curr(curr_line.rstrip('\n'))

    def process_curr(self, cur_l):
        """
        Process a single line of input.
        Called by: read_each_line()

        Takes a string argument, and may output a single line
        to stdout. The output may depend on values from previous input strings,
        as well as on values in the current input string. Output is formatted
        as:
           'NIGHT, date, time'  or
           'NAP, time, duration'
        Returns: None
        """
        if not cur_l or cur_l.startswith('Week of ') or cur_l.startswith('======='):
            self.handle_header_line()
        elif self.date_checker.match(cur_l):
            self.handle_date_line(cur_l)
        elif cur_l.startswith('action: '):
            self.handle_action_line(cur_l)
        else:
            Transform.transform_logger.warning('Bad value {} in input'.
                                               format(cur_l))
        if self.out_val is not None:
            self.output_val()

    def handle_header_line(self):
        self.out_val = None

    def handle_date_line(self, line):
        self.last_date = line[4:]

    def handle_action_line(self, line):
        if line.startswith('action: b'):
            self.last_sleep_time = self.get_time_part_from(line)
            self.out_val = 'NIGHT, {}, {}, {}, {}'.format(self.last_date,
                                                          self.last_sleep_time,
                                                          'false', 'false')
        elif line.startswith('action: s'):
            self.last_sleep_time = self.get_time_part_from(line)
        elif line.startswith('action: w'):
            wake_time = self.get_time_part_from(line)
            duration = self.get_duration(wake_time, self.last_sleep_time)
            self.out_val = 'NAP, {}, {}'.format(self.last_sleep_time, duration)
        elif line.startswith('action: N'):
            self.last_sleep_time = self.get_time_part_from(line)
            self.out_val = 'NIGHT, {}, {}, {}, {}'.format(self.last_date,
                                                          self.last_sleep_time,
                                                          'true', 'false')
        elif line.startswith('action: Y'):
            self.last_sleep_time = self.get_time_part_from(line)
            self.out_val = 'NIGHT, {}, {}, {}, {}'.format(self.last_date,
                                                          self.last_sleep_time,
                                                          'false', 'true')

    def output_val(self):
        print(self.out_val)
        self.out_val = None

    @staticmethod
    def get_time_part_from(cur_l):
        """
        Extract and return the time part of its string argument.

        Input time may be in 'h:mm' or 'hh:mm' format.
        Called by: process_curr().
        Returns: Extracted time as a string in 'hh:mm' format.
        """
        end_pos = cur_l.rfind(', hours: ')
        out_time = cur_l[17:] if end_pos == -1 else cur_l[17: end_pos]
        if len(out_time) == 4:
            out_time = '0' + out_time
        return out_time

    @staticmethod
    def get_duration(w_time, s_time):
        """
        Calculate the interval between w_time and s_time.

        Arguments are strings representing times in 'hh:mm' format.
        get_duration() calculates the interval between them as a
        string in decimal format e.g.,
            04.25 for 4 1/4 hours
        Called by: process_curr()
        Returns: the calculated interval, whose value will be
                non-negative.
        """
        w_time_list = list(map(int, w_time.split(':')))
        s_time_list = list(map(int, s_time.split(':')))
        if w_time_list[1] < s_time_list[1]:  # wake minute < sleep minute
            w_time_list[1] += 60
            w_time_list[0] -= 1
        if w_time_list[0] < s_time_list[0]:  # wake hour < sleep hour
            w_time_list[0] += 24
        dur_list = [(w_time_list[x] - s_time_list[x])
                    for x in range(len(w_time_list))]
        duration = str(dur_list[0])
        if len(duration) == 1:  # change hour from '1' to '01', e.g.
            duration = '0' + duration
        duration += Transform.quarter_hour_to_decimal(dur_list[1])
        return duration

    @staticmethod
    def quarter_hour_to_decimal(quarter):
        """
        Convert an integer number of minutes into a decimal string

        Argument is a number of minutes past the hour. If that number
        is a quarter-hour, convert it to a decimal quarter represented
        as a string.

        Called by: get_duration()
        Returns: a number of minutes represented as a decimal fraction
        """
        valid_quarters = (0, 15, 30, 45)
        if quarter not in valid_quarters:
            transform_logger = logging.getLogger('transform.do_transform')
            transform_logger.warning('Invalid quarter {} in do_transform.py '
                                     'quarter_hour_to_decimal()'.
                                     format(quarter))
            quarter = Transform.get_closest_quarter(quarter)

        decimal_quarter = None
        if quarter == 15:
            decimal_quarter = '.25'
        elif quarter == 30:
            decimal_quarter = '.50'
        elif quarter == 45:
            decimal_quarter = '.75'
        elif quarter == 0:
            decimal_quarter = '.00'
        return decimal_quarter

    @staticmethod
    def get_closest_quarter(q):
        if q < 8:
            closest_quarter = 0
        elif 8 <= q < 23:
            closest_quarter = 15
        elif 23 <= q < 37:
            closest_quarter = 30
        else:
            closest_quarter = 45
        return closest_quarter

def main():
    # from: https://docs.python.org/3/howto/
    # logging-cookbook.html#network-logging
    root_logger = logging.getLogger('')
    root_logger.setLevel(logging.INFO)
    socket_handler = logging.handlers.SocketHandler('localhost',
                                                    logging.handlers.
                                                    DEFAULT_TCP_LOGGING_PORT)
    # don't bother with a formatter, since a socket handler sends the event as
    # an unformatted pickle
    root_logger.addHandler(socket_handler)

    # transform_logger will need a formatter since it is writing to file
    transform_logger = logging.getLogger('transform.do_transform')
    transform_logger.setLevel(logging.DEBUG)
    file_handler = logging.FileHandler('src/transform/do_transform.log',
                                       mode='w')
    formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    transform_logger.addHandler(file_handler)
    transform_logger.propagate = False


if __name__ == '__main__':
    main()
    logging.info('transform start')
    t = Transform()
    t.read_each_line()
    logging.info('transform finish')
