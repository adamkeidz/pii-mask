"""Optional second pass: a local Ollama model reviews MASKED text for leftover personal data.
Only talks to 127.0.0.1. Findings never get printed; they go back into the masker."""
import json
import re
import urllib.request

OLLAMA_URL = "http://127.0.0.1:11434/api/chat"
MODEL = "qwen3:8b"
VALID = {"NAME", "IC", "PHONE", "EMAIL", "ADDRESS", "ORG", "TIN", "BRN", "ACCT"}

PROMPT = """You check text for personal data that is still visible. Some personal data was already
replaced by placeholders in square brackets like [NAME], [PHONE], [ADDRESS]; those are fine.
Read every line. List each piece of personal data that is NOT inside square brackets:
- people's names or given names, any culture, any case (Hamdan, Xiu Wen, jessica, Saraswathy Perumal)
- IC numbers, phone numbers, emails, street addresses, company names, TINs, SSM numbers, bank accounts
Do not list placeholders, job titles, cities, product names, dates, amounts or ordinary words.
Copy each finding exactly as written.

Example text: "Ask Hamdan and [NAME] to call [PHONE]. jessica will bring the file to [ADDRESS]."
Example answer: {"items":[{"text":"Hamdan","type":"NAME"},{"text":"jessica","type":"NAME"}]}

Answer with JSON only: {"items":[{"text":"...","type":"NAME|IC|PHONE|EMAIL|ADDRESS|ORG|TIN|BRN|ACCT"}]}
Answer {"items":[]} if nothing is left.

TEXT:
"""


def _ask(chunk, timeout=180):
    body = json.dumps({
        "model": MODEL, "stream": False, "format": "json", "think": False,
        "options": {"temperature": 0, "num_ctx": 8192, "num_predict": 768},
        "messages": [{"role": "user", "content": PROMPT + chunk}],
    }).encode()
    req = urllib.request.Request(OLLAMA_URL, data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        data = json.loads(r.read())
    try:
        items = json.loads(data["message"]["content"]).get("items", [])
    except (ValueError, KeyError, AttributeError):
        return []
    out = []
    for it in items if isinstance(items, list) else []:
        if not isinstance(it, dict):
            continue
        text, typ = str(it.get("text", "")).strip(), str(it.get("type", "")).upper()
        if typ in VALID and len(text) >= 3 and "[" not in text and "]" not in text \
                and re.search(r"[A-Za-z0-9]", text) and not _noise(text, typ):
            out.append((text, typ))
    return out


def _noise(text, typ):
    from .engine import KEEP_TERMS
    from .lists import HONORIFICS
    t = text.strip().casefold()
    if t in KEEP_TERMS or t in {h.casefold() for h in HONORIFICS}:
        return True
    if typ in ("IC", "PHONE", "TIN", "BRN", "ACCT") and not re.search(r"\d{4}", text):
        return True  # labels like "No. K/P", not numbers
    return False


def available():
    try:
        with urllib.request.urlopen("http://127.0.0.1:11434/api/tags", timeout=3) as r:
            tags = json.loads(r.read())
        return any(m.get("name", "").startswith(MODEL) for m in tags.get("models", []))
    except Exception:
        return False


def check(masked_texts, chunk_chars=2500):
    chunks, cur = [], ""
    for t in masked_texts:
        if len(cur) + len(t) > chunk_chars and cur:
            chunks.append(cur)
            cur = ""
        cur += t + "\n"
        while len(cur) > chunk_chars * 1.5:
            chunks.append(cur[:chunk_chars])
            cur = cur[chunk_chars:]
    if cur.strip():
        chunks.append(cur)
    hits = []
    for c in chunks:
        try:
            found = _ask(c)
        except Exception:  # timeout or runner error: report it, never block masking
            STATUS["failed"] += 1
            continue
        STATUS["chunks"] += 1
        # Only keep findings that really are in this chunk (models sometimes invent text).
        hits.extend((v, t) for v, t in found if v in c)
    return hits


STATUS = {"chunks": 0, "failed": 0}
