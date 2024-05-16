import pdb
from datetime import datetime
import os
import pytest
import sys

from sqlalchemy import create_engine, text

from src.load.load import connect, read_nights_naps


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
def db_connection():
    try:
        url = 'postgresql://{}:{}@localhost/sleep_test'.format(
            os.environ['DB_TEST_USERNAME'], os.environ['DB_TEST_PASSWORD'])
    except KeyError:
        pytest.skip("Database credentials not found in environment variables")

    engine = create_engine(url)
    yield engine
    engine.dispose()


def test_connect_with_file_input(db_connection, mocker, tmp_path, monkeypatch):
    pdb.set_trace()
    # Create a test file with sample data
    sample_data = "NIGHT, 2023-06-08, 22:00:00, false, false\nNAP, 14:30:00, 01:15\n"
    test_file_path = tmp_path / "test_file.txt"
    test_file_path.write_text(sample_data)

    # Modify sys.argv to include the test file path
    monkeypatch.setattr('sys.argv', ['load.py', 'True', str(test_file_path)])

    # Create the mock object for read_nights_naps
    mock_read_nights_naps = mocker.patch('src.load.load.read_nights_naps', wraps=read_nights_naps)

    # Call connect function
    connect(db_connection.url)

    # Verify that read_nights_naps is called with the correct arguments
    mock_read_nights_naps.assert_called_once_with(db_connection, str(test_file_path))


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


def test_connect_failure(mocker):
    # Invalid database URL
    invalid_url = 'postgresql://invalid_user:invalid_password@localhost/invalid_db'

    # Call connect function with invalid URL
    with pytest.raises(Exception):
        connect(invalid_url)


def test_connect_with_file_input(db_connection, mocker):
    # Mocking sys.argv to simulate command-line arguments
    mocker.patch('sys.argv', ['load.py', 'True', 'test_file.txt'])

    # Create the mock object for read_nights_naps
    mock_read_nights_naps = mocker.patch('src.load.load.read_nights_naps', wraps=read_nights_naps)

    # Call connect function
    connect(db_connection.url)

    # Verify that read_nights_naps is called with the correct arguments
    mock_read_nights_naps.assert_called_once_with(db_connection, 'test_file.txt')


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
