"""Heuristic prescription classifier.

PharmaOS provides no prescription flags, so we infer them. This is a SAFETY
default, not medical advice: anything we cannot confidently mark OTC defaults to
requiring pharmacist review. A pharmacist can override any product from Telegram.

Returns (requires_prescription, requires_review).
"""
from __future__ import annotations

# Generic-name fragments that are prescription / controlled and must be reviewed.
_RX_GENERIC_FRAGMENTS = (
    # Antibiotics / antimicrobials
    "amoxicillin", "ampicillin", "augmentin", "azithromycin", "cefuroxime",
    "ceftriaxone", "cefixime", "ciprofloxacin", "levofloxacin", "ofloxacin",
    "metronidazole", "doxycycline", "erythromycin", "clarithromycin",
    "gentamicin", "cloxacillin", "flucloxacillin", "tetracycline", "rifampicin",
    "isoniazid", "fluconazole", "ketoconazole",
    # Controlled substances / CNS
    "tramadol", "codeine", "morphine", "pentazocine", "diazepam", "lorazepam",
    "clonazepam", "alprazolam", "phenobarbital", "pregabalin", "gabapentin",
    "amitriptyline", "fluoxetine", "sertraline", "haloperidol", "olanzapine",
    "risperidone", "carbamazepine", "phenytoin", "methadone",
    # Cardiovascular / chronic Rx
    "warfarin", "clopidogrel", "insulin", "metformin", "glibenclamide",
    "amlodipine", "lisinopril", "losartan", "atenolol", "bisoprolol",
    "hydrochlorothiazide", "furosemide", "atorvastatin", "simvastatin",
    "digoxin", "spironolactone",
    # Steroids / hormones
    "prednisolone", "dexamethasone", "hydrocortisone", "methylprednisolone",
    "salbutamol", "estradiol", "testosterone",
)

# Dosage forms that always need pharmacist handling/review.
_RX_DOSAGE_FORMS = (
    "injection", "powder for injection", "solution for injection",
    "infusion", "implant", "intravenous", "iv",
)

# Categories that are clearly not freely-OTC consumer drugs.
_REVIEW_CATEGORIES = ("vaccines and biologics", "veterinary")

# Generic-name fragments that are safely OTC (common pharmacy counter items).
_OTC_GENERIC_FRAGMENTS = (
    "paracetamol", "acetaminophen", "ibuprofen", "aspirin", "vitamin",
    "multivitamin", "ascorbic", "folic acid", "zinc", "calcium", "ors",
    "oral rehydration", "antacid", "magnesium trisilicate", "loratadine",
    "cetirizine", "chlorpheniramine", "hand sanitizer", "glucose",
)

_OTC_FORMS = ("tablet", "caplet", "capsule", "syrup", "suspension", "lozenge")


def _norm(s: str | None) -> str:
    return (s or "").strip().lower()


def classify(
    name: str | None,
    generic: str | None = None,
    dosage_form: str | None = None,
    category: str | None = None,
) -> tuple[bool, bool]:
    """Return (requires_prescription, requires_review)."""
    text = " ".join(_norm(x) for x in (name, generic))
    form = _norm(dosage_form)
    cat = _norm(category)

    # 1. Prescription / controlled drug names -> Rx + review.
    if any(frag in text for frag in _RX_GENERIC_FRAGMENTS):
        return True, True

    # 2. Injectables and similar -> review (treated as Rx-grade).
    if any(f in form for f in _RX_DOSAGE_FORMS):
        return True, True

    # 3. Vaccines / veterinary -> review.
    if any(c in cat for c in _REVIEW_CATEGORIES):
        return False, True

    # 4. Clearly-OTC names in an oral/topical form -> sellable without review.
    if any(frag in text for frag in _OTC_GENERIC_FRAGMENTS) and (form in _OTC_FORMS or not form):
        return False, False

    # 5. Default: unknown -> require review before sale (safety first).
    return False, True
