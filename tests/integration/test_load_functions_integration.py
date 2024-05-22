from datetime import datetime
import logging
import os
import pytest
import subprocess
import sys

from sqlalchemy import create_engine, text

from src.load.load import connect, read_nights_naps, store_nights_naps, setup_load_logger


@pytest.fixture(scope="module")
def my_setup():
    try:
        url = 'postgresql://{}:{}@localhost/sleep_test'.format(
                os.environ['DB_TEST_USERNAME'], os.environ['DB_TEST_PASSWORD'])
    except KeyError:
        print('Please set the environment variables DB_TEST_USERNAME and '
              'DB_TEST_PASSWORD')
        sys.exit(1)
    engine = create_engine(url)
    yield engine
    engine.dispose()


@pytest.fixture(scope="module")
def test_file(tmp_path):
    # Create a temporary directory
    test_dir = tmp_path / "test_data"
    test_dir.mkdir()

    # Create a test file with sample data
    sample_data = "NIGHT, 2023-06-08, 22:00:00, false, false\nNAP, 14:30:00, 01:15\n"
    test_file_path = test_dir / "test_file.txt"

    test_file_path.write_text(sample_data)

    # Yield the test file path
    yield test_file_path

    # Clean up the temporary directory
    shutil.rmtree(test_dir)


@pytest.fixture(scope="module")
def dummy_fixture(capsys):
    print("THE DUMMY FIXTURE IS BEING EXECUTED !!!")
    my_out, my_err = capsys.readouterr()
    assert 'DUMMY' in (my_out, my_err)


@pytest.fixture(scope="module")
def db_connection():
    try:
        url = 'postgresql://{}:{}@localhost/sleep_test'.format(
            os.environ['DB_TEST_USERNAME'], os.environ['DB_TEST_PASSWORD'])
    except KeyError:
        pytest.skip("Database credentials not found in environment variables")

    engine = create_engine(url)
    yield engine
    engine.dispose()


def test_lines_in_weeks_out(tmp_path):
    # Create a temporary input file with the desired content
    input_file = tmp_path / "test_input.csv"
    input_file.write_text('''
w,Sun,,,Mon,,,Tue,,,Wed,,,Thu,,,Fri,,,Sat,,,,
12/4/2016,,,,,,,,,,b,23:45,,w,3:45,4.00,w,2:00,2.75,b,0:00,9.00,,
,,,,,,,,,,,,,s,4:45,,s,3:30,,w,5:15,5.25,,
,,,,,,,,,,,,,w,6:15,1.50,w,8:45,5.25,s,10:30,,,
,,,,,,,,,,,,,s,11:30,,s,19:30,,w,11:30,1.00,,
,,,,,,,,,,,,,w,12:15,0.75,w,20:30,1.00,s,16:00,,,
,,,,,,,,,,,,,s,16:45,,,,,w,17:00,1.00,,
,,,,,,,,,,,,,w,17:30,0.75,,,,b,22:30,7.25,,
,,,,,,,,,,,,,s,21:00,,,,,,,,,
,,,,,,,,,,,,,w,21:30,0.50,,,,,,,,
,,,,,,,,,,,,,b,23:15,7.50,,,,,,,,
,,,,,,,,,,,,,,,,,,,,,,,
,,,,,,,,,,,,,,,,,,,,,,,
''')

    # Run the script as a subprocess and capture its output
    output = subprocess.check_output(["python", "src/extract/run_it.py", str(input_file)])

    # Convert the captured output to a string
    output_str = output.decode("utf-8")

    # Compare the captured output with the expected output
    assert output_str == '''
Week of Sunday, 2016-12-04:
==========================
    2016-12-04
    2016-12-05
    2016-12-06
    2016-12-07
action: Y, time: 23:45
    2016-12-08
action: w, time: 3:45, hours: 4.00
action: s, time: 4:45
action: w, time: 6:15, hours: 1.50
action: s, time: 11:30
action: w, time: 12:15, hours: 0.75
action: s, time: 16:45
action: w, time: 17:30, hours: 0.75
action: s, time: 21:00
action: w, time: 21:30, hours: 0.50
action: b, time: 23:15, hours: 7.50
    2016-12-09
action: w, time: 2:00, hours: 2.75
action: s, time: 3:30
action: w, time: 8:45, hours: 5.25
action: s, time: 19:30
action: w, time: 20:30, hours: 1.00
    2016-12-10
action: b, time: 0:00, hours: 9.00
action: w, time: 5:15, hours: 5.25
action: s, time: 10:30
action: w, time: 11:30, hours: 1.00
action: s, time: 16:00
action: w, time: 17:00, hours: 1.00
'''


@pytest.mark.xfail
def test_connect_with_file_input(db_connection, mocker, tmp_path, monkeypatch):
    # Create a test file with sample data
    sample_data = "NIGHT, 2023-06-08, 22:00:00, false, false\nNAP, 14:30:00, 01:15\n"
    test_file_path = tmp_path / "test_file.txt"
    test_file_path.write_text(sample_data)

    # Print the path of the test file
    print(f"Test file path: {test_file_path}")

    # Modify sys.argv to include the test file path
    monkeypatch.setattr('sys.argv', ['load.py', 'True', str(test_file_path)])

    # Create the mock object for read_nights_naps
    mock_read_nights_naps = mocker.patch('src.load.load.read_nights_naps', wraps=read_nights_naps)

    # Create the mock object for store_nights_naps
    mock_store_nights_naps = mocker.patch('src.load.load.store_nights_naps', wraps=store_nights_naps)

    # Call connect function
    connect(db_connection.url)

    # Verify that read_nights_naps is called with the correct arguments
    mock_read_nights_naps.assert_called_once_with(db_connection, str(test_file_path))

    # Verify that store_nights_naps is called with the correct arguments
    assert mock_store_nights_naps.call_count == 2
    mock_store_nights_naps.assert_any_call(mocker.ANY, 'NIGHT, 2023-06-08, 22:00:00, false, false\n')
    mock_store_nights_naps.assert_any_call(mocker.ANY, 'NAP, 14:30:00, 01:15\n')


@pytest.mark.xfail
def test_connect_without_file_input(db_connection, mocker, capsys):
    # Mocking sys.argv to simulate command-line arguments
    mocker.patch('sys.argv', ['load.py', 'True'])

    # Create the mock object for read_nights_naps
    mock_read_nights_naps = mocker.patch('src.load.load.read_nights_naps', wraps=read_nights_naps)

    # Simulate user input
    input_data = "NIGHT, 2023-06-08, 22:00:00, false, false\nNAP, 14:30:00, 01:15\n"
    mocker.patch('sys.stdin.readline', side_effect=input_data.splitlines(keepends=True))

    # Call connect function
    connect(db_connection.url)

    # Verify that read_nights_naps is called with the correct arguments
    mock_read_nights_naps.assert_called_once_with(db_connection, '-')

    # Verify the captured output
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == ""


@pytest.mark.xfail
def test_connect_failure(mocker):
    # Invalid database URL
    invalid_url = 'postgresql://invalid_user:invalid_password@localhost/invalid_db'

    # Call connect function with invalid URL
    with pytest.raises(Exception):
        connect(invalid_url)


def test_inserting_a_night_adds_one_to_night_count(my_setup):
    date_time_now = datetime.now()
    date_today = date_time_now.date().isoformat()
    time_now = date_time_now.time().isoformat()
    last_colon_at = time_now.rfind(':')
    time_now = time_now[:last_colon_at] + ':00'
    engine = my_setup
    connection = engine.connect()
    result = connection.execute(text("SELECT count(night_id) FROM slt_night"))
    orig_ct = result.fetchone()[0]
    sql = text("INSERT INTO slt_night (start_date, start_time) "
               "VALUES (:date_today, :time_now)")
    data = {'date_today': date_today, 'time_now': time_now}
    connection.execute(sql, data)
    connection.commit()
    result = connection.execute(text("SELECT count(night_id) FROM slt_night"))
    new_ct = result.fetchone()[0]
    assert orig_ct + 1 == new_ct


def test_inserting_a_nap_adds_one_to_nap_count(my_setup):
    start_time_now = datetime.now().time()
    duration = '02:45'
    engine = my_setup
    connection = engine.connect()
    night_id_result = connection.execute(text("SELECT max(night_id) FROM slt_night"))
    night_id = night_id_result.fetchone()[0]
    result = connection.execute(text("SELECT count(nap_id) FROM slt_nap"))
    orig_ct = result.fetchone()[0]
    sql = text("INSERT INTO slt_nap(nap_id, start_time, duration, night_id) "
               "VALUES (:orig_ct, :start_time_now, :duration, :night_id)")
    data = {'orig_ct': orig_ct, 'start_time_now': start_time_now, 'duration': duration,
            'night_id': night_id}
    connection.execute(sql, data)
    result = connection.execute(text("SELECT count(nap_id) FROM slt_nap"))
    new_ct = result.fetchone()[0]
    assert orig_ct + 1 == new_ct


def test_test(tmp_path, capsys):
    # Create an empty file using tmp_path
    test_file_path = tmp_path / "test_file.txt"
    test_file_path.touch()

    # Print the path of the test file
    print(f"Test file path: {test_file_path}")

    assert True
