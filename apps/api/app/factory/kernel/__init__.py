"""The trusted kernel: pure standard library, small enough to read in one sitting.

Nothing outside this package can build a Certificate. Plugins (SymPy, Hypothesis, Z3, round-trip
checks, LLM drafts) produce data and rejections only. See docs/adr for the design.
"""

from app.factory.kernel.certificate import (
    KERNEL_VERSION,
    Certificate,
    CertificationRefused,
    MethodResult,
    PluginVerdict,
    certificate_is_current,
    mint_item_certificate,
)
from app.factory.kernel.certify import (
    OK,
    BoxReport,
    Outcome,
    certify_template,
    clopper_pearson_upper,
    fail,
    skip,
)
from app.factory.kernel.constants import CONSTANTS_VERSION, constants_hash
from app.factory.kernel.verify import DOMAINS, KERNEL_GROUP, Verdict, verify

__all__ = [
    "DOMAINS",
    "KERNEL_GROUP",
    "KERNEL_VERSION",
    "OK",
    "CONSTANTS_VERSION",
    "BoxReport",
    "Certificate",
    "CertificationRefused",
    "MethodResult",
    "Outcome",
    "PluginVerdict",
    "Verdict",
    "certificate_is_current",
    "certify_template",
    "clopper_pearson_upper",
    "constants_hash",
    "fail",
    "mint_item_certificate",
    "skip",
    "verify",
]
