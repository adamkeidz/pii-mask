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

# ---------------------------------------------------------------- name parts
# Words that link a given name to a father's name (or an alias). Everything from the first one on is
# the father's side and is never masked on its own: "Siti binti Demo" -> "Siti".
NAME_CONNECTORS = {"bin", "binti", "bte", "bt", "bt.", "b.", "binte", "a/l", "a/p", "s/o", "d/o",
                   "anak", "ak", "ak."}
# Prefixes that identify nobody on their own ("Siti Hajar" is called "Hajar"). Kept only when they
# are the whole given name, as in "Siti binti Demo".
NAME_PREFIXES = {"mohd", "md", "muhammad", "muhamad", "mohamad", "mohammad", "mohamed", "mohammed",
                 "nur", "nurul", "nor", "noor", "siti", "abdul", "abd", "ab", "wan", "nik", "che",
                 "syed", "sharifah", "tengku", "tunku", "raja", "megat", "puteri", "awang", "dayang"}
# A lone part is masked across the whole batch, so it must not be an everyday word or a place:
# "April", "Grace", "Indah" or "Jaya" can be a given name and also appear in normal text.
PART_STOP = {w.casefold() for w in [
    # placeholders used in demo data
    "Demo", "Contoh", "Sample", "Sampel", "Ujian", "Test",
    # very common given-name words that identify nobody
    "Kumar", "Devi",
    # months and days
    "January", "February", "March", "April", "May", "June", "July", "August", "September",
    "October", "November", "December", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday",
    "Saturday", "Sunday", "Januari", "Februari", "Mac", "Mei", "Julai", "Ogos", "Oktober",
    "Disember", "Isnin", "Selasa", "Rabu", "Khamis", "Jumaat", "Sabtu", "Ahad",
    # English words that are also given names
    "Grace", "Hope", "Joy", "Faith", "Will", "Mark", "Rose", "Bill", "Summer", "Dawn", "Rich",
    "Sunny", "Holly", "Ivy", "Lily", "Daisy", "Iris", "Pearl", "Ruby", "Crystal", "Amber", "Jade",
    "Angel", "King", "Queen", "Prince", "Young", "Long", "Page", "Hall", "Grant", "Frank", "Art",
    "Victory", "Star", "Sky", "Dear", "Thank", "Thanks", "Please", "Regards", "Office", "Account",
    # Malay words that are also given names
    "Indah", "Jaya", "Seri", "Sri", "Cahaya", "Bintang", "Bulan", "Intan", "Mutiara", "Permata",
    "Bunga", "Mawar", "Melati", "Kenanga", "Suria", "Putra", "Putri", "Ratna", "Murni", "Setia",
    "Harapan", "Bahagia", "Sentosa", "Makmur", "Maju", "Baru", "Utama", "Emas", "Budi", "Bakti",
    "Merdeka", "Raya", "Aman", "Damai", "Bayu", "Embun", "Salam", "Selamat", "Permai", "Ria",
    # places
    "Malaysia", "Singapore", "Kuala", "Lumpur", "Johor", "Bahru", "Bharu", "Petaling", "Shah",
    "Alam", "Kota", "Kinabalu", "Kuching", "Ipoh", "Kajang", "Cheras", "Klang", "Subang",
    "Puchong", "Seremban", "Melaka", "Malacca", "Penang", "Pinang", "Pulau", "Bandar", "Taman",
    "Jalan", "Kampung", "Bukit", "Sungai", "Batu", "Tanjung", "Teluk", "Putrajaya", "Cyberjaya",
    "Ampang", "Gombak", "Kepong", "Rawang", "Nilai", "Muar", "Kedah", "Kelantan", "Pahang",
    "Perak", "Perlis", "Sabah", "Sarawak", "Selangor", "Terengganu", "Labuan", "Negeri",
    "Sembilan", "Kuantan", "Bayan", "Lepas", "Ayer", "Keroh",
]}
