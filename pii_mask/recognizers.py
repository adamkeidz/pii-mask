"""Malaysian PII recognizers for Presidio (regex plus validation)."""
import re
from presidio_analyzer import Pattern, PatternRecognizer

from .lists import HONORIFICS, CHINESE_SURNAMES, MY_STATES, STRIP_TITLE_RE, _TITLE_ALT  # noqa: F401

# Presidio compiles with IGNORECASE by default; name and org patterns depend on capitals.
FLAGS = re.DOTALL | re.MULTILINE

# Place-of-birth codes printed on MyKad (JPN). 00, 17-20, 69, 70, 73, 80, 81, 94-97 are unused.
_PB_VALID = set(range(1, 17)) | set(range(21, 60)) | set(range(60, 69)) | {71, 72} \
    | set(range(74, 80)) | set(range(82, 94)) | {98, 99}
_DAYS = [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]

# A name word: Capitalised or ALL CAPS, allows Mohd., Nur', Abd-Rahman, @ aliases.
_W = r"(?:[A-Z][a-z'\-]+\.?|[A-Z]{2,}\.?|[A-Z]\.)"
_WS = r"[ \t]+"
_CONNECT = r"(?:bin|binti|bte|bt\.?|b\.|binte|a/l|a/p|s/o|d/o|anak|ak\.?|@)"




def _date_ok(yy: int, mm: int, dd: int) -> bool:
    if not 1 <= mm <= 12 or dd < 1:
        return False
    if mm == 2 and dd == 29:
        return yy % 4 == 0  # 1900 is not a plausible birth year for a live MyKad, 2000 is leap
    return dd <= _DAYS[mm - 1]


class MyKadRecognizer(PatternRecognizer):
    PATTERNS = [
        Pattern("mykad_dashed", r"(?<![\d\w])\d{6}[ -]\d{2}[ -]\d{4}(?![\d\w])", 0.85),
        Pattern("mykad_plain", r"(?<![\d\w-])\d{12}(?![\d\w])", 0.55),
    ]
    CONTEXT = ["ic", "nric", "mykad", "mykid", "kp", "kad", "pengenalan", "identity", "identification",
               "no.kp", "i/c", "ic no"]

    def __init__(self):
        super().__init__(supported_entity="IC", patterns=self.PATTERNS, context=self.CONTEXT,
                         name="MyKadRecognizer", global_regex_flags=FLAGS)

    def validate_result(self, pattern_text: str):
        d = re.sub(r"\D", "", pattern_text)
        if len(d) != 12:
            return False
        if not _date_ok(int(d[0:2]), int(d[2:4]), int(d[4:6])):
            return False
        return int(d[6:8]) in _PB_VALID


class TinRecognizer(PatternRecognizer):
    # IG/SG/OG individuals; C, CS, D, E, F, FA, PT, TA, TC, TN, TR, TP, J, LE non-individuals.
    PATTERNS = [
        Pattern("tin_ig", r"(?<![A-Za-z\d])(?:IG|SG|OG)[ -]?\d{9,13}(?!\d)", 0.85),
        Pattern("tin_multi", r"(?<![A-Za-z\d])(?:CS|FA|PT|TA|TC|TN|TR|TP|LE)[ -]?\d{8,13}(?!\d)", 0.8),
        Pattern("tin_single", r"(?<![A-Za-z\d])[CDEFJ]\d{8,13}(?!\d)", 0.6),
    ]
    CONTEXT = ["tin", "cukai", "lhdn", "tax", "income", "pengenalan", "taxpayer", "no.cukai"]

    def __init__(self):
        super().__init__(supported_entity="TIN", patterns=self.PATTERNS, context=self.CONTEXT,
                         name="TinRecognizer", global_regex_flags=FLAGS)


class BrnRecognizer(PatternRecognizer):
    PATTERNS = [
        # New SSM format: YYYY + entity type (01-06) + 6 digits, optional old number in brackets.
        Pattern("brn_new", r"(?<![\d\w])(?:19[5-9]\d|20[0-4]\d)0[1-6]\d{6}(?![\d\w])", 0.6),
        Pattern("brn_old", r"(?<![\d\w-])\d{4,7}[ -]?[A-Z](?![\w-])", 0.1),
        Pattern("brn_old_dash", r"(?<![\d\w-])\d{4,7}-[A-Z](?![\w-])", 0.6),
    ]
    CONTEXT = ["ssm", "brn", "roc", "rob", "registration", "pendaftaran", "company", "syarikat",
               "sdn", "bhd", "berhad", "business", "perniagaan", "reg"]

    def __init__(self):
        super().__init__(supported_entity="BRN", patterns=self.PATTERNS, context=self.CONTEXT,
                         name="BrnRecognizer", global_regex_flags=FLAGS)

    def validate_result(self, pattern_text: str):
        t = pattern_text.strip()
        if re.fullmatch(r"\d{4,7}[A-Z]", t) or re.fullmatch(r"\d{4,7} [A-Z]", t):
            return None  # undecided, keep base score (needs context to pass the threshold)
        return True


_SEP = r"[ \-.]?"


class MyPhoneRecognizer(PatternRecognizer):
    PATTERNS = [
        Pattern("my_mobile",
                r"(?<![\d\w+])(?:\+?60[ \-]?|0)1\d" + _SEP + r"\d{3,4}" + _SEP + r"\d{4}(?!\d)", 0.75),
        Pattern("my_land_kl",
                r"(?<![\d\w+])(?:\+?60[ \-]?\(?|\(?0)3\)?" + _SEP + r"\d{4}" + _SEP + r"\d{4}(?!\d)", 0.7),
        Pattern("my_land_state",
                r"(?<![\d\w+])(?:\+?60[ \-]?\(?|\(?0)[4-79]\)?" + _SEP + r"\d{3}" + _SEP + r"\d{4}(?!\d)", 0.65),
        Pattern("my_land_east",
                r"(?<![\d\w+])(?:\+?60[ \-]?\(?|\(?0)8[2-9]\)?" + _SEP + r"\d{3}" + _SEP + r"\d{3,4}(?!\d)", 0.65),
    ]
    CONTEXT = ["tel", "telefon", "phone", "hp", "h/p", "mobile", "bimbit", "call", "whatsapp", "wa",
               "fax", "faks", "hubungi", "contact"]

    def __init__(self):
        super().__init__(supported_entity="PHONE", patterns=self.PATTERNS, context=self.CONTEXT,
                         name="MyPhoneRecognizer", global_regex_flags=FLAGS)


class EmailRegexRecognizer(PatternRecognizer):
    """Email without tldextract (Presidio's built-in one may fetch the public suffix list)."""
    PATTERNS = [Pattern("email",
                        r"(?<![\w.%+-])[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,24}\b",
                        0.9)]

    def __init__(self):
        super().__init__(supported_entity="EMAIL", patterns=self.PATTERNS, name="EmailRegexRecognizer", global_regex_flags=FLAGS)


class MalayNameRecognizer(PatternRecognizer):
    PATTERNS = [
        # X bin Y / X a/l Y / X anak Y
        Pattern("patronymic",
                r"(?<![\w])" + _W + r"(?:" + _WS + _W + r"){0,3}" + _WS + r"(?i:" + _CONNECT + r")"
                + _WS + _W + r"(?:" + _WS + _W + r"){0,3}", 0.85),
        # Honorific + 1 to 4 name words
        Pattern("honorific",
                r"(?<![\w])(?:(?i:" + _TITLE_ALT + r")" + _WS + r")+" + _W + r"(?:" + _WS + _W + r"){0,3}",
                0.7),
        # Chinese style: Surname + 1 or 2 given-name words (Tan Wei Ming)
        Pattern("chinese",
                r"(?<![\w])(?:" + "|".join(CHINESE_SURNAMES) + r"|"
                + "|".join(s.upper() for s in CHINESE_SURNAMES) + r")" + _WS
                + r"(?!Sri\b|SRI\b|Bhd\b|BHD\b)" + _W + r"(?:" + _WS + _W + r")?(?![\w])", 0.45),
    ]

    def __init__(self):
        super().__init__(supported_entity="NAME", patterns=self.PATTERNS, name="MalayNameRecognizer", global_regex_flags=FLAGS)


_ORG_SUFFIX = (r"(?:Sdn\.?[ ]?Bhd\.?|SDN\.?[ ]?BHD\.?|Berhad|BERHAD|Bhd\.?|BHD\.?|PLT|Enterprise|ENTERPRISE"
               r"|Trading|TRADING|Holdings|HOLDINGS|Resources|RESOURCES|Ventures|VENTURES|Industries"
               r"|Corporation|Corp\.?|Ltd\.?|LTD\.?|Limited|Inc\.?|LLP|Co\.|Services|SERVICES|Solutions"
               r"|SOLUTIONS|Technologies|Engineering|Construction|Logistics|Consultancy|Agency|Clinic"
               r"|Klinik|Restoran|Kedai|Pharmacy|Farmasi)")


class OrgSuffixRecognizer(PatternRecognizer):
    PATTERNS = [
        Pattern("org_suffix",
                r"(?<![\w])(?:[A-Z0-9][\w&'.\-]*" + _WS + r"){0,5}(?:[A-Z0-9][\w&'.\-]*)" + _WS
                + r"(?:\(M\)" + _WS + r")?" + _ORG_SUFFIX + r"(?![\w])", 0.6),
        Pattern("org_prefix",
                r"(?<![\w])(?:Syarikat|Kedai|Restoran|Klinik|Pusat|Persatuan)" + _WS + _W
                + r"(?:" + _WS + r"(?:" + _W + r"|&|\d+))" + r"{0,5}", 0.55),
    ]

    def __init__(self):
        super().__init__(supported_entity="ORG", patterns=self.PATTERNS, name="OrgSuffixRecognizer", global_regex_flags=FLAGS)


_STREET = (r"(?:Jalan|Jln\.?|Lorong|Lrg\.?|Persiaran|Psrn\.?|Lebuh|Lebuhraya|Lengkok|Lingkaran|Medan"
           r"|Taman|Tmn\.?|Kampung|Kampong|Kg\.?|Bandar|Bdr\.?|Desa|Pangsapuri|Kondominium|Apartment"
           r"|Apartmen|Residensi|Flat|Blok|Block|Bangunan|Wisma|Menara|Plaza|Kompleks|Seksyen|Section"
           r"|Batu|Simpang|Street|Road|Avenue|Jalan)")


class MyAddressRecognizer(PatternRecognizer):
    """Address fragments; the masker merges adjacent fragments into one span."""
    PATTERNS = [
        Pattern("street", r"(?<![\w])(?i:" + _STREET + r")\.?" + _WS + r"(?:[A-Z0-9][\w'/\-.]*)(?:" + _WS
                + r"(?:[A-Z0-9][\w'/\-.]*|\d+[A-Z]?(?:/\d+[A-Z]?)*))" + r"{0,4}", 0.6),
        Pattern("unit", r"(?<![\w])(?:No\.?|NO\.?|Lot|LOT|Unit|UNIT|PT|Tingkat|Aras|Level|Blok|BLOK|Block|Suite)" + _WS
                + r"\d{1,5}[A-Z]?(?:[\-/]\d+[A-Z]?){0,3}\b", 0.5),
        Pattern("postcode_city", r"(?<![\d\w])\d{5}" + _WS + r"[A-Z][A-Za-z'.]+(?:" + _WS
                + r"[A-Z][A-Za-z'.]+){0,3}", 0.6),
        Pattern("unit_bare", r"(?<![\w\-/])(?:[A-Z]{1,2}-)?\d{1,4}[A-Z]?(?:-\d{1,3}){1,3}(?=,\s*" + _STREET + r")", 0.5),
        Pattern("unit_num", r"(?<![\w\-/])\d{1,4}[A-Z]?(?=,?\s+" + _STREET + r")", 0.5),
    ]

    def __init__(self):
        super().__init__(supported_entity="ADDRESS", patterns=self.PATTERNS, name="MyAddressRecognizer", global_regex_flags=FLAGS)


class BankAccountRecognizer(PatternRecognizer):
    PATTERNS = [Pattern("acct", r"(?<![\d\w-])\d{10,16}(?![\d\w])", 0.1),
                Pattern("acct_dash", r"(?<![\d\w-])\d{3,6}(?:[ -]\d{2,8}){1,3}(?![\d\w-])", 0.1)]
    CONTEXT = ["account", "akaun", "acc", "a/c", "acct", "bank", "maybank", "cimb", "rhb", "hlb",
               "public", "ambank", "bsn", "islam", "muamalat", "rakyat", "affin", "alliance", "ocbc",
               "uob", "hsbc", "agrobank", "transfer", "pindahan"]

    def __init__(self):
        super().__init__(supported_entity="ACCT", patterns=self.PATTERNS, context=self.CONTEXT,
                         name="BankAccountRecognizer", global_regex_flags=FLAGS)


def all_recognizers():
    return [MyKadRecognizer(), TinRecognizer(), BrnRecognizer(), MyPhoneRecognizer(),
            EmailRegexRecognizer(), MalayNameRecognizer(), OrgSuffixRecognizer(),
            MyAddressRecognizer(), BankAccountRecognizer()]
