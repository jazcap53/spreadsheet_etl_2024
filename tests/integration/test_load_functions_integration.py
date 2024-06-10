import builtins
from datetime import datetime, date as dt_date, time as dt_time
import logging
import os
import pytest
import subprocess
import sys
import time

from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import sessionmaker, scoped_session

from src.load.load import connect, read_nights_naps, store_nights_naps, setup_load_logger


# ========== FIXTURES ==========

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
def db_connection_url():
    url = None
    try:
        url = 'postgresql://{}:{}@localhost/sleep_test'.format(
            os.environ['DB_TEST_USERNAME'], os.environ['DB_TEST_PASSWORD'])
    except KeyError:
        pytest.skip("Database credentials not found in environment variables")

    yield url


@pytest.fixture(scope="module")
def db_session():
   url = 'postgresql://{}:{}@localhost/sleep_test'.format(
           os.environ['DB_USERNAME'], os.environ['DB_PASSWORD'])
   engine = create_engine(url)
   Session = scoped_session(sessionmaker(bind=engine))
   yield Session()
   Session.remove()


# ========== HELPER FUNCTIONS ==========


# Define a function to check whether there are any night records
def no_night_records_exist(db_session):
    night_count_result = db_session.execute(text("SELECT count(*) FROM sl_night"))
    night_count = night_count_result.fetchone()[0]
    return night_count == 0


def create_test_file(tmp_path, sample_data):
    """Create a test file with sample data."""
    test_file_path = tmp_path / "test_file.txt"
    test_file_path.write_text(sample_data)
    return test_file_path


def set_sys_argv(test_file_path=None):
    """Set sys.argv based on the presence of a test file path."""
    if test_file_path:
        return ["load.py", str(test_file_path), "True"]
    else:
        return ["load.py", "True"]


def run_load_script(sys_argv, input_data=None):
    """Run the load.py script as a separate process."""
    cmd = ["python", "src/load/load.py"] + sys_argv[1:]
    if input_data:
        subprocess.run(cmd, input=input_data, text=True, check=True)
    else:
        subprocess.run(cmd, check=True)
    time.sleep(0.5)  # Allow time for data insertion


def check_night_record(connection, expected_date, expected_time):
    """Check if the night record was inserted correctly."""
    result = connection.execute(text("SELECT * FROM sl_night WHERE start_date = :date AND start_time = :time"),
                              {"date": expected_date, "time": expected_time})
    night_record = result.fetchone()
    assert night_record is not None
    assert night_record[3] is False  # Check start_no_data
    assert night_record[4] is False  # Check end_no_data


def check_nap_record(connection, expected_time, expected_duration):
    """Check if the nap record was inserted correctly."""
    result = connection.execute(text("SELECT * FROM sl_nap WHERE start_time = :time AND duration = :duration"),
                              {"time": expected_time, "duration": expected_duration})
    nap_record = result.fetchone()
    assert nap_record is not None


def check_night_record_using_session(db_session, expected_date, expected_time):
    """Check if the night record was inserted correctly using db_session."""
    result = db_session.execute(text("SELECT * FROM sl_night WHERE start_date = :date AND start_time = :time"),
                                {"date": expected_date, "time": expected_time})
    night_record = result.fetchone()
    assert night_record is not None
    assert night_record[3] is False  # Check start_no_data
    assert night_record[4] is False  # Check end_no_data


def check_nap_record_using_session(db_session, expected_time, expected_duration):
    """Check if the nap record was inserted correctly using db_session."""
    result = db_session.execute(text("SELECT * FROM sl_nap WHERE start_time = :time AND duration = :duration"),
                                {"time": expected_time, "duration": expected_duration})
    nap_record = result.fetchone()
    assert nap_record is not None


# ========== TESTS ==========


@pytest.mark.parametrize("input_data", [
    None,
    "NIGHT, 2023-06-08, 22:00:00, false, false\nNAP, 14:30:00, 01.25\n"
])
def test_connect_indirectly(tmp_path, db_connection_url, input_data):
    """
    Test the connect() functionality indirectly.

    NOTE: This test relies on the 'set_test_env_variables' fixture
    to set the required environment variables for the test database.
    """
    # Save the original command line arguments and environment variables
    original_sys_argv = sys.argv.copy()
    original_env = os.environ.copy()

    try:
        if input_data is None:
            sample_data = "NIGHT, 2023-06-08, 22:00:00, false, false\nNAP, 14:30:00, 01.25\n"
            test_file_path = create_test_file(tmp_path, sample_data)
            sys_argv = set_sys_argv(test_file_path)
        else:
            sys_argv = set_sys_argv()

        run_load_script(sys_argv, input_data=input_data if input_data else None)

        # Create a database engine using the connection URL
        engine = create_engine(db_connection_url)

        # Query the database to check if the data was loaded correctly
        with engine.connect() as connection:
            check_night_record(connection, '2023-06-08', '22:00:00')
            check_nap_record(connection, '14:30:00', '01:15:00')

    finally:
        # Restore the original command line arguments and environment variables
        sys.argv = original_sys_argv
        os.environ.clear()
        os.environ.update(original_env)


def test_lines_in_weeks_out(tmp_path):
    # Create a temporary input file with the desired content using create_test_file
    input_data = '''
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
'''
    input_file = create_test_file(tmp_path, input_data)

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


def test_connect_failure():
    # Invalid database URL
    invalid_url = 'postgresql://invalid_user:invalid_password@localhost/invalid_db'

    # Call connect function with invalid URL
    connect(invalid_url)


def test_inserting_a_night_adds_one_to_night_count(db_session):
    date_time_now = datetime.now()
    date_today = date_time_now.date().isoformat()
    time_now = date_time_now.time().isoformat()
    last_colon_at = time_now.rfind(':')
    time_now = time_now[:last_colon_at] + ':00'

    result = db_session.execute(text("SELECT count(night_id) FROM sl_night"))
    orig_ct = result.fetchone()[0]

    sql = text("INSERT INTO sl_night (start_date, start_time, start_no_data, end_no_data) "
               "VALUES (:date_today, :time_now, false, false)")
    data = {'date_today': date_today, 'time_now': time_now}
    db_session.execute(sql, data)

    result = db_session.execute(text("SELECT count(night_id) FROM sl_night"))
    new_ct = result.fetchone()[0]

    assert orig_ct + 1 == new_ct

    # Check if the night record was inserted correctly using check_night_record_using_session
    check_night_record_using_session(db_session, date_today, time_now)


def test_inserting_a_nap_adds_one_to_nap_count(db_session):
    start_time_now = datetime.now().time()
    duration = '02:45'

    night_id_result = db_session.execute(text("SELECT max(night_id) FROM sl_night"))
    night_id = night_id_result.fetchone()[0]

    result = db_session.execute(text("SELECT max(nap_id) FROM sl_nap"))
    orig_ct = result.fetchone()[0]
    next_ct = 1 if orig_ct is None else orig_ct + 1

    sql = text("INSERT INTO sl_nap(nap_id, start_time, duration, night_id) "
               "VALUES (:next_ct, :start_time_now, :duration, :night_id)")
    data = {'next_ct': next_ct, 'start_time_now': start_time_now, 'duration': duration,
            'night_id': night_id}
    db_session.execute(sql, data)

    result = db_session.execute(text("SELECT max(nap_id) FROM sl_nap"))
    new_ct = result.fetchone()[0]

    assert new_ct == next_ct

    # Check if the nap record was inserted correctly using check_nap_record_using_session
    check_nap_record_using_session(db_session, start_time_now, duration)
