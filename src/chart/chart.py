# file: chart.py
# andrew jarcho
# 10/2018


from tests.file_access_wrappers import FileReadAccessWrapper
import re
from datetime import datetime, timedelta
from collections import namedtuple


Triple = namedtuple('Triple', ['start', 'length', 'symbol'], defaults=[0, 0, 0])
QS_IN_DAY = 96  # 24 * 4 quarter hours in a day
ASLEEP = u'\u2588'  # the printed color (black ink)
AWAKE = u'\u0020'  # the background color (white paper)
NO_DATA = u'\u2591'  # no data


class Chart:
    """
    Create a sleep chart from input data
    """
    def __init__(self, filename):
        self.filename = filename
        self.infile = None
        self.curr_line = ''
        self.prev_line = ''
        self.sleep_state = NO_DATA  # TODO: was AWAKE
        self.date_re = None
        self.quarters_carried = 0
        self.output_row = [NO_DATA] * QS_IN_DAY
        # self.curr_output_row = []
        self.header_seen = False
        self.spaces_left = QS_IN_DAY
        self.input_date = ''
        self.output_date = '2016-12-04'
        self.date_advanced = 0

    def read_file(self):
        """
        Send each line of file to parser.

        :yield: a parsed input line
        :return: None
        Called by: main()
        """
        with open(self.filename) as self.infile:
            while self.get_a_line():
                self.input_date, parsed_input_line = self.parse_input_line()
                yield parsed_input_line  # parsed_input_line is a Triple

    def get_a_line(self):
        """
        Get next non-header, non-date-only input line

        :return: bool
        Called by: read_file()
        """
        self.curr_line = self.infile.readline().rstrip()
        if not self.header_seen:
            self.skip_header()
        while self.curr_line[14:22] == ' ' * 8:
            self.curr_line = self.infile.readline().rstrip()
        return bool(self.curr_line)

    def skip_header(self):
        """
        Skip the file's header lines

        :return:
        Called by: get_a_line()
        """
        while self.curr_line and not self.date_re.match(self.curr_line):
            self.curr_line = self.infile.readline().rstrip()
        self.header_seen = True

    def parse_input_line(self):
        """

        :return: a Triple holding
                     a start position,
                     a count of quarter hours,
                     a unicode character (ASLEEP, AWAKE, NO_DATA)
        Called by: read_file()
        """
        line_array = self.curr_line.split('|')  # curr_line[-1] may be '|'
        line_array = list(map(str.strip, line_array))  # so strip() now
        if len(line_array) < 2:  # we've reached '(dddd rows)': end of input
            return None, Triple(None, None, None)
        date_in = line_array[0]
        start = self.time_or_interval_str_to_int(line_array[1])
        length = self.time_or_interval_str_to_int(line_array[2])
        # TODO: write a self.set_symbol(line_array) function -- call it
        #       wherever a symbol must be output (???) OR call it below only (???)
        symbol = ASLEEP
        return date_in, Triple(start, length, symbol)

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
                curr_triple = Triple(*next(read_file_iterator))
                if curr_triple.start is None:  # reached end of input
                    return
            except RuntimeError:
                return

            row_out = self.write_leading_blanks(curr_triple, row_out)
            spaces_left_now = self.spaces_left
            row_out = self.insert_to_row_out(curr_triple, row_out)
            if curr_triple.length >= spaces_left_now:
                self.write_output(row_out)
                row_out = self.output_row[:]  # get fresh copy of row to output
                self.spaces_left = QS_IN_DAY
            if self.quarters_carried:
                row_out = self.handle_quarters_carried(row_out)

    def write_leading_blanks(self, curr_triple, row_out):
        """
        Write blanks onto row_out from current posn to start of curr_triple.
        :param curr_triple:
        :param row_out:
        :return:
        Called by: make_output()
        """
        curr_posn = QS_IN_DAY - self.spaces_left
        if curr_posn < curr_triple.start:
            triple_to_insert = Triple(curr_posn,
                                      curr_triple.start - curr_posn, AWAKE)
            row_out = self.insert_to_row_out(triple_to_insert, row_out)
        else:
            triple_to_insert = Triple(curr_posn,
                                      QS_IN_DAY - curr_posn, AWAKE)
            row_out = self.insert_to_row_out(triple_to_insert, row_out)
            self.write_output(row_out)
            row_out = self.output_row[:]
            self.spaces_left = QS_IN_DAY
            if curr_triple.start > 0:
                triple_to_insert = Triple(0, curr_triple.start, AWAKE)
                row_out = self.insert_to_row_out(triple_to_insert, row_out)
        return row_out

    def handle_quarters_carried(self, curr_output_row):
        curr_output_row = self.insert_to_row_out(
                Triple(0, self.quarters_carried, ASLEEP), curr_output_row)
        self.quarters_carried = 0
        return curr_output_row

    def insert_to_row_out(self, triple, output_row):
        finish = triple.start + triple.length
        if finish > QS_IN_DAY:
            self.quarters_carried = finish - QS_IN_DAY
            triple = triple._replace(length=triple.length - self.quarters_carried)
        for i in range(triple.start, triple.start + triple.length):
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
        self.output_date = self.advance_output_date(self.output_date)
        print(f'{self.output_date} |{"".join(extended_output_row)}|')

    def advance_date(self, my_date, make_ruler=False):
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
    def time_or_interval_str_to_int(my_str):
        """
        Obtain from self.curr_interval the number of 15-minute chunks it contains
        :return: int: the number of chunks
        Called by: read_file()
        """
        if my_str:
            return (int(my_str[:2]) * 4 +  # 4 chunks per hour
                    int(my_str[3:5]) // 15) % QS_IN_DAY
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
    chart = Chart('/home/jazcap53/python_projects/spreadsheet_etl/' +
                  'xtraneous/transform_input_sheet_041_v001.txt')
    chart.compile_date_re()
    read_file_iterator = chart.read_file()
    ruler_line = chart.create_ruler()
    print(ruler_line)
    chart.make_output(read_file_iterator)


if __name__ == '__main__':
    main()
