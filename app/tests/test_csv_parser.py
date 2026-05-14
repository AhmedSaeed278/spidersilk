import pytest

from spidersilk.csv_parser import CsvParseError, parse_all


def test_parse_basic():
    raw = (
        b'"211627629","Purple Safi Kaftan","4900.0000"\n'
        b'"211622324","White Logo-T-Shirt"," 450.0000"\n'
    )
    rows = parse_all(raw)
    assert len(rows) == 2
    assert rows[0].sku == "211627629"
    assert rows[0].name == "Purple Safi Kaftan"
    assert rows[0].price == 4900.0
    assert rows[1].price == 450.0


def test_skips_blank_lines():
    raw = b'"1","a","1.0"\n\n"2","b","2.0"\n'
    rows = parse_all(raw)
    assert len(rows) == 2


def test_rejects_wrong_column_count():
    raw = b'"1","a"\n'
    with pytest.raises(CsvParseError):
        parse_all(raw)


def test_rejects_bad_price():
    raw = b'"1","a","not-a-number"\n'
    with pytest.raises(CsvParseError):
        parse_all(raw)
