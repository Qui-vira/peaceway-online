from app.bot.customer.checkout import _STEP_BACK, _STEP_STATE, _STEP_TEXT


def test_step_maps_cover_same_keys():
    # Every text-input step must have a prompt, a state, and a back target.
    assert set(_STEP_TEXT) == set(_STEP_STATE) == set(_STEP_BACK)


def test_back_chain_has_no_self_reference():
    for step, target in _STEP_BACK.items():
        assert target != f"checkout:back:{step}"


def test_back_chain_reaches_a_real_screen_eventually():
    # Walking "name"'s back target should NOT be another checkout:back: callback
    # (it goes straight to the real cart:view screen).
    assert _STEP_BACK["name"] == "cart:view"
