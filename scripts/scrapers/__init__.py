"""Per-manufacturer scrapers. One module each, because every site differs.

Registered here so the orchestrator can run one or all of them by name.
"""
from __future__ import annotations

from . import ac_drugs, afrab_chem, emzor, embassy_pharma, greenlife, may_baker

# name -> module. The name is what you pass to --manufacturer on the CLI.
SCRAPERS = {
    "emzor": emzor,
    "afrab-chem": afrab_chem,
    "greenlife": greenlife,
    "embassy": embassy_pharma,
    "may-baker": may_baker,
    "ac-drugs": ac_drugs,
}

__all__ = ["SCRAPERS"]
