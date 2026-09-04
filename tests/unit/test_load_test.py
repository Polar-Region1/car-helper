import pytest

from scripts.load_test import _parse_sse, parse_args


def test_parse_sse_supports_multiline_data():
    event, payload = _parse_sse('event: content\ndata: {"text":\ndata: "车型"}')

    assert event == "content"
    assert payload == {"text": "车型"}


def test_load_test_arguments_are_bounded():
    with pytest.raises(SystemExit):
        parse_args(["--users", "0"])
    with pytest.raises(SystemExit):
        parse_args(["--timeout", "0"])
    with pytest.raises(SystemExit):
        parse_args(["--message", "   "])
