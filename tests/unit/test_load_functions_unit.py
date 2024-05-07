import logging

from src.load.load import decimal_to_interval


def test_decimal_to_interval_valid_input():
    assert decimal_to_interval('3.25') == '3:15'
    assert decimal_to_interval('1.50') == '1:30'
    assert decimal_to_interval('0.00') == '0:00'


def test_decimal_to_interval_invalid_input(caplog):
    caplog.set_level(logging.WARNING)
    assert decimal_to_interval('2.80') == '2:None'
    assert "Value for dec_mins 80 not found in decimal_to_interval()" in caplog.text
