from guardette.utils import copy_signature


def test_copy_signature_returns_the_decorated_function():
    def source():
        return None

    def decorated(value):
        return value

    result = copy_signature(source)(decorated)

    assert result is decorated
    assert result("value") == "value"
