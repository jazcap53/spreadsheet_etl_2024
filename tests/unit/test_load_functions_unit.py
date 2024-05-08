import logging

from src.load.load import decimal_to_interval, setup_network_logger, setup_load_logger


def test_decimal_to_interval_valid_input():
    assert decimal_to_interval('3.25') == '3:15'
    assert decimal_to_interval('1.50') == '1:30'
    assert decimal_to_interval('0.00') == '0:00'


def test_decimal_to_interval_invalid_input(caplog):
    caplog.set_level(logging.WARNING)
    assert decimal_to_interval('2.80') == '2:None'
    assert "Value for dec_mins 80 not found in decimal_to_interval()" in caplog.text


def test_setup_network_logger(caplog):
    caplog.set_level(logging.INFO)
    setup_network_logger()
    root_logger = logging.getLogger('')
    assert any(level == logging.INFO for level in [handler.level for handler in root_logger.handlers])
    assert any(isinstance(handler, logging.handlers.SocketHandler) for handler in root_logger.handlers)
    assert any(handler.host == 'localhost' for handler in root_logger.handlers
               if isinstance(handler, logging.handlers.SocketHandler))
    assert any(handler.port == logging.handlers.DEFAULT_TCP_LOGGING_PORT for handler in root_logger.handlers
               if isinstance(handler, logging.handlers.SocketHandler))


def test_setup_load_logger():
    load_logger = setup_load_logger()
    assert load_logger.name == 'load.load'
    assert load_logger.level == logging.DEBUG
    assert len(load_logger.handlers) == 1
    assert isinstance(load_logger.handlers[0], logging.FileHandler)
    # assert load_logger.handlers[0].baseFilename == 'src/load/load.log'
    assert load_logger.handlers[0].baseFilename.endswith('src/load/load.log')
    assert load_logger.handlers[0].mode == 'w'
    assert load_logger.propagate == False