# file: chart.py
# andrew jarcho
# 10/2018


import os
from tests.file_access_wrappers import FileReadAccessWrapper
import sys  # temporary: for sys.exit()
import re
from datetime import datetime, timedelta
from collections import namedtuple

DEBUG =False 

QS_IN_DAY = 96  # 24 * 4 quarter hours in a day
ASLEEP = 'x' if DEBUG else u'\u2588'  # the printed color (black ink)
AWAKE = 'o' if DEBUG else u'\u0020'  # the background color (white paper)
NO_DATA = '-' if DEBUG else u'\u2591'  # no data
Triple = namedtuple('Triple', ['start', 'length', 'symbol'], defaults=[0, 0, 0])
QuartersCarried = namedtuple('QuartersCarried', ['length', 'symbol'], defaults=[0, NO_DATA])
stub = os.getenv('HOME2', '/media/jazcap53/0951a155-3d9d-41c3-a827-0b609af3979f')


class Chart:
    """
    Create a sleep chart from input data
    """
    def __init__(self, filename):
        self.curr_line = ''
        self.curr_sunday = ''
        self.date_re = None
        self.filename = filename
        # self.stub = os.getenv('HOME2', '/media/jazcap53/0951a155-3d9d-41c3-a827-0b609af3979f')
        self.infile = None
        self.last_date_read = None
        self.last_sleep_time = None
        self.last_start_posn = None
        self.output_date = '2016-12-04'
        self.output_row = [NO_DATA] * QS_IN_DAY
        self.quarters_carried = QuartersCarried(0, NO_DATA)
        self.sleep_state = NO_DATA  # TODO: was AWAKE
        self.spaces_left = QS_IN_DAY

    def read_file(self):
        """
        Send each line of file to parser.

        :yield: a parsed input line
        :return: None
        Called by: main()
        """
        with open(self.filename) as self.infile:
            while self.get_a_line():
                parsed_input_line = self.parse_input_line()
                if parsed_input_line.start == -1:
                    continue
                yield parsed_input_line  # parsed_input_line is a Triple

    def get_a_line(self):
        """
        Get next input line, discarding blank lines and '======'s

        :return: bool
        Called by: read_file()
        """
        self.curr_line = self.infile.readline().strip()
        if self.curr_line == '':  # discard exactly one blank line
            self.curr_line = self.infile.readline().strip()
        if self.curr_line.startswith('Week of Sunday, '):
            self.curr_sunday = self.curr_line[16: -1]
            self.infile.readline()  # discard '============' line
            self.curr_line = self.infile.readline().strip()
        return self.curr_line != ''

    def parse_input_line(self):
        """
        :return: a Triple holding
                     a start position, (start)
                     a count of quarter hours, (length)
                     a unicode character (ASLEEP, AWAKE, NO_DATA) (symbol)
        Called by: read_file()
        """
        if self.curr_line and re.match(r'\d{4}-\d{2}-\d{2}$', self.curr_line):
            if self.last_date_read is None:
                self.last_start_posn = 0
                self.last_date_read = self.curr_line
                return Triple(-1, -1, -1)
            else:
                if self.sleep_state == NO_DATA:
                    quarters_to_output = QS_IN_DAY - self.last_start_posn
                    t = Triple(self.last_start_posn, quarters_to_output,
                               self.sleep_state)
                    return t
                else:
                    self.last_date_read = self.curr_line
                    return Triple(-1, -1, -1)
        else:
            return self.handle_action_line(self.curr_line)

    def handle_action_line(self, line):
        """
        If a complete Triple is not yet available, return a
        Triple with values (-1, -1, -1).
        If a complete Triple is available, return the complete Triple.

        :param line:
        :return: a Triple holding
                     a start position,
                     a count of quarter hours,
                     a unicode character (ASLEEP, AWAKE, NO_DATA)
        Called by: parse_input_line()
        """
        if line.startswith('action: ') and line[8] in 'bsY':
            self.last_sleep_time = self.get_time_part(line)
            self.last_start_posn = self.get_start_posn(line)
            self.sleep_state = ASLEEP
            return Triple(-1, -1, -1)
        elif line.startswith('action: w'):
            wake_time = self.get_time_part(line)
            duration = self.get_duration(wake_time, self.last_sleep_time)
            length = self.get_num_chunks(duration)
            self.sleep_state = AWAKE
            t = Triple(self.last_start_posn, length, ASLEEP)
            return t
        elif line.startswith('action: N'):
            self.last_sleep_time = self.get_time_part(line)
            self.last_start_posn = self.get_start_posn(line)
            self.sleep_state = NO_DATA
            return Triple(-1, -1, -1)

    @staticmethod
    def get_time_part(cur_l):
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
        duration += Chart.quarter_hour_to_decimal(dur_list[1])
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
            quarter = Chart.get_closest_quarter(quarter)

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

    def make_output(self, read_file_iterator):
        """

        Make new day row.
        Insert any left over quarters to new day row.

        :return:
        Called by: main()
        """
        row_out = self.output_row[:]
        self.spaces_left = QS_IN_DAY
        
        while True:
            try:
                curr_triple = next(read_file_iterator)
                if curr_triple.start is None:  # reached end of input
                    return
            except StopIteration:
                return

            row_out = self.insert_leading_sleep_states(curr_triple, row_out)
            row_out = self.insert_to_row_out(curr_triple, row_out)  # sets self.quarters_carried.length
            if not self.spaces_left:
                self.write_output(row_out)  # advances self.output_date
                row_out = self.output_row[:]  # get fresh copy of row to output
                self.spaces_left = QS_IN_DAY
            if self.quarters_carried.length:
                row_out = self.handle_quarters_carried(row_out)

    def insert_leading_sleep_states(self, curr_triple, row_out):
        """
                Write sleep states onto row_out from current posn to start of curr_triple.
                :param curr_triple:
                :param row_out:
                :return:
                Called by: make_output()
                """
        curr_posn = QS_IN_DAY - self.spaces_left
        if curr_posn < curr_triple.start:
            triple_to_insert = Triple(curr_posn,
                                      curr_triple.start - curr_posn, self.sleep_state)
            row_out = self.insert_to_row_out(triple_to_insert, row_out)
        elif curr_posn == curr_triple.start:
            pass  # insert no leading sleep states
        else:
            triple_to_insert = Triple(curr_posn,
                                      QS_IN_DAY - curr_posn, self.sleep_state)
            row_out = self.insert_to_row_out(triple_to_insert, row_out)
            if not row_out.count(NO_DATA) or curr_triple.symbol == NO_DATA:  # row out is complete
                self.write_output(row_out)
            row_out = self.output_row[:]
            self.spaces_left = QS_IN_DAY
            if curr_triple.start > 0:
                triple_to_insert = Triple(0, curr_triple.start, self.sleep_state)
                row_out = self.insert_to_row_out(triple_to_insert, row_out)
        return row_out

    def handle_quarters_carried(self, curr_output_row):
        curr_output_row = self.insert_to_row_out(
                Triple(0, self.quarters_carried.length, self.quarters_carried.symbol), curr_output_row)
        self.quarters_carried = self.quarters_carried._replace(length=0)
        return curr_output_row

    def insert_to_row_out(self, triple, output_row):
        finish = triple.start + triple.length
        if finish > QS_IN_DAY:
            self.quarters_carried = QuartersCarried(finish - QS_IN_DAY, triple.symbol)
            triple = triple._replace(length=triple.length - self.quarters_carried.length)
        for i in range(triple.start, triple.start + triple.length):
            if DEBUG is True:
                if not i % 4:
                    output_row[i] = triple.symbol.upper()
                else:
                    output_row[i] = triple.symbol.lower()
            else:
                output_row[i] = triple.symbol
            self.spaces_left -= 1
        return output_row

    def get_curr_posn(self):
        return QS_IN_DAY - self.spaces_left

    def write_output(self, my_output_row):
        """

        :param my_output_row:
        :return:
        Called by: make_output()
        """
        extended_output_row = []
        for ix, val in enumerate(my_output_row):
            extended_output_row.append(val)
        print(f'{self.output_date} |{"".join(extended_output_row)}|')
        self.output_date = self.advance_output_date(self.output_date)

    def advance_date(self, my_date, make_ruler=False):
        """

        :param my_date:
        :param make_ruler:
        :return:
        Called by: advance_input_date(), advance_output_date()
        """
        date_as_datetime = datetime.strptime(my_date, '%Y-%m-%d')
        if make_ruler and date_as_datetime.date().weekday() == 5:
            print(self.create_ruler())
        date_as_datetime += timedelta(days=1)
        return date_as_datetime.strftime('%Y-%m-%d')

    def advance_input_date(self, my_input_date):
        return self.advance_date(my_input_date)

    def advance_output_date(self, my_output_date):
        return self.advance_date(my_output_date, True)

    @staticmethod
    def get_num_chunks(my_str):
        """
        Obtain from an interval the number of 15-minute chunks it contains
        :return: int: the number of chunks
        Called by: read_file()
        """
        if my_str:
            m = re.search(r'(\d{1,2})\.(\d{2})', my_str)  # TODO: compile this
            assert bool(m)
            return (int(m.group(1)) * 4 +  # 4 chunks per hour
                    int(m.group(2)) // 25) % QS_IN_DAY  # m.group(2) is decimal
        return 0

    @staticmethod
    def get_start_posn(time_str):
        """
        Obtain from a time string its starting position in an output day
        Called by: read_file()
        :param time_str: a time expressed as 'HH:MM'
        :return: int: the starting position
        """
        if time_str:
            m = re.search(r'(\d{1,2}):(\d{2})', time_str)  # TODO: compile this
            assert bool(m)
            return (int(m.group(1)) * 4 +  # 4 chunks per hour
                    int(m.group(2)) // 15) % QS_IN_DAY  # m.group(2) is base 60
        return 0

    def compile_date_re(self):
        """
        :return: None
        Called by: main()
        """
        self.date_re = re.compile(r' \d{4}-\d{2}-\d{2} \|')

    @staticmethod
    def create_ruler():
        ruler = list(str(x) for x in range(12)) * 2
        for ix, val in enumerate(ruler):
            if ix == 0:
                ruler[ix] = '12a'
            elif ix == 12:
                ruler[ix] = '12p'
        ruler_line = ' ' * 12 + ''.join(v.ljust(4, ' ') for v in ruler)
        return ruler_line


def main():
    sheet_path = ('spreadsheet_etl/' +
                  'xtraneous/transform_input_sheet_043b.txt')
    sheet_file = os.path.join(stub, sheet_path)
    # chart = Chart('/jazcap53/python_projects/spreadsheet_etl/' +
    #               'xtraneous/transform_input_sheet_043b.txt')
    chart = Chart(sheet_file)
    chart.compile_date_re()
    read_file_iterator = chart.read_file()
    ruler_line = chart.create_ruler()
    print(ruler_line)
    chart.make_output(read_file_iterator)


if __name__ == '__main__':
    main()
