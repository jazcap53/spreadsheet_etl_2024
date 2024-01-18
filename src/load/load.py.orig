#!/usr/bin/python3

# file: src/load/load.py
# andrew jarcho
# 2017-02-20


import logging
import logging.handlers
import fileinput
# TODO: eliminate need for sqlalchemy
from sqlalchemy import create_engine, func
import os
import sys


def decimal_to_interval(dec_str):
    """
    Convert duration from a decimal string to an interval string
    (E.g., '3.25' for 3 1/4 hours becomes '03:15').
    Called by: read_nights_naps()
    """
    dec_mins_to_mins = {'00': '00', '25': '15', '50': '30', '75': '45'}
    hrs, dec_mins = dec_str.split('.')
    mins = None
    try:
        mins = dec_mins_to_mins[dec_mins]
    except KeyError:
        logging.warning('Value for dec_mins {} not found in '
                        'decimal_to_interval()'.format(dec_mins))
    interval_str = '{}:{}'.format(hrs, mins)
    return interval_str


def read_nights_naps(engine, infile_name=sys.stdin):
    """
    Read NIGHT and NAP data from infile_name;
    call function to load that data into database.

    :param engine: the db engine
    :param infile_name: read data from file or stdin
    :return: None
    Called by: connect()
    """
    with fileinput.input(infile_name) as data_source:
        connection = engine.connect()
        trans = connection.begin()
        try:
            keep_going = True
            while keep_going:
                my_line = data_source.readline()
                keep_going = store_nights_naps(connection, my_line)
            trans.commit()
        except Exception:
            trans.rollback()
            raise


def store_nights_naps(connection, my_line):
    """
    Insert a line of data into the db

    If the line starts with 'NIGHT':
        insert a night into sl_night
    If the line starts with 'NAP':
        insert a nap into sl_nap

    :param connection: an open db connection
    :param my_line: a line of data from the transform stage
    :return: True if the line was inserted, else False
    Called by read_nights_naps()
    """
    success = False
    line_list = my_line.rstrip().split(', ')
    if line_list[0] == 'NIGHT':
        result = connection.execute(
            func.sl_insert_night(*line_list[1:])
        )
        load_logger.debug(result)
        success = True
    elif line_list[0] == 'NAP':
        result = connection.execute(
            func.sl_insert_nap(line_list[1],
                               decimal_to_interval(line_list[2])
                               )
        )
        load_logger.debug(result)
        success = True
    return success


def connect(url):
    """
    Connect to the PostgreSQL db server;
    invoke read_nights_naps() to load data from input to db_s_etl.

    :param url: the db url
    :return: None
    Called by: client code
    """
    engine = create_engine(url)

    try:
        # if 'True' is a c.l. arg:
        #     if a file name is also a c.l. arg:
        #         read from file name
        #     else:
        #         read from stdin
        sys.argv.remove('True')
        infile_name = sys.argv[1] if len(sys.argv) > 1 else '-'
        read_nights_naps(engine, infile_name)
    except ValueError:
        pass  # don't touch the db


def main():
    """
    Set up root (network) logger and load logger
    Called by: client code
    """
    setup_network_logger()
    return setup_load_logger()


def setup_network_logger():
    """
    Set up a logger to handle messages from all processes
    :return: None
    Called by: main()
    """
    # https://docs.python.org/3/howto/logging-cookbook.html#network-logging
    root_logger = logging.getLogger('')
    root_logger.setLevel(logging.INFO)
    socket_handler = logging.handlers.SocketHandler('localhost',
                                                    logging.handlers.
                                                    DEFAULT_TCP_LOGGING_PORT)
    # don't bother with a formatter here, since a socket handler sends the
    # event as an unformatted pickle
    root_logger.addHandler(socket_handler)
    # end of logging-cookbook code


def setup_load_logger():
    """
    Setup a logger for messages from the load process only
    :return: the load logger
    Called by: main()
    """
    # load_logger will need a formatter since it is writing to file
    load_logger = logging.getLogger('load.load')
    load_logger.setLevel(logging.DEBUG)
    file_handler = logging.FileHandler('src/load/load.log', mode='w')
    formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    load_logger.addHandler(file_handler)
    load_logger.propagate = False

    return load_logger


if __name__ == '__main__':
    load_logger = main()
    logging.info('load start')
    try:
        url = 'postgresql://{}:{}@127.0.0.1/sleep'.format(
                os.environ['DB_USERNAME'], os.environ['DB_PASSWORD'])
    except KeyError:
        print('Please set the environment variables DB_USERNAME and '
              'DB_PASSWORD')
        sys.exit(1)
    connect(url)  # only c.l.a. will be 'True' or 'False'
    logging.info('load finish')
