"""Word lists shared by the recognizers and the span resolver (no heavy imports)."""
import re

HONORIFICS = [
    "Tan Sri", "Puan Sri", "Toh Puan", "Dato' Sri", "Datuk Seri", "Dato Sri", "Dato'", "Dato",
    "Datuk", "Datin Paduka", "Datin", "Tun", "Tengku", "Tunku", "Raja", "Syed", "Sharifah",
    "Encik", "En.", "Puan", "Pn.", "Cik", "Tuan", "Tn.", "Haji", "Hj.", "Hj", "Hajah", "Hjh.",
    "Hjh", "Dr.", "Dr", "Prof.", "Prof", "Ir.", "Ir", "Mr.", "Mr", "Mrs.", "Mrs", "Ms.", "Ms",
    "Madam", "Mdm.", "Mdm", "Sdr.", "Sdri.", "Saudara", "Saudari", "Ustaz", "Ustazah", "Cikgu",
]
# Titles that are part of a hereditary name (Syed, Tengku) are kept inside the token.
STRIP_TITLES = [h for h in HONORIFICS if h not in ("Syed", "Sharifah", "Tengku", "Tunku", "Raja")]
_TITLE_ALT = "|".join(re.escape(h) for h in sorted(HONORIFICS, key=len, reverse=True))
STRIP_TITLE_RE = re.compile(
    r"^(?:(?:" + "|".join(re.escape(h) for h in sorted(STRIP_TITLES, key=len, reverse=True))
    + r")(?:\s+|(?<=\.)))+", re.IGNORECASE)

CHINESE_SURNAMES = [
    "Tan", "Lim", "Lee", "Ng", "Wong", "Chan", "Ong", "Teh", "Goh", "Chong", "Leong", "Yap", "Low",
    "Chin", "Liew", "Ho", "Koh", "Cheah", "Khoo", "Lau", "Foo", "Kok", "Loh", "Teoh", "Yeoh", "Soo",
    "Chua", "Choo", "Tay", "Siow", "Chew", "Ooi", "Cheong", "Yong", "Tee", "Heng", "Hew", "Chia",
    "Lai", "Kang", "Phang", "Wan", "Sim", "Seow", "Pang", "Liow", "Kua", "Chai", "Chiew", "Gan",
    "Yeo", "Hoo", "Loke", "Leow", "Thong", "Fong", "Kwan", "Lew", "Mok", "Quek", "Toh", "Wee",
]

MY_STATES = [
    "Johor", "Kedah", "Kelantan", "Melaka", "Malacca", "Negeri Sembilan", "Pahang", "Perak",
    "Perlis", "Pulau Pinang", "Penang", "Sabah", "Sarawak", "Selangor", "Terengganu",
    "Kuala Lumpur", "Wilayah Persekutuan Kuala Lumpur", "W.P. Kuala Lumpur", "WP Kuala Lumpur",
    "Labuan", "W.P. Labuan", "Putrajaya", "W.P. Putrajaya", "Johor Darul Takzim",
    "Selangor Darul Ehsan", "Malaysia",
]
