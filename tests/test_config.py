from app.core.config import Settings, _parse_emails, _parse_ids


def test_parse_ids_basic():
    assert _parse_ids("111, 222 ,333") == {111, 222, 333}


def test_parse_ids_ignores_blanks_and_garbage():
    assert _parse_ids(" , 111, abc, ") == {111}
    assert _parse_ids("") == set()


def test_parse_emails():
    assert _parse_emails("a@x.com, b@y.com ") == ["a@x.com", "b@y.com"]


def test_role_id_properties():
    s = Settings(
        owner_telegram_ids="111,222",
        pharmacist_telegram_ids="333",
        _env_file=None,
    )
    assert s.owner_ids == {111, 222}
    assert s.pharmacist_ids == {333}
    assert s.packaging_ids == set()


def test_emails_for_role():
    s = Settings(owner_emails="boss@peaceway.ng", _env_file=None)
    assert s.emails_for("owner") == ["boss@peaceway.ng"]
    assert s.emails_for("dispatcher") == []


def test_flutterwave_disabled_when_no_keys():
    s = Settings(_env_file=None)
    assert s.flutterwave_enabled is False
