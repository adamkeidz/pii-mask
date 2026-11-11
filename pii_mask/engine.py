"""Detection, span resolution and reversible token assignment."""
import os
import re
import json
import socket
from dataclasses import dataclass

TOOL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def offline_guard():
    """Refuse every network connection that is not loopback. Masking must never leave the PC."""
    allowed = {"127.0.0.1", "::1", "localhost"}
    orig_connect = socket.socket.connect
    orig_connect_ex = socket.socket.connect_ex

    def _check(addr):
        host = addr[0] if isinstance(addr, tuple) else addr
        if isinstance(host, str) and host not in allowed and not host.startswith("127."):
            raise ConnectionRefusedError("pii-mask: non-loopback network access is blocked")

    def connect(self, addr):
        _check(addr)
        return orig_connect(self, addr)

    def connect_ex(self, addr):
        _check(addr)
        return orig_connect_ex(self, addr)

    socket.socket.connect = connect
    socket.socket.connect_ex = connect_ex


TYPES = ["NAME", "IC", "PHONE", "ADDRESS", "ORG", "EMAIL", "TIN", "BRN", "ACCT", "CARD"]
PRIORITY = {"EMAIL": 100, "IC": 90, "TIN": 85, "CARD": 82, "PHONE": 80, "BRN": 75, "ACCT": 70,
            "ADDRESS": 50, "ORG": 45, "NAME": 40}
TOKEN_RE = re.compile(r"\[(" + "|".join(TYPES) + r")_(\d+)(?:\.(\d+))?\]")
GLINER_LABELS = {"person": "NAME", "organization": "ORG", "address": "ADDRESS"}
DEFAULT_MODEL = "urchade/gliner_multi-v2.1,knowledgator/gliner-pii-base-v1.0"
FAST_MODEL = "urchade/gliner_multi-v2.1"


@dataclass
class Span:
    start: int
    end: int
    type: str
    score: float = 1.0
    src: str = ""


# ---------------------------------------------------------------- detection

class Detector:
    def __init__(self, model_name=DEFAULT_MODEL, threshold=0.35, use_gliner=True):
        import logging
        import warnings
        warnings.filterwarnings("ignore")
        for name in ("presidio-analyzer", "transformers", "gliner", "torch", "huggingface_hub"):
            logging.getLogger(name).setLevel(logging.ERROR)
        from presidio_analyzer import AnalyzerEngine, RecognizerRegistry
        from presidio_analyzer.nlp_engine import SpacyNlpEngine
        from presidio_analyzer.predefined_recognizers import CreditCardRecognizer
        from .recognizers import all_recognizers

        self.nlp = SpacyNlpEngine(models=[{"lang_code": "en", "model_name": "en_core_web_sm"}])
        self.nlp.load()
        reg = RecognizerRegistry(supported_languages=["en"])
        for r in all_recognizers():
            reg.add_recognizer(r)
        cc = CreditCardRecognizer()
        cc.supported_entities = ["CARD"]
        cc.supported_entity = "CARD"
        reg.add_recognizer(cc)
        self.analyzer = AnalyzerEngine(registry=reg, nlp_engine=self.nlp, supported_languages=["en"])
        self.threshold = threshold
        self.gliners = []
        self.model_name = model_name
        if use_gliner:
            import torch
            from gliner import GLiNER
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
            for name in model_name.split(","):  # "a,b" runs both models and unions their spans
                g = GLiNER.from_pretrained(name.strip(), local_files_only=True)
                g.to(self.device)
                g.eval()
                self.gliners.append(g)

    def regex_spans(self, texts):
        out = []
        idx = [i for i, t in enumerate(texts) if t and re.search(r"[A-Za-z0-9]", t)]
        res = {i: [] for i in range(len(texts))}
        batch = [texts[i] for i in idx]
        if batch:
            arts = list(self.nlp.process_batch(batch, language="en"))
            for i, (_, art) in zip(idx, arts):
                for r in self.analyzer.analyze(texts[i], language="en", nlp_artifacts=art,
                                               score_threshold=0.4):
                    res[i].append(Span(r.start, r.end, r.entity_type, r.score, "regex"))
        for i in range(len(texts)):
            out.append(res[i])
        return out

    @staticmethod
    def _chunks(text, size=900):
        """Split at line/sentence boundaries into pieces of at most ~size chars, with offsets."""
        pieces, start = [], 0
        while start < len(text):
            end = min(len(text), start + size)
            if end < len(text):
                cut = max(text.rfind("\n", start, end), text.rfind(". ", start, end))
                if cut <= start + size // 3:
                    cut = text.rfind(" ", start, end)
                if cut > start:
                    end = cut + 1
            pieces.append((start, text[start:end]))
            start = end
        return pieces

    def gliner_spans(self, texts, batch_size=16):
        res = [[] for _ in texts]
        if not self.gliners:
            return res
        jobs = []
        for i, t in enumerate(texts):
            if t and len(t.strip()) >= 3 and re.search(r"[A-Za-z]{2}", t):
                for off, piece in self._chunks(t):
                    if piece.strip():
                        jobs.append((i, off, piece))
        import torch
        with torch.inference_mode():
            for b in range(0, len(jobs), 256):
                part = jobs[b:b + 256]
                for g in self.gliners:
                    preds = g.inference([p for _, _, p in part], list(GLINER_LABELS),
                                        threshold=self.threshold, batch_size=batch_size)
                    for (i, off, _), ents in zip(part, preds):
                        for e in ents:
                            res[i].append(Span(off + e["start"], off + e["end"], GLINER_LABELS[e["label"]],
                                               float(e["score"]), "gliner"))
        return res

    def detect(self, texts):
        rx = self.regex_spans(texts)
        gl = self.gliner_spans(texts)
        return [a + b for a, b in zip(rx, gl)]


# ---------------------------------------------------------------- resolution

from .lists import MY_STATES, STRIP_TITLE_RE  # noqa: E402

_STATE_TAIL = re.compile(r"^[\s,]*(?:" + "|".join(re.escape(s) for s in
                         sorted(MY_STATES, key=len, reverse=True)) + r")\b\.?", re.IGNORECASE)
_UNIT_HEAD = re.compile(r"(?:(?:No\.?|Lot|Unit|PT|Blok|Block|Tingkat|Aras|Level|Suite)\s*)?"
                        r"(?:[A-Z]{1,2}-)?\d{1,5}[A-Z]?(?:[\-/]\d{1,4}[A-Z]?){0,3}\s*,?\s*$", re.IGNORECASE)
# Capitalised words that start sentences or label fields; never the first word of a name.
_LEAD_STOP = re.compile(r"^(?:(?:Spouse|Wife|Husband|Isteri|Suami|Anak|Dear|Hi|Hello|Salam|Customer|Client|Pelanggan"
                        r"|Attendees?|Contact|Please|Call|Thanks|Kepada|Dirujuk|Untuk|Dengan|Sila|Beliau|Nama|Name"
                        r"|Guarantor|Penjamin|Referred|From|To|Cc|Dari|Oleh|Meeting|Mesyuarat|Tel|Ref)\s+)+",
                        re.IGNORECASE)
_GAP_OK = re.compile(r"^[\s,.;/\-]{0,4}$")
_TRIM_CHARS = " \t\r\n,.;:()[]\"'-"


def _trim(text, s):
    st, en = s.start, s.end
    while st < en and text[st] in _TRIM_CHARS:
        st += 1
    while en > st and text[en - 1] in _TRIM_CHARS:
        if text[en - 1] == "." and s.type in ("ORG", "NAME") and re.search(r"\b(Bhd|Co|Corp|Ltd|Inc|Hj|Mohd)\.$", text[st:en]):
            break
        if text[en - 1] == ")" and "(" in text[st:en]:
            break
        if text[en - 1] == "'" and s.type == "NAME":
            break
        en -= 1
    return Span(st, en, s.type, s.score, s.src)


def _merge_same_type(spans):
    out = []
    for s in sorted(spans, key=lambda x: (x.type, x.start, -x.end)):
        if out and out[-1].type == s.type and s.start < out[-1].end:
            p = out[-1]
            out[-1] = Span(p.start, max(p.end, s.end), p.type, max(p.score, s.score), p.src + "+" + s.src)
        else:
            out.append(s)
    return out


def _merge_address(text, spans):
    addr = sorted([s for s in spans if s.type == "ADDRESS"], key=lambda x: x.start)
    rest = [s for s in spans if s.type != "ADDRESS"]
    merged = []
    for s in addr:
        if merged and (s.start <= merged[-1].end or _GAP_OK.match(text[merged[-1].end:s.start])):
            p = merged[-1]
            merged[-1] = Span(p.start, max(p.end, s.end), "ADDRESS", max(p.score, s.score), "addr")
        else:
            merged.append(s)
    final = []
    for s in merged:
        st, en = s.start, s.end
        while True:  # extend over ", Selangor", ", Malaysia"
            m = _STATE_TAIL.match(text[en:en + 60])
            if not m:
                break
            en += m.end()
        m = _UNIT_HEAD.search(text[max(0, st - 30):st])
        if m and m.group(0).strip():
            st = max(0, st - 30) + m.start()
        # A lone fragment without street, number or postcode is too weak to be an address.
        frag = text[st:en]
        if s.src == "gliner" and len(frag) < 6:
            continue
        final.append(Span(st, en, "ADDRESS", s.score, s.src))
    return rest + final


# Public bodies, banks and products that models tag as ORG; never client data. Extend with
# "keep_terms" in the column config.
KEEP_TERMS = {t.casefold() for t in [
    "LHDN", "IRBM", "MyInvois", "SSM", "KWSP", "EPF", "PERKESO", "SOCSO", "SST", "JPN", "KDN", "MOF",
    "Bank Negara", "BNM", "Maybank", "CIMB", "Public Bank", "RHB", "Hong Leong Bank", "AmBank",
    "Bank Islam", "Bank Rakyat", "BSN", "Affin Bank", "Alliance Bank", "OCBC", "UOB", "HSBC",
    "DuitNow", "FPX", "Touch 'n Go", "Shopee", "Lazada", "Grab", "Excel", "Word", "PDF", "WhatsApp"]}


def add_keep_terms(terms):
    KEEP_TERMS.update(t.casefold().strip() for t in terms or [] if t.strip())


def resolve(text, spans):
    spans = [_trim(text, s) for s in spans]
    spans = [s for s in spans if text[s.start:s.end].casefold() not in KEEP_TERMS]
    spans = [s for s in spans if s.end - s.start >= 2]
    spans = _merge_same_type(spans)
    spans = _merge_address(text, spans)
    spans = _merge_same_type(spans)
    # Names: drop leading honorifics so "Encik Ali" and "Ali" share one token.
    fixed = []
    for s in spans:
        if s.type == "NAME":
            m = _LEAD_STOP.match(text[s.start:s.end])
            if m and m.end() < s.end - s.start:
                s = Span(s.start + m.end(), s.end, s.type, s.score, s.src)
            m = STRIP_TITLE_RE.match(text[s.start:s.end])
            if m and m.end() < s.end - s.start:
                s = Span(s.start + m.end(), s.end, s.type, s.score, s.src)
            if not re.search(r"[A-Za-z]{2}", text[s.start:s.end]):
                continue
        if s.src == "gliner" and s.type == "ORG" and not re.search(r"[A-Z0-9]", text[s.start:s.end]):
            continue  # lowercase "our auditor", "pejabat": generic nouns, not organisations
        fixed.append(_trim(text, s))
    order = sorted(fixed, key=lambda x: (-PRIORITY.get(x.type, 0), -(x.end - x.start), -x.score))
    taken = []  # chosen spans, non overlapping
    for s in order:
        pieces = [(s.start, s.end)]
        for t in taken:
            nxt = []
            for a, b in pieces:
                if b <= t.start or a >= t.end:
                    nxt.append((a, b))
                else:
                    if a < t.start:
                        nxt.append((a, t.start))
                    if b > t.end:
                        nxt.append((t.end, b))
            pieces = nxt
        cut = pieces != [(s.start, s.end)]
        for a, b in pieces:
            piece = _trim(text, Span(a, b, s.type, s.score, s.src))
            n_alnum = len(re.findall(r"[A-Za-z0-9]", text[piece.start:piece.end]))
            # A model span that mostly overlapped a stronger match leaves crumbs like "IC" or "at".
            if cut and (n_alnum < 4 or (piece.end - piece.start) < 0.4 * (s.end - s.start)):
                continue
            if n_alnum >= 2:
                taken.append(piece)
    return sorted(taken, key=lambda x: x.start)


# ---------------------------------------------------------------- tokens

def norm_key(typ, value):
    v = value.strip()
    if typ in ("IC", "ACCT", "CARD"):
        return re.sub(r"\D", "", v)
    if typ == "PHONE":
        d = re.sub(r"\D", "", v)
        return "0" + d[2:] if d.startswith("60") else d
    if typ in ("TIN", "BRN"):
        return re.sub(r"[\s\-]", "", v).upper()
    if typ == "EMAIL":
        return v.lower()
    return re.sub(r"\s+", " ", v).strip(" .,").casefold()


class TokenMap:
    def __init__(self):
        self.entries = {}   # (type, norm) -> {"n": int, "variants": [surface,...]}
        self.counter = {t: 0 for t in TYPES}

    @classmethod
    def load(cls, path):
        tm = cls()
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        for e in data["entries"]:
            tm.entries[(e["type"], e["norm"])] = {"n": e["n"], "variants": e["variants"]}
            tm.counter[e["type"]] = max(tm.counter.get(e["type"], 0), e["n"])
        return tm

    def save(self, path, meta=None):
        data = {"version": 1, "meta": meta or {},
                "entries": [{"type": t, "norm": k, "n": v["n"], "variants": v["variants"]}
                            for (t, k), v in self.entries.items()]}
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=1)
        os.replace(tmp, path)

    def token(self, typ, surface):
        key = (typ, norm_key(typ, surface))
        e = self.entries.get(key)
        if e is None:
            self.counter[typ] = self.counter.get(typ, 0) + 1
            e = {"n": self.counter[typ], "variants": []}
            self.entries[key] = e
        if surface not in e["variants"]:
            e["variants"].append(surface)
        v = e["variants"].index(surface)
        return f"[{typ}_{e['n']}]" if v == 0 else f"[{typ}_{e['n']}.{v + 1}]"

    def reverse(self):
        rev = {}
        for (t, _), e in self.entries.items():
            for i, s in enumerate(e["variants"]):
                rev[f"[{t}_{e['n']}]" if i == 0 else f"[{t}_{e['n']}.{i + 1}]"] = s
        return rev

    def counts(self):
        c = {}
        for (t, _), e in self.entries.items():
            c[t] = c.get(t, 0) + 1
        return c


def unmask_text(text, rev):
    missing = set()

    def sub(m):
        v = rev.get(m.group(0))
        if v is None:
            missing.add(m.group(0))
            return m.group(0)
        return v
    return TOKEN_RE.sub(sub, text), missing


# ---------------------------------------------------------------- batch masking

_NAME_STOP = {"bin", "binti", "bte", "anak", "mohd", "muhammad", "mohamad", "mohammad", "nur", "nurul",
              "siti", "abdul", "abd", "haji", "hajah", "encik", "puan", "datuk", "dato", "datin", "tuan",
              "syed", "sharifah", "kumar", "devi", "binte", "demo", "sample", "contoh"}


def _known_patterns(found):
    """found: dict value -> type. Builds one regex per case mode for propagation."""
    multi, single = {}, {}
    for v, t in found.items():
        v = v.strip()
        if len(v) < 3:
            continue
        (multi if (" " in v or not v.isalpha()) else single)[v] = t
    pats = []
    if multi:
        alt = "|".join(re.escape(v) for v in sorted(multi, key=len, reverse=True))
        pats.append((re.compile(r"(?<![\w@])(?:" + alt + r")(?![\w@])", re.IGNORECASE),
                     {k.casefold(): v for k, v in multi.items()}))
    if single:
        alt = "|".join(re.escape(v) for v in sorted(single, key=len, reverse=True))
        variants = {}
        for k, t in single.items():
            variants[k] = t
            variants[k.upper()] = t
        alt = "|".join(re.escape(v) for v in sorted(variants, key=len, reverse=True))
        pats.append((re.compile(r"(?<![\w@])(?:" + alt + r")(?![\w@])"), variants))
    return pats


def mask_units(units, detector, tmap, forced=None, llm=None, stats=None, regex_only=()):
    """units: list[str]. forced: {index: TYPE} masks the whole unit. Returns list of span lists
    where each span carries .token. The detector is never given a forced unit."""
    forced = forced or {}
    todo = [u if i not in forced else "" for i, u in enumerate(units)]
    raw = detector.detect(todo)
    for i in regex_only:  # file names: the model over-fires on short labels like "customers"
        raw[i] = [s for s in raw[i] if s.src == "regex"]
    spans = []
    for i, u in enumerate(units):
        if i in forced:
            s = _trim(u, Span(0, len(u), forced[i], 1.0, "column"))
            spans.append([s] if s.end > s.start else [])
        else:
            spans.append(resolve(u, raw[i]))
    found = {}
    for i, u in enumerate(units):
        for s in spans[i]:
            found.setdefault(u[s.start:s.end], s.type)
    _add_name_parts(found)
    for _round in range(2 if llm else 1):
        pats = _known_patterns(found)
        for i, u in enumerate(units):
            if i in forced or not u:
                continue
            extra = []
            for rx, table in pats:
                for m in rx.finditer(u):
                    t = table.get(m.group(0)) or table.get(m.group(0).casefold())
                    if t:
                        extra.append(Span(m.start(), m.end(), t, 0.99, "known"))
            if extra:
                spans[i] = _union(u, spans[i], extra)
        if llm and _round == 0:
            masked = [apply_spans(u, sp, tmap, dry=True) for u, sp in zip(units, spans)]
            hits = llm([m for i, m in enumerate(masked) if i not in forced and m.strip()])
            new = 0
            for value, typ in hits:
                if value not in found and any(value in u for u in units):
                    found[value] = typ
                    new += 1
            if stats is not None:
                stats["llm_extra"] = stats.get("llm_extra", 0) + new
            if not new:
                break
    for i, u in enumerate(units):
        for s in spans[i]:
            s.token = tmap.token(s.type, u[s.start:s.end])
            if stats is not None:
                stats.setdefault("mentions", {}).setdefault(s.type, 0)
                stats["mentions"][s.type] += 1
    return spans


def _add_name_parts(found):
    for v, t in list(found.items()):
        if t != "NAME":
            continue
        for w in re.split(r"[\s,]+", v):
            w = w.strip(".'")
            if len(w) >= 4 and w.isalpha() and w[0].isupper() and w.casefold() not in _NAME_STOP:
                found.setdefault(w, "NAME")


def _union(text, base, extra):
    out = list(base)
    for e in extra:
        if all(e.end <= b.start or e.start >= b.end for b in out):
            out.append(e)
    return sorted(out, key=lambda x: x.start)


def apply_spans(text, spans, tmap=None, dry=False):
    parts, last = [], 0
    for s in sorted(spans, key=lambda x: x.start):
        parts.append(text[last:s.start])
        parts.append(f"[{s.type}]" if dry else s.token)
        last = s.end
    parts.append(text[last:])
    return "".join(parts)
