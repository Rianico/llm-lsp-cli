"""Unit tests for type_helpers module."""

from llm_lsp_cli.utils.type_helpers import (
    get_dict,
    get_int,
    get_list,
    get_list_of_dicts,
    get_optional_dict,
    get_optional_int,
    get_optional_list,
    get_optional_str,
    get_str,
)


class TestGetInt:
    """Tests for get_int function."""

    def test_returns_int_from_dict(self) -> None:
        """Returns integer value from dict."""
        data: dict[str, object] = {"count": 42}
        assert get_int(data, "count") == 42

    def test_returns_default_for_missing_key(self) -> None:
        """Returns default for missing key."""
        data: dict[str, object] = {}
        assert get_int(data, "count", default=10) == 10

    def test_returns_default_for_non_int_value(self) -> None:
        """Returns default when value is not an int."""
        data: dict[str, object] = {"count": "not an int"}
        assert get_int(data, "count") == 0

    def test_returns_default_for_non_dict_input(self) -> None:
        """Returns default when input is not a dict."""
        assert get_int("not a dict", "count") == 0


class TestGetStr:
    """Tests for get_str function."""

    def test_returns_str_from_dict(self) -> None:
        """Returns string value from dict."""
        data: dict[str, object] = {"name": "test"}
        assert get_str(data, "name") == "test"

    def test_returns_default_for_missing_key(self) -> None:
        """Returns default for missing key."""
        data: dict[str, object] = {}
        assert get_str(data, "name", default="default") == "default"

    def test_returns_default_for_non_str_value(self) -> None:
        """Returns default when value is not a string."""
        data: dict[str, object] = {"name": 123}
        assert get_str(data, "name") == ""

    def test_returns_default_for_non_dict_input(self) -> None:
        """Returns default when input is not a dict."""
        assert get_str("not a dict", "name") == ""


class TestGetOptionalStr:
    """Tests for get_optional_str function."""

    def test_returns_str_from_dict(self) -> None:
        """Returns string value from dict."""
        data: dict[str, object] = {"name": "test"}
        assert get_optional_str(data, "name") == "test"

    def test_returns_none_for_missing_key(self) -> None:
        """Returns None for missing key."""
        data: dict[str, object] = {}
        assert get_optional_str(data, "name") is None

    def test_returns_none_for_none_value(self) -> None:
        """Returns None when value is None."""
        data: dict[str, object] = {"name": None}
        assert get_optional_str(data, "name") is None

    def test_returns_none_for_non_str_value(self) -> None:
        """Returns None when value is not a string."""
        data: dict[str, object] = {"name": 123}
        assert get_optional_str(data, "name") is None


class TestGetOptionalInt:
    """Tests for get_optional_int function."""

    def test_returns_int_from_dict(self) -> None:
        """Returns int value from dict."""
        data: dict[str, object] = {"count": 42}
        assert get_optional_int(data, "count") == 42

    def test_returns_none_for_missing_key(self) -> None:
        """Returns None for missing key."""
        data: dict[str, object] = {}
        assert get_optional_int(data, "count") is None

    def test_returns_none_for_none_value(self) -> None:
        """Returns None when value is None."""
        data: dict[str, object] = {"count": None}
        assert get_optional_int(data, "count") is None

    def test_returns_none_for_non_int_value(self) -> None:
        """Returns None when value is not an int."""
        data: dict[str, object] = {"count": "not an int"}
        assert get_optional_int(data, "count") is None


class TestGetList:
    """Tests for get_list function."""

    def test_returns_list_from_dict(self) -> None:
        """Returns list value from dict."""
        data: dict[str, object] = {"items": [1, 2, 3]}
        assert get_list(data, "items") == [1, 2, 3]

    def test_returns_empty_list_for_missing_key(self) -> None:
        """Returns empty list for missing key."""
        data: dict[str, object] = {}
        assert get_list(data, "items") == []

    def test_returns_empty_list_for_non_list_value(self) -> None:
        """Returns empty list when value is not a list."""
        data: dict[str, object] = {"items": "not a list"}
        assert get_list(data, "items") == []

    def test_returns_empty_list_for_non_dict_input(self) -> None:
        """Returns empty list when input is not a dict."""
        assert get_list("not a dict", "items") == []


class TestGetOptionalList:
    """Tests for get_optional_list function."""

    def test_returns_list_from_dict(self) -> None:
        """Returns list value from dict."""
        data: dict[str, object] = {"items": [1, 2, 3]}
        assert get_optional_list(data, "items") == [1, 2, 3]

    def test_returns_none_for_missing_key(self) -> None:
        """Returns None for missing key."""
        data: dict[str, object] = {}
        assert get_optional_list(data, "items") is None

    def test_returns_none_for_none_value(self) -> None:
        """Returns None when value is None."""
        data: dict[str, object] = {"items": None}
        assert get_optional_list(data, "items") is None

    def test_returns_none_for_non_list_value(self) -> None:
        """Returns None when value is not a list."""
        data: dict[str, object] = {"items": "not a list"}
        assert get_optional_list(data, "items") is None


class TestGetDict:
    """Tests for get_dict function."""

    def test_returns_dict_from_dict(self) -> None:
        """Returns dict value from dict."""
        inner: dict[str, object] = {"nested": "value"}
        data: dict[str, object] = {"config": inner}
        assert get_dict(data, "config") == {"nested": "value"}

    def test_returns_empty_dict_for_missing_key(self) -> None:
        """Returns empty dict for missing key."""
        data: dict[str, object] = {}
        assert get_dict(data, "config") == {}

    def test_returns_empty_dict_for_non_dict_value(self) -> None:
        """Returns empty dict when value is not a dict."""
        data: dict[str, object] = {"config": "not a dict"}
        assert get_dict(data, "config") == {}


class TestGetOptionalDict:
    """Tests for get_optional_dict function."""

    def test_returns_dict_from_dict(self) -> None:
        """Returns dict value from dict."""
        inner: dict[str, object] = {"nested": "value"}
        data: dict[str, object] = {"config": inner}
        assert get_optional_dict(data, "config") == {"nested": "value"}

    def test_returns_none_for_missing_key(self) -> None:
        """Returns None for missing key."""
        data: dict[str, object] = {}
        assert get_optional_dict(data, "config") is None

    def test_returns_none_for_none_value(self) -> None:
        """Returns None when value is None."""
        data: dict[str, object] = {"config": None}
        assert get_optional_dict(data, "config") is None

    def test_returns_none_for_non_dict_value(self) -> None:
        """Returns None when value is not a dict."""
        data: dict[str, object] = {"config": "not a dict"}
        assert get_optional_dict(data, "config") is None


class TestGetListOfDicts:
    """Tests for get_list_of_dicts function."""

    def test_returns_list_of_dicts(self) -> None:
        """Returns list of dict values."""
        data: dict[str, object] = {
            "items": [{"a": 1}, {"b": 2}]
        }
        result = get_list_of_dicts(data, "items")
        assert result == [{"a": 1}, {"b": 2}]

    def test_filters_non_dict_items(self) -> None:
        """Filters out non-dict items from list."""
        data: dict[str, object] = {
            "items": [{"a": 1}, "not a dict", {"b": 2}]
        }
        result = get_list_of_dicts(data, "items")
        assert result == [{"a": 1}, {"b": 2}]

    def test_returns_empty_list_for_missing_key(self) -> None:
        """Returns empty list for missing key."""
        data: dict[str, object] = {}
        assert get_list_of_dicts(data, "items") == []

    def test_returns_empty_list_for_non_list_value(self) -> None:
        """Returns empty list when value is not a list."""
        data: dict[str, object] = {"items": "not a list"}
        assert get_list_of_dicts(data, "items") == []

    def test_returns_empty_list_for_non_dict_input(self) -> None:
        """Returns empty list when input is not a dict."""
        assert get_list_of_dicts("not a dict", "items") == []
