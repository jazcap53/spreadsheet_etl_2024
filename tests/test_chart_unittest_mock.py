from src.chart.chart_new import Chart
from unittest.mock import Mock, MagicMock

chart = Chart('/home/jazcap53/spreadsheet_etl/'
              'xtraneous/transform_input_sheet_043b.txt')
chart.compile_date_re()
read_file_iterator = chart.read_file()
ruler_line = chart.create_ruler()
print(ruler_line)
chart.make_output(read_file_iterator)


line = ''
chart.handle_action_line = MagicMock()
chart.parse_input_line()
chart.handle_action_line.assert_called_once_with('')
# chart.parse_input_line()
# chart.handle_action_line.assert_called_with('Week of Sunday, 2016-12-04:\n==========================')




