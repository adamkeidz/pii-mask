"""Generates a FAKE Malaysian test set and its ground truth. Every value is invented: phones use the
unused 000 exchange, emails use example.com/net/org, companies are Demo/Contoh/Sampel names,
streets are Demo/Contoh/Sampel/Ujian style. Run: python gen_testdata.py [seed] [rows]"""
import csv
import json
import os
import random
import sys
from email.message import EmailMessage

HERE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
OUT = os.path.join(HERE, "input")
rnd = random.Random(int(sys.argv[1]) if len(sys.argv) > 1 else 7)
N_ROWS = int(sys.argv[2]) if len(sys.argv) > 2 else 50

MALAY_M = ["Ahmad", "Muhammad Faiz", "Mohd Hafiz", "Amirul Hakim", "Zulkifli", "Khairul Anuar", "Azman",
           "Hafizuddin", "Syafiq", "Ikmal", "Rosli", "Fadzil", "Mohd Firdaus", "Ariff"]
MALAY_F = ["Nur Aisyah", "Siti Hajar", "Nurul Izzah", "Farah Wahida", "Aminah", "Noraini", "Zarina",
           "Hidayah", "Syazwani", "Rohana", "Nor Azlina", "Siti Khadijah"]
MALAY_FATHER = ["Ismail", "Abdullah", "Hassan", "Ibrahim", "Yusof", "Othman", "Kamarudin", "Razak",
                "Salleh", "Hamid", "Mustafa", "Ramli", "Sulaiman", "Zakaria"]
CN_SUR = ["Tan", "Lim", "Wong", "Lee", "Ng", "Chong", "Ong", "Goh", "Yap", "Leong", "Teh", "Chin", "Cheah"]
CN_GIVEN = ["Wei Ming", "Mei Ling", "Kok Leong", "Siew Lan", "Boon Keat", "Jia Hui", "Chee Keong",
            "Pei Shan", "Kah Wai", "Hui Min", "Zhi Hao", "Li Ting", "Yee Mun"]
EN_GIVEN = ["Jason", "Michelle", "Daniel", "Grace", "Kelvin", "Joanne"]
IN_M = ["Ravi", "Suresh Kumar", "Ganesh", "Arjun", "Vijay", "Muthu", "Kumaravel", "Rajesh", "Prakash"]
IN_F = ["Kavitha", "Priya", "Lakshmi", "Anitha", "Meena", "Shalini", "Revathi", "Thilaga"]
IN_FATHER = ["Subramaniam", "Muniandy", "Rajan", "Ganesan", "Krishnan", "Arumugam", "Ramasamy",
             "Selvaraj", "Pillai", "Govindasamy"]

STREETS = ["Demo", "Contoh", "Sampel", "Ujian", "Mawar", "Melati", "Kenanga", "Cempaka", "Teratai", "Dahlia"]
PARKS = ["Contoh Indah", "Demo Jaya", "Sampel Utama", "Ujian Permai", "Sri Contoh", "Desa Demo",
         "Bukit Sampel", "Contoh Ria"]
CITIES = [("43000", "Kajang", "Selangor"), ("47301", "Petaling Jaya", "Selangor"),
          ("40150", "Shah Alam", "Selangor"), ("56000", "Cheras", "Kuala Lumpur"),
          ("81100", "Johor Bahru", "Johor"), ("11900", "Bayan Lepas", "Pulau Pinang"),
          ("30450", "Ipoh", "Perak"), ("25200", "Kuantan", "Pahang"), ("88400", "Kota Kinabalu", "Sabah"),
          ("93350", "Kuching", "Sarawak"), ("15050", "Kota Bharu", "Kelantan"), ("75450", "Ayer Keroh", "Melaka")]
CO_A = ["Demo", "Contoh", "Sampel", "Ujian"]
CO_B = ["Maju", "Jaya", "Bina", "Niaga", "Teknik", "Global", "Makmur", "Sentosa", "Harapan", "Cemerlang"]
CO_C = ["Sdn Bhd", "Sdn. Bhd.", "Enterprise", "Trading", "Holdings Berhad", "Resources", "PLT"]


def person():
    kind = rnd.choice(["malay_m", "malay_f", "cn", "cn", "in_m", "in_f"])
    if kind == "malay_m":
        g, f = rnd.choice(MALAY_M), rnd.choice(MALAY_FATHER)
        full = f"{g} {rnd.choice(['bin', 'bin', 'b.'])} {f}"
        short, title = g.split()[-1] if g.startswith("M") and " " in g else g.split()[0], "Encik"
    elif kind == "malay_f":
        g, f = rnd.choice(MALAY_F), rnd.choice(MALAY_FATHER)
        full = f"{g} {rnd.choice(['binti', 'binti', 'bt'])} {f}"
        short, title = g.split()[-1] if g.startswith(("Nur ", "Siti ", "Nor ")) else g.split()[0], "Puan"
    elif kind == "cn":
        s, g = rnd.choice(CN_SUR), rnd.choice(CN_GIVEN)
        full = f"{s} {g}" if rnd.random() < 0.75 else f"{rnd.choice(EN_GIVEN)} {s} {g}"
        short, title = full.split()[0] if full.split()[0] in EN_GIVEN else f"{s} {g}", rnd.choice(["Mr", "Ms"])
    elif kind == "in_m":
        g, f = rnd.choice(IN_M), rnd.choice(IN_FATHER)
        full = f"{g} {rnd.choice(['a/l', 'a/l', 's/o'])} {f}"
        short, title = g.split()[0], "Mr"
    else:
        g, f = rnd.choice(IN_F), rnd.choice(IN_FATHER)
        full = f"{g} {rnd.choice(['a/p', 'a/p', 'd/o'])} {f}"
        short, title = g, "Ms"
    if rnd.random() < 0.12:
        full = full.upper()
    first = full.split()[0].lower().strip(".")
    last = full.split()[-1].lower()
    email = f"{first}.{last}{rnd.randint(1, 99)}@{rnd.choice(['example.com', 'example.net', 'example.org'])}"
    return {"name": full, "short": short, "title": title, "email": email}


def ic(dashes=True):
    while True:
        y, m, d = rnd.randint(60, 99) if rnd.random() < .8 else rnd.randint(0, 4), rnd.randint(1, 12), rnd.randint(1, 28)
        pb = rnd.randint(1, 14)
        s = f"{y:02d}{m:02d}{d:02d}{pb:02d}{rnd.randint(0, 9999):04d}"
        return f"{s[:6]}-{s[6:8]}-{s[8:]}" if dashes else s


def phone():
    k = rnd.random()
    n = rnd.randint(0, 9999)
    p = rnd.choice(["2", "3", "6", "7", "9"])
    if k < 0.45:
        return f"01{p}-000 {n:04d}"
    if k < 0.6:
        return f"01{p}-000{n:04d}"
    if k < 0.72:
        return f"+60 1{p}-000 {n:04d}"
    if k < 0.8:
        return f"601{p}000{n:04d}"
    if k < 0.9:
        return f"011-0000 {n:04d}"
    return f"03-0000 {n:04d}"


def tin(company=False):
    if company:
        return f"C0000{rnd.randint(0, 999999):06d}0"
    return f"IG000{rnd.randint(0, 99999999):08d}"


def brn():
    if rnd.random() < 0.7:
        return f"20{rnd.randint(13, 26)}0{rnd.choice([1, 3])}00{rnd.randint(0, 9999):04d}"
    return f"00{rnd.randint(1000, 9999)}-{rnd.choice('ADKMPTUVWX')}"


def company():
    return f"{rnd.choice(CO_A)} {rnd.choice(CO_B)} {rnd.choice(CO_C)}"


def address():
    pc, city, state = rnd.choice(CITIES)
    k = rnd.random()
    st = f"Jalan {rnd.choice(STREETS)} {rnd.randint(1, 12)}" + (f"/{rnd.randint(1, 9)}" if rnd.random() < .5 else "")
    park = f"Taman {rnd.choice(PARKS)}"
    if k < 0.55:
        unit = f"No. {rnd.randint(1, 120)}"
        full, parts = f"{unit}, {st}, {park}, {pc} {city}, {state}", [unit, st, park, pc]
    elif k < 0.75:
        unit = f"{rnd.choice('ABC')}-{rnd.randint(1, 20)}-{rnd.randint(1, 12)}"
        apt = f"Pangsapuri {rnd.choice(PARKS)}"
        full, parts = f"{unit}, {apt}, {st}, {pc} {city}, {state}", [unit, apt, st, pc]
    elif k < 0.88:
        unit = f"Lot {rnd.randint(100, 9999)}"
        kg = f"Kampung {rnd.choice(STREETS)} {rnd.choice(['Baru', 'Hulu', 'Tengah'])}"
        full, parts = f"{unit}, {kg}, {pc} {city}, {state}", [unit, kg, pc]
    else:
        unit = f"{rnd.randint(1, 99)}{rnd.choice(['', 'A', 'B'])}"
        lr = f"Lorong {rnd.choice(STREETS)} {rnd.randint(1, 9)}"
        full, parts = f"{unit} {lr}, {pc} {city}, {state}", [lr, pc]
    return full, parts


GT = []


def gt(file, typ, value, parts=None, where=None):
    GT.append({"file": file, "type": typ, "value": value, "parts": parts or [], "where": where})


def make_customers():
    header = ["Customer ID", "Name", "IC No", "Phone", "Email", "TIN", "Company", "BRN", "Address",
              "Amount (RM)", "Notes"]
    rows = []
    for i in range(N_ROWS):
        p, p2 = person(), person()
        is_co = rnd.random() < 0.3
        addr, parts = address()
        row = {"Customer ID": f"CUST-{1001 + i}", "Name": p["name"], "IC No": ic(rnd.random() < .8),
               "Phone": phone(), "Email": p["email"], "TIN": tin(is_co), "Company": company(),
               "BRN": brn(), "Address": addr, "Amount (RM)": f"{rnd.randint(50, 9000)}.{rnd.randint(0, 99):02d}"}
        k = rnd.random()
        notes, extra = "", []
        if k < 0.2:
            ph = phone()
            notes = f"Spouse {p2['name']} can be reached at {ph}."
            extra = [("NAME", p2["name"]), ("PHONE", ph)]
        elif k < 0.4:
            c2 = company()
            notes = f"Dirujuk oleh {p2['title']} {p2['name']} dari {c2}."
            extra = [("NAME", p2["name"]), ("ORG", c2)]
        elif k < 0.55:
            notes = f"Bayaran lewat, sudah hubungi {p['title']} {p['short']} pada 3 Nov."
            extra = [("NAME", p["short"])]
        elif k < 0.65:
            ic2 = ic(False)
            notes = f"Guarantor IC {ic2}, emel {p2['email']}"
            extra = [("IC", ic2), ("EMAIL", p2["email"])]
        elif k < 0.75:
            notes = "Alamat surat-menyurat sama. Invoice INV-2026-0042 settled via MyInvois."
        else:
            notes = ""
        row["Notes"] = notes
        rows.append(row)
        f = "customers"
        for col, typ in [("Name", "NAME"), ("IC No", "IC"), ("Phone", "PHONE"), ("Email", "EMAIL"),
                         ("TIN", "TIN"), ("Company", "ORG"), ("BRN", "BRN")]:
            gt(f, typ, row[col], where=f"row{i + 2}:{col}")
        gt(f, "ADDRESS", addr, parts, where=f"row{i + 2}:Address")
        for typ, v in extra:
            gt(f, typ, v, where=f"row{i + 2}:Notes")
    with open(os.path.join(OUT, "customers.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, header)
        w.writeheader()
        w.writerows(rows)
    import openpyxl
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Customers"
    ws.append(header)
    for r in rows:
        ws.append([r[h] for h in header])
    wb.properties.creator = "Demo Staff"
    wb.save(os.path.join(OUT, "customers.xlsx"))


def text_files():
    P = [person() for _ in range(12)]
    A = [address() for _ in range(4)]
    PH = [phone() for _ in range(6)]
    IC_ = [ic(rnd.random() < .5) for _ in range(4)]
    CO = [company() for _ in range(4)]
    TN = [tin(), tin(True), tin()]
    BR = [brn(), brn()]

    note1 = f"""Meeting notes, 4 Nov 2026

Attendees: {P[0]['name']} (finance), {P[1]['name']} and our auditor.
{P[0]['short']} said the customer {P[2]['name']} (IC {IC_[0]}) still owes RM 4,200.00 on invoice
INV-2026-0117. Please call {P[2]['title']} {P[2]['short']} at {PH[0]} before Friday.
Their company {CO[0]}, registration no. {BR[0]}, TIN {TN[1]}, moved to {A[0][0]}.
Action: {P[1]['short']} to email {P[2]['email']} with the statement. LHDN deadline is 31 Dec.
"""
    gt("note1.txt", "NAME", P[0]["name"]); gt("note1.txt", "NAME", P[1]["name"])
    gt("note1.txt", "NAME", P[0]["short"]); gt("note1.txt", "NAME", P[2]["name"])
    gt("note1.txt", "IC", IC_[0]); gt("note1.txt", "NAME", P[2]["short"]); gt("note1.txt", "PHONE", PH[0])
    gt("note1.txt", "ORG", CO[0]); gt("note1.txt", "BRN", BR[0]); gt("note1.txt", "TIN", TN[1])
    gt("note1.txt", "ADDRESS", A[0][0], A[0][1]); gt("note1.txt", "NAME", P[1]["short"])
    gt("note1.txt", "EMAIL", P[2]["email"])

    note2 = f"""# Catatan pelanggan

{P[3]['title']} {P[3]['name']} telah menghubungi pejabat semalam berkenaan cukai pendapatan.
Beliau tinggal di {A[1][0]} dan boleh dihubungi di talian {PH[1]}.
Nombor kad pengenalan beliau ialah {IC_[1]} dan nombor cukai {TN[0]}.
Anak beliau, {P[4]['name']}, akan datang ke pejabat pada hari Isnin untuk serahkan dokumen.
Sila maklumkan kepada {P[5]['short']} di bahagian akaun. Jumlah tertunggak RM 980.50.
"""
    for t, v in [("NAME", P[3]["name"]), ("ADDRESS", A[1]), ("PHONE", PH[1]), ("IC", IC_[1]),
                 ("TIN", TN[0]), ("NAME", P[4]["name"]), ("NAME", P[5]["short"])]:
        gt("note2.md", t, v[0] if isinstance(v, tuple) else v, v[1] if isinstance(v, tuple) else None)

    m = EmailMessage()
    m["From"] = f"{P[6]['name']} <{P[6]['email']}>"
    m["To"] = f"Accounts Demo <accounts@example.org>"
    m["Subject"] = f"Re: Invois tertunggak {CO[1]}"
    m["Date"] = "Tue, 04 Nov 2026 10:15:00 +0800"
    m.set_content(f"""Hi team,

Saya dah check dengan {P[7]['name']}, dia kata payment akan dibuat minggu depan.
Kalau ada apa-apa, boleh WhatsApp saya di {PH[2]} or call the office line {PH[5]}.
Please update the buyer details: {CO[1]}, BRN {BR[1]}, address {A[2][0]}.

Thanks,
{P[6]['short']}
""")
    with open(os.path.join(OUT, "email3.eml"), "wb") as fh:
        fh.write(bytes(m))
    for t, v in [("NAME", P[6]["name"]), ("EMAIL", P[6]["email"]), ("ORG", CO[1]), ("NAME", P[7]["name"]),
                 ("PHONE", PH[2]), ("PHONE", PH[5]), ("BRN", BR[1]), ("ADDRESS", A[2]), ("NAME", P[6]["short"])]:
        gt("email3.eml", t, v[0] if isinstance(v, tuple) else v, v[1] if isinstance(v, tuple) else None)

    note4 = f"""todo list (petang ni)
- follow up dgn {P[8]['short'].lower()} pasal invoice bulan lepas, dia belum bayar lagi
- {P[9]['name']} nak tukar alamat ke {A[3][0]}
- hantar e-invoice untuk {CO[2]}, tin {TN[2]}
- ic {P[9]['short']} = {IC_[2]}, hp {PH[3]}
- meeting dengan Dato' {P[10]['name']} jam 3 petang (bawa fail Kuala Lumpur)
"""
    for t, v in [("NAME", P[8]["short"].lower()), ("NAME", P[9]["name"]), ("ADDRESS", A[3]), ("ORG", CO[2]),
                 ("TIN", TN[2]), ("NAME", P[9]["short"]), ("IC", IC_[2]), ("PHONE", PH[3]),
                 ("NAME", P[10]["name"])]:
        gt("note4.txt", t, v[0] if isinstance(v, tuple) else v, v[1] if isinstance(v, tuple) else None)

    m = EmailMessage()
    m["From"] = f"{P[11]['name']} <{P[11]['email']}>"
    m["To"] = f"{P[3]['name']} <{P[3]['email']}>"
    m["Subject"] = "Dokumen e-invois"
    m.set_content(f"Salam {P[3]['short']},\nBerikut dokumen untuk {CO[3]}. Akaun bank Maybank 5140 0012 3456 untuk bayaran.\nIC saya {IC_[3]}.\n")
    m.add_alternative(f"<p>Salam <b>{P[3]['short']}</b>,</p><p>Berikut dokumen untuk {CO[3]}.</p>", subtype="html")
    with open(os.path.join(OUT, "email5.eml"), "wb") as fh:
        fh.write(bytes(m))
    for t, v in [("NAME", P[11]["name"]), ("EMAIL", P[11]["email"]), ("NAME", P[3]["name"]),
                 ("EMAIL", P[3]["email"]), ("NAME", P[3]["short"]), ("ORG", CO[3]), ("IC", IC_[3]),
                 ("ACCT", "5140 0012 3456")]:
        gt("email5.eml", t, v)

    for name, body in [("note1.txt", note1), ("note2.md", note2), ("note4.txt", note4)]:
        with open(os.path.join(OUT, name), "w", encoding="utf-8", newline="\n") as fh:
            fh.write(body)


def docx_file():
    import docx
    P = [person() for _ in range(4)]
    a = address()
    co, b, ph, i0 = company(), brn(), phone(), ic()
    d = docx.Document()
    d.add_heading("Surat Pengesahan Pelanggan", 1)
    d.add_paragraph(f"Kepada: {P[0]['title']} {P[0]['name']}")
    d.add_paragraph(a[0])
    para = d.add_paragraph("Dengan hormatnya, kami mengesahkan bahawa ")
    para.add_run(P[0]["name"]).bold = True
    para.add_run(f" (No. K/P: {i0}) adalah pelanggan berdaftar {co} sejak 2019.")
    d.add_paragraph(f"Untuk sebarang pertanyaan, sila hubungi {P[1]['name']} di {ph}.")
    t = d.add_table(rows=1, cols=3)
    t.rows[0].cells[0].text, t.rows[0].cells[1].text, t.rows[0].cells[2].text = "Nama", "No. IC", "Telefon"
    gt("letter.docx", "NAME", P[0]["name"]); gt("letter.docx", "ADDRESS", a[0], a[1])
    gt("letter.docx", "IC", i0); gt("letter.docx", "ORG", co); gt("letter.docx", "NAME", P[1]["name"])
    gt("letter.docx", "PHONE", ph)
    for p in P[2:]:
        r = t.add_row().cells
        r[0].text, r[1].text, r[2].text = p["name"], ic(), phone()
        gt("letter.docx", "NAME", r[0].text); gt("letter.docx", "IC", r[1].text); gt("letter.docx", "PHONE", r[2].text)
    d.sections[0].footer.paragraphs[0].text = f"{co} ({b})"
    gt("letter.docx", "BRN", b)
    d.save(os.path.join(OUT, "letter.docx"))


def pdf_file():
    """Minimal hand-built PDF with one text page (no extra dependency)."""
    p = person()
    a = address()
    i0, acct = ic(), f"{rnd.randint(1000, 9999)}{rnd.randint(10000000, 99999999)}"
    lines = ["Penyata Akaun Demo", f"Nama: {p['name']}", f"No. KP: {i0}", f"Alamat: {a[0]}",
             f"No. Akaun Bank: {acct}", "Baki: RM 1,234.56"]
    gt("statement.pdf", "NAME", p["name"]); gt("statement.pdf", "IC", i0)
    gt("statement.pdf", "ADDRESS", a[0], a[1]); gt("statement.pdf", "ACCT", acct)
    esc = lambda s: s.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    stream = "BT /F1 11 Tf 50 780 Td 14 TL " + " ".join(f"({esc(l)}) Tj T*" for l in lines) + " ET"
    objs = ["<< /Type /Catalog /Pages 2 0 R >>", "<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
            "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>",
            f"<< /Length {len(stream)} >>\nstream\n{stream}\nendstream",
            "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"]
    out, offs = "%PDF-1.4\n", []
    for n, o in enumerate(objs, 1):
        offs.append(len(out.encode("latin-1")))
        out += f"{n} 0 obj\n{o}\nendobj\n"
    x = len(out.encode("latin-1"))
    out += f"xref\n0 {len(objs) + 1}\n0000000000 65535 f \n" + "".join(f"{o:010d} 00000 n \n" for o in offs)
    out += f"trailer\n<< /Size {len(objs) + 1} /Root 1 0 R >>\nstartxref\n{x}\n%%EOF\n"
    with open(os.path.join(OUT, "statement.pdf"), "wb") as fh:
        fh.write(out.encode("latin-1"))


def holdout():
    """Different phrasing and harder cases, written before tuning; used only to measure."""
    global GT
    GT = []
    P = [person() for _ in range(14)]
    A = [address() for _ in range(3)]
    I = [ic(False), ic(True), ic(True).replace("-", " ")]
    co = [company() for _ in range(2)]
    ph_odd = [f"(03) 0000-{rnd.randint(0, 9999):04d}", f"+6012 000 {rnd.randint(0, 9999):04d}",
              f"013 000 {rnd.randint(0, 9999):04d}", f"082-000 {rnd.randint(0, 999):03d}"]
    lone_cn = rnd.choice(CN_GIVEN)
    in_plain = f"{rnd.choice(IN_F)} {rnd.choice(IN_FATHER)}"
    email_up = P[5]["email"].upper()
    texts = {
        "h1.txt": (f"""Complaint log
The caller identified herself as {P[0]['name']} and gave her MyKad number as {I[0]}.
She said her husband, {P[1]['name']}, had already paid. Her neighbour {lone_cn} witnessed it.
Callback: {ph_odd[0]} (office) or {ph_odd[1]}.
""", [("NAME", P[0]["name"]), ("IC", I[0]), ("NAME", P[1]["name"]), ("NAME", lone_cn),
      ("PHONE", ph_odd[0]), ("PHONE", ph_odd[1])]),
        "h2.txt": (f"""Minit ringkas
Pengarah {co[0]} iaitu {P[2]['name']} bersetuju menandatangani perjanjian.
Saksi: {in_plain}, No. K/P {I[1]}.
Surat akan dihantar ke alamat berdaftar di {A[0][0]}.
""", [("ORG", co[0]), ("NAME", P[2]["name"]), ("NAME", in_plain), ("IC", I[1]), ("ADDRESS", A[0])]),
        "h3.txt": (f"""fyi {P[3]['short'].lower()} dah resign. new pic is {P[4]['name']}, email {email_up},
hp {ph_odd[2]}. kalau urgent boleh call {P[4]['short']} terus.
""", [("NAME", P[3]["short"].lower()), ("NAME", P[4]["name"]), ("EMAIL", email_up), ("PHONE", ph_odd[2]),
      ("NAME", P[4]["short"])]),
        "h4.txt": (f"""Delivery address changed for order 5521:
{P[6]['name']}
{A[1][0]}
Tel: {ph_odd[3]}
Previous recipient {P[7]['name']} (IC {I[2]}) no longer at {A[2][0]}.
""", [("NAME", P[6]["name"]), ("ADDRESS", A[1]), ("PHONE", ph_odd[3]), ("NAME", P[7]["name"]),
      ("IC", I[2]), ("ADDRESS", A[2])]),
        "h5.txt": (f"""Dear {P[8]['title']} {P[8]['short']},
Thank you for meeting with {P[9]['name']} and {P[10]['name']} yesterday. As discussed, {co[1]} will
issue the e-invoice under TIN {tin(True)} once {P[11]['short']} confirms the amount of RM 12,400.
Regards, {P[12]['name']}
""", [("NAME", P[8]["short"]), ("NAME", P[9]["name"]), ("NAME", P[10]["name"]), ("ORG", co[1]),
      ("NAME", P[11]["short"]), ("NAME", P[12]["name"])]),
    }
    os.makedirs(os.path.join(HERE, "holdout"), exist_ok=True)
    for f, (body, ents) in texts.items():
        with open(os.path.join(HERE, "holdout", f), "w", encoding="utf-8", newline="\n") as fh:
            fh.write(body)
        for t, v in ents:
            gt(f, t, v[0] if isinstance(v, tuple) else v, v[1] if isinstance(v, tuple) else None)
    with open(os.path.join(HERE, "ground_truth_holdout.json"), "w", encoding="utf-8") as fh:
        json.dump({"entities": GT, "controls": ["Complaint log", "RM 12,400", "order 5521"]}, fh, indent=1)


CONTROLS = ["INV-2026-0042", "MyInvois", "RM 4,200.00", "INV-2026-0117", "LHDN", "31 Dec", "RM 980.50",
            "Kuala Lumpur", "CUST-1001", "Baki: RM 1,234.56", "Surat Pengesahan Pelanggan"]

if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    make_customers()
    text_files()
    docx_file()
    pdf_file()
    with open(os.path.join(HERE, "ground_truth.json"), "w", encoding="utf-8") as fh:
        json.dump({"entities": GT, "controls": CONTROLS}, fh, indent=1, ensure_ascii=False)
    print(f"wrote {len(GT)} labelled values to {OUT}")
    holdout()
    print(f"wrote {len(GT)} holdout values")
