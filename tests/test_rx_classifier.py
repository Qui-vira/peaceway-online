from app.services.rx_classifier import classify


def test_antibiotic_is_rx_and_review():
    assert classify("Amoxil 500", "Amoxicillin", "Capsule", "Drugs") == (True, True)


def test_controlled_substance_is_rx():
    rx, review = classify("Tramal", "Tramadol", "Capsule", "Drugs")
    assert rx is True and review is True


def test_injection_requires_review():
    rx, review = classify("SomeDrug Injection", "Whatever", "Solution for injection", "Drugs")
    assert review is True


def test_plain_paracetamol_is_otc():
    assert classify("Panadol", "Paracetamol", "Tablet", "Drugs") == (False, False)


def test_vitamin_is_otc():
    assert classify("Vitamin C 1000", "Ascorbic Acid", "Tablet", "Herbals and Nutraceuticals") == (
        False,
        False,
    )


def test_vaccine_requires_review_not_rx():
    assert classify("Hepatitis B Vaccine", "Vaccine", "Injection", "Vaccines and Biologics") == (
        True,
        True,
    )


def test_unknown_defaults_to_review():
    rx, review = classify("Zynatac Tablets", "Unknown Compound", "Tablet", "Drugs")
    assert rx is False and review is True
