"""Regression test suite for locale-aware numeric and currency sanitization."""

import pytest
from app.core.numeric import (
    detect_csv_delimiter,
    is_blank_marker,
    sanitize_currency,
    sanitize_integer,
    sanitize_percent,
)


@pytest.mark.parametrize(
    "input_val, expected",
    [
        ("Rp 50.000", 50000.0),
        ("Rp 100.000", 100000.0),
        ("-Rp 1.000", -1000.0),
        ("(1.000)", -1000.0),
        ("(100.000)", -100000.0),
        ("261.911.314", 261911314.0),
        ("261.911.314,50", 261911314.50),
        ("149.000", 149000.0),
        (None, 0.0),
        ("", 0.0),
        ("-", 0.0),
        ("--", 0.0),
        ("n/a", 0.0),
        ("#DIV/0!", 0.0),
        (150000, 150000.0),
        (150000.5, 150000.5),
        ("Rp 1.500.000,75", 1500000.75),
    ],
)
def test_sanitize_currency_id_id(input_val, expected):
    """Verifies that currency strings under Indonesian formatting parse with 100% precision."""
    assert sanitize_currency(input_val) == pytest.approx(expected)


@pytest.mark.parametrize(
    "input_val, expected",
    [
        ("$1,500.50", 1500.50),
        ("1,500,000.00", 1500000.00),
        ("(500.25)", -500.25),
    ],
)
def test_sanitize_currency_en_us(input_val, expected):
    """Verifies that explicit override for US/English decimal separator works accurately."""
    assert sanitize_currency(input_val, decimal_sep=".") == pytest.approx(expected)


@pytest.mark.parametrize(
    "input_val, expected",
    [
        (5, 5),
        ("5", 5),
        ("Rp 50.000", 50000),
        (2.4, 2),
        (2.5, 3),
        (2.6, 3),
        (-2.4, -2),
        (-2.5, -3),
        (-2.6, -3),
        ("2,4", 2),
        ("2,5", 3),
        ("2,6", 3),
        ("-2,4", -2),
        ("-2,5", -3),
        ("-2,6", -3),
        ("149.000,4", 149000),
        ("149.000,6", 149001),
        (None, 0),
        ("-", 0),
    ],
)
def test_sanitize_integer_rounding(input_val, expected):
    """Verifies half-away-from-zero rounding behavior for integer quantities."""
    assert sanitize_integer(input_val) == expected


def test_sanitize_integer_en_us_override():
    """Verifies integer rounding with explicit English decimal separator override."""
    assert sanitize_integer("2.4", decimal_sep=".") == 2
    assert sanitize_integer("2.5", decimal_sep=".") == 3
    assert sanitize_integer("-2.5", decimal_sep=".") == -3


@pytest.mark.parametrize(
    "input_val, expected",
    [
        ("3,05%", 0.0305),
        ("5,974791292%", 0.05974791292),
        ("100%", 1.0),
        ("0%", 0.0),
        (0.0597, 0.0597),
        (None, 0.0),
        ("-", 0.0),
    ],
)
def test_sanitize_percent(input_val, expected):
    """Verifies percentage strings convert to exact 0-1 float ratios."""
    assert sanitize_percent(input_val) == pytest.approx(expected)


@pytest.mark.parametrize(
    "marker, is_blank",
    [
        (None, True),
        ("", True),
        ("-", True),
        ("--", True),
        ("N/A", True),
        ("null", True),
        ("#DIV/0!", True),
        ("#VALUE!", True),
        ("Active", False),
        ("0", False),
        (0, False),
    ],
)
def test_is_blank_marker(marker, is_blank):
    """Verifies blank and error placeholder cell identification."""
    assert is_blank_marker(marker) is is_blank


@pytest.mark.parametrize(
    "content, expected",
    [
        (b"header1,header2,header3\nval1,val2,val3\n", ","),
        (b"header1;header2;header3\nval1;val2;val3\n", ";"),
        (b"header1\theader2\theader3\nval1\tval2\tval3\n", "\t"),
        (b"", ","),
        # R6: comma-bearing quoted titles must not flip a ';'-delimited file,
        # at either 2-column or 5-column width.
        (
            b'"Produk";"Nama Variasi"\n'
            b'"Raecca Glow Up Tint, Lip Tint, Lip & Cheek";"05. Dynamic"\n'
            b'"Raecca Over The Glaze, Cute, Matte";"Ov Cute"\n',
            ";",
        ),
        (
            b'"Produk";"Nama Variasi";"SKU";"Qty";"GMV"\n'
            b'"Raecca Glow Up Tint, Lip Tint, Lip & Cheek, Waterproof, Long Lasting, 2pcs";"05. Dynamic";"SKU1";"2";"298.000"\n'
            b'"Raecca Tinted Jelly Balm, Bunny Pink, Sheer";"Bunny Pink";"SKU2";"1";"149.000"\n',
            ";",
        ),
        # R6: ragged rows (uneven column counts) make csv.Sniffer raise; the
        # counting fallback must still pick the clear delimiter majority.
        (b"Produk;Variasi;GMV\nA;B;1000\nC;D\nE;F;G;H\n", ";"),
    ],
)
def test_detect_csv_delimiter(content: bytes, expected: str):
    """Verifies CSV delimiter sniffer across comma, semicolon, and tab,
    including quote-aware handling of comma-bearing quoted titles (R6)."""
    assert detect_csv_delimiter(content) == expected
