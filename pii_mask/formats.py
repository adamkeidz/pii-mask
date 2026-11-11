"""File readers and writers. Each reader returns a Doc with text units; the writer puts tokens back
into the same structure."""
import csv
import io
import json
import os
import re
from email import policy
from email.parser import BytesParser

SUPPORTED = {".csv", ".xlsx", ".xlsm", ".txt", ".md", ".eml", ".docx", ".pdf"}

COLUMN_RULES = [  # (type, regex on the header, case-insensitive). First match wins.
    ("EMAIL", r"e-?mail|emel"),
    ("ORG", r"company|syarikat|organi[sz]ation|employer|majikan|business name|nama perniagaan|vendor|supplier|pembekal"),
    ("TIN", r"\btin\b|tax\s*(id|no|number|ref)|no\.?\s*cukai|income tax"),
    ("BRN", r"\bbrn\b|\bssm\b|\broc\b|\brob\b|registration|pendaftaran|reg\.?\s*no"),
    ("IC", r"\bic\b|nric|mykad|mykid|no\.?\s*k/?p|kad pengenalan|identity|passport|pasport|\bid\s*no"),
    ("PHONE", r"phone|\btel|telefon|mobile|\bhp\b|h/p|whatsapp|\bfax|faks|bimbit|contact\s*no"),
    ("ADDRESS", r"address|alamat|street|jalan"),
    ("ACCT", r"account\s*(no|number)|akaun|bank\s*acc|a/c"),
    ("NAME", r"name|nama|\bpic\b|contact person|pelanggan|customer|client|buyer|pembeli|employee|pekerja|staff|penerima|recipient|payee"),
]


def column_type(header, config):
    h = (header or "").strip()
    cols = (config or {}).get("columns", {})
    for k, v in cols.items():
        if k.strip().casefold() == h.casefold():
            v = v.upper()
            return None if v in ("SCAN", "") else v  # KEEP handled by caller
    if (config or {}).get("auto", True) is False:
        return None
    for typ, rx in COLUMN_RULES:
        if re.search(rx, h, re.IGNORECASE):
            if typ == "NAME" and re.search(r"file|product|item|produk|barang|service|bank|\bid\b|code|kod|\bno\b|number|ref|#", h, re.I):
                continue
            return typ
    return None


def _read_text(path):
    raw = open(path, "rb").read()
    for enc in ("utf-8-sig", "utf-8", "cp1252"):
        try:
            return raw.decode(enc), enc
        except UnicodeDecodeError:
            continue
    return raw.decode("latin-1"), "latin-1"


class Doc:
    out_suffix = ""

    def __init__(self):
        self.units, self.forced = [], {}


class TextDoc(Doc):
    def __init__(self, path, config=None):
        super().__init__()
        self.text, self.enc = _read_text(path)
        self.enc = "utf-8" if self.enc == "utf-8-sig" else self.enc
        self.units = [self.text]

    def write(self, spans, out, apply):
        with open(out, "w", encoding=self.enc, newline="") as f:
            f.write(apply(self.units[0], spans[0]))

    @staticmethod
    def unmask(src, dst, sub):
        text, enc = _read_text(src)
        enc = "utf-8" if enc == "utf-8-sig" else enc
        with open(dst, "w", encoding=enc, newline="") as f:
            f.write(sub(text))


class EmlDoc(TextDoc):
    out_suffix = ".txt"

    def __init__(self, path, config=None):
        Doc.__init__(self)
        msg = BytesParser(policy=policy.default).parse(open(path, "rb"))
        lines = []
        for h in ("From", "To", "Cc", "Reply-To", "Date", "Subject"):
            if msg[h]:
                lines.append(f"{h}: {msg[h]}")
        body = msg.get_body(preferencelist=("plain", "html"))
        text = ""
        if body is not None:
            text = body.get_content()
            if body.get_content_type() == "text/html":
                text = re.sub(r"(?is)<(script|style).*?</\1>", "", text)
                text = re.sub(r"(?i)<br\s*/?>|</p>|</div>|</tr>", "\n", text)
                text = re.sub(r"<[^>]+>", "", text)
                import html
                text = html.unescape(text)
        atts = [p.get_filename() or "(unnamed)" for p in msg.iter_attachments()]
        out = "\n".join(lines) + "\n\n" + text.replace("\r\n", "\n")
        if atts:
            out += "\n\n[attachments not included: " + ", ".join(atts) + "]\n"
        self.text, self.enc, self.units = out, "utf-8", [out]


class PdfDoc(TextDoc):
    out_suffix = ".txt"

    def __init__(self, path, config=None):
        Doc.__init__(self)
        from pypdf import PdfReader
        pages = [(p.extract_text() or "") for p in PdfReader(path).pages]
        self.text = "".join(f"--- page {i + 1} ---\n{t}\n" for i, t in enumerate(pages))
        self.enc, self.units = "utf-8", [self.text]
        self.pages = len(pages)


class CsvDoc(Doc):
    def __init__(self, path, config=None):
        super().__init__()
        text, enc = _read_text(path)
        self.enc = "utf-8-sig" if enc == "utf-8-sig" else enc
        try:
            self.dialect = csv.Sniffer().sniff(text[:4096], delimiters=",;\t|")
        except csv.Error:
            self.dialect = csv.excel
        self.newline = "\r\n" if "\r\n" in text[:4096] else "\n"
        self.rows = list(csv.reader(io.StringIO(text, newline=""), self.dialect))
        self.cells = []
        header = self.rows[0] if self.rows else []
        keep = {k.casefold() for k, v in (config or {}).get("columns", {}).items() if v.upper() == "KEEP"}
        types = [column_type(h, config) for h in header]
        self.column_types = types
        for r in range(1, len(self.rows)):
            for c, val in enumerate(self.rows[r]):
                if not val.strip():
                    continue
                if c < len(header) and header[c].strip().casefold() in keep:
                    continue
                self.cells.append((r, c))
                if c < len(types) and types[c]:
                    self.forced[len(self.units)] = types[c]
                self.units.append(val)

    def write(self, spans, out, apply):
        rows = [list(r) for r in self.rows]
        for (r, c), u, sp in zip(self.cells, self.units, spans):
            rows[r][c] = apply(u, sp)
        with open(out, "w", encoding=self.enc, newline="") as f:
            w = csv.writer(f, dialect=self.dialect, lineterminator=self.newline)
            w.writerows(rows)

    @staticmethod
    def unmask(src, dst, sub):
        doc = CsvDoc(src, {"auto": False})
        rows = [[sub(v) for v in r] for r in doc.rows]
        with open(dst, "w", encoding=doc.enc, newline="") as f:
            csv.writer(f, dialect=doc.dialect, lineterminator=doc.newline).writerows(rows)


class XlsxDoc(Doc):
    def __init__(self, path, config=None):
        super().__init__()
        import openpyxl
        self.wb = openpyxl.load_workbook(path, keep_vba=path.lower().endswith(".xlsm"))
        keep = {k.casefold() for k, v in (config or {}).get("columns", {}).items() if v.upper() == "KEEP"}
        self.cells = []
        for ws in self.wb.worksheets:
            header = None
            for row in ws.iter_rows():
                if header is None:  # header is the first non-empty row
                    h = {c.column: c.value for c in row if isinstance(c.value, str) and c.value.strip()}
                    header = h or None
                    continue
                for cell in row:
                    v = cell.value
                    h = str(header.get(cell.column, ""))
                    if v is None or h.strip().casefold() in keep:
                        continue
                    typ = column_type(h, config)
                    if isinstance(v, str):
                        if v.startswith("=") or not v.strip():
                            continue
                        text = v
                    elif isinstance(v, (int, float)) and not isinstance(v, bool):
                        text = str(int(v)) if float(v).is_integer() else str(v)
                        if not typ and len(re.sub(r"\D", "", text)) < 9:
                            continue
                    else:
                        continue  # dates, booleans
                    self.cells.append(cell)
                    if typ:
                        self.forced[len(self.units)] = typ
                    self.units.append(text)
            for cell_comment in [c for row in ws.iter_rows() for c in row if c.comment]:
                cell_comment.comment = None  # comments are not scanned, so drop them
        p = self.wb.properties
        p.creator = p.lastModifiedBy = p.title = p.subject = p.keywords = p.description = None

    def write(self, spans, out, apply):
        for cell, u, sp in zip(self.cells, self.units, spans):
            if sp:
                cell.value = apply(u, sp)
        self.wb.save(out)

    @staticmethod
    def unmask(src, dst, sub):
        import openpyxl
        wb = openpyxl.load_workbook(src, keep_vba=src.lower().endswith(".xlsm"))
        for ws in wb.worksheets:
            for row in ws.iter_rows():
                for cell in row:
                    if isinstance(cell.value, str) and "[" in cell.value:
                        cell.value = sub(cell.value)
        wb.save(dst)


def _docx_paragraphs(document):
    from docx.oxml.ns import qn
    roots = [document.element.body]
    for s in document.sections:
        for part in (s.header, s.footer, s.first_page_header, s.first_page_footer,
                     s.even_page_header, s.even_page_footer):
            try:
                if part is not None and not part.is_linked_to_previous:
                    roots.append(part._element)
            except Exception:
                pass
    seen = set()
    for root in roots:
        for p in root.iter(qn("w:p")):
            if id(p) in seen:
                continue
            seen.add(id(p))
            ts = [t for t in p.iter(qn("w:t"))]
            if ts:
                yield ts


def _replace_in_nodes(nodes, reps):
    """nodes: w:t elements. reps: [(start, end, replacement)] on the joined text. Text that spans
    several runs goes into the first run; formatting of the other runs is kept."""
    texts = [n.text or "" for n in nodes]
    for start, end, rep in sorted(reps, key=lambda x: -x[0]):
        pos, first = 0, True
        for i, t in enumerate(texts):
            a, b = pos, pos + len(t)
            pos = b
            if b <= start or a >= end:
                continue
            lo, hi = max(start, a) - a, min(end, b) - a
            texts[i] = t[:lo] + (rep if first else "") + t[hi:]
            first = False
    for n, t in zip(nodes, texts):
        if n.text != t:
            n.text = t
            n.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")


class DocxDoc(Doc):
    def __init__(self, path, config=None):
        super().__init__()
        import docx
        self.document = docx.Document(path)
        self.paras = list(_docx_paragraphs(self.document))
        self.units = ["".join(t.text or "" for t in ts) for ts in self.paras]
        cp = self.document.core_properties
        cp.author = cp.last_modified_by = cp.title = cp.subject = cp.keywords = cp.comments = ""

    def write(self, spans, out, apply):
        for ts, sp in zip(self.paras, spans):
            if sp:
                _replace_in_nodes(ts, [(s.start, s.end, s.token) for s in sp])
        self.document.save(out)

    @staticmethod
    def unmask(src, dst, sub):
        import docx
        from .engine import TOKEN_RE
        d = docx.Document(src)
        for ts in _docx_paragraphs(d):
            text = "".join(t.text or "" for t in ts)
            reps = [(m.start(), m.end(), sub(m.group(0))) for m in TOKEN_RE.finditer(text)]
            if reps:
                _replace_in_nodes(ts, reps)
        d.save(dst)


HANDLERS = {".csv": CsvDoc, ".xlsx": XlsxDoc, ".xlsm": XlsxDoc, ".txt": TextDoc, ".md": TextDoc,
            ".eml": EmlDoc, ".docx": DocxDoc, ".pdf": PdfDoc}


def load_config(path_or_none, input_path):
    cand = [path_or_none] if path_or_none else []
    d = input_path if os.path.isdir(input_path) else os.path.dirname(input_path)
    cand.append(os.path.join(d, "pii-columns.json"))
    for c in cand:
        if c and os.path.isfile(c):
            with open(c, encoding="utf-8") as f:
                return json.load(f)
    return None
