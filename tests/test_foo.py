from sms_api.foo import foo


def test_foo() -> None:
    assert foo("foo") == "foo"
