"""Recall, speed and round-trip check on the FAKE test set (run gen_testdata.py first).
Usage: python tests/evaluate.py [--model ID] [--llm-check] [--no-gliner] [--files a,b]"""
import argparse
import csv
import io
import json
import os
import re
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
os.environ.setdefault("TORCH_CPP_LOG_LEVEL", "ERROR")

from pii_mask.engine import offline_guard, Detector, TokenMap, mask_units, apply_spans, unmask_text, \
    TOKEN_RE, DEFAULT_MODEL  # noqa: E402
from pii_mask.formats import HANDLERS, _docx_paragraphs  # noqa: E402
from pii_mask import llm as llm_mod  # noqa: E402

DATA = os.path.join(HERE, "data")
STOP = {"bin", "binti", "a/l", "a/p", "s/o", "d/o", "b.", "bt", "mohd", "muhammad", "nur", "siti", "nor",
        "nurul", "kumar"}


def masked_text(path):
    ext = os.path.splitext(path)[1].lower()
    if ext in (".xlsx", ".xlsm"):
        import openpyxl
        wb = openpyxl.load_workbook(path)
        return "\n".join(" | ".join("" if c.value is None else str(c.value) for c in row)
                         for ws in wb.worksheets for row in ws.iter_rows())
    if ext == ".docx":
        import docx
        return "\n".join("".join(t.text or "" for t in ts) for ts in _docx_paragraphs(docx.Document(path)))
    return open(path, encoding="utf-8-sig").read()


def present(value, text, ci=True):
    return re.search(r"(?<![\w])" + re.escape(value) + r"(?![\w])", text, re.I if ci else 0) is not None


def leaked(e, text):
    v, t = e["value"], e["type"]
    if t == "ADDRESS":
        left = [p for p in e["parts"] if present(p, text)]
        return left
    if present(v, text):
        return [v]
    if t == "NAME":
        return [w for w in v.split() if len(w) >= 4 and w.lower() not in STOP and w not in e.get("keep", [])
                and present(w, text, ci=False)]
    return []


def token_checks(e, tm):
    """Problems with the token a value got: wrong type, or a name part not linked to its name."""
    rev = tm.reverse()
    bases = {k.split(".")[0].rstrip("]") for k, s in rev.items() if s == e["value"]}
    out = []
    if e.get("typed") and not any(b.startswith("[" + e["type"] + "_") for b in bases):
        out.append(f"typed {e['type']}: got {sorted(bases) or 'no token'}")
    if e.get("linked_to"):
        full = {k.split(".")[0].rstrip("]") for k, s in rev.items() if s == e["linked_to"]}
        if not bases & full:
            out.append(f"not linked to {e['linked_to']!r}: {sorted(bases)} vs {sorted(full)}")
    return out


def compare(src, masked, restored):
    ext = os.path.splitext(src)[1].lower()
    if ext in (".txt", ".md"):
        return open(src, "rb").read() == open(restored, "rb").read()
    if ext == ".csv":
        a = list(csv.reader(io.StringIO(open(src, encoding="utf-8-sig").read())))
        b = list(csv.reader(io.StringIO(open(restored, encoding="utf-8-sig").read())))
        return a == b
    if ext == ".xlsx":
        import openpyxl
        va = [[c.value for c in r] for ws in openpyxl.load_workbook(src).worksheets for r in ws.iter_rows()]
        vb = [[c.value for c in r] for ws in openpyxl.load_workbook(restored).worksheets for r in ws.iter_rows()]
        return va == vb
    if ext == ".docx":
        return masked_text(src) == masked_text(restored)
    if ext in (".eml", ".pdf"):
        return HANDLERS[ext](src).text == open(restored, encoding="utf-8").read()
    return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--threshold", type=float, default=0.35)
    ap.add_argument("--llm-check", action="store_true")
    ap.add_argument("--no-gliner", action="store_true")
    ap.add_argument("--files", default="")
    ap.add_argument("--quiet", action="store_true")
    ap.add_argument("--set", default="input", choices=["input", "holdout"])
    ap.add_argument("--no-columns", action="store_true", help="ignore header rules: detectors only")
    a = ap.parse_args()
    offline_guard()
    gt = json.load(open(os.path.join(DATA, "ground_truth.json" if a.set == "input" else
                                   "ground_truth_holdout.json"), encoding="utf-8"))
    out_dir = os.path.join(DATA, "out")
    os.makedirs(out_dir, exist_ok=True)
    t0 = time.time()
    det = Detector(model_name=a.model, threshold=a.threshold, use_gliner=not a.no_gliner)
    print(f"model {a.model if not a.no_gliner else 'regex only'} loaded in {time.time() - t0:.1f}s")
    llm = llm_mod.check if a.llm_check else None
    files = sorted(os.listdir(os.path.join(DATA, a.set)))
    if a.files:
        files = [f for f in files if f in a.files.split(",")]
    tot, miss_by_type, misses, rt_ok, speed = {}, {}, [], {}, []
    over = {}
    tok_n, tok_bad = 0, []
    for f in files:
        src = os.path.join(DATA, a.set, f)
        ext = os.path.splitext(f)[1].lower()
        doc = HANDLERS[ext](src, {"auto": False} if a.no_columns else None)
        tm = TokenMap()
        stats = {}
        t1 = time.time()
        spans = mask_units(doc.units, det, tm, forced=doc.forced, llm=llm, stats=stats)
        dt = time.time() - t1
        out = os.path.join(out_dir, f + doc.out_suffix)
        doc.write(spans, out, apply_spans)
        rev = tm.reverse()
        restored = os.path.join(out_dir, "restored-" + f + doc.out_suffix)
        handler = HANDLERS[".txt"] if ext in (".eml", ".pdf") else HANDLERS[ext]
        handler.unmask(out, restored, lambda s: unmask_text(s, rev)[0])
        rt_ok[f] = compare(src, out, restored)
        text = masked_text(out)
        if ext in (".csv", ".xlsx"):
            rows = len(getattr(doc, "rows", [])) - 1 if ext == ".csv" else 50
            speed.append((f, f"{rows / dt:.1f} rows/s ({dt:.2f}s for {rows} rows)"))
        else:
            pages = max(1, len(doc.text if hasattr(doc, "text") else "".join(doc.units)) / 3000)
            speed.append((f, f"{dt / pages:.2f} s/page ({dt:.2f}s, {pages:.2f} pages of 3000 chars)"))
        key = os.path.splitext(f)[0]
        ents = [e for e in gt["entities"] if e["file"] in (f, key)]
        for e in ents:
            tot[e["type"]] = tot.get(e["type"], 0) + 1
            lk = leaked(e, text)
            if lk:
                miss_by_type[e["type"]] = miss_by_type.get(e["type"], 0) + 1
                misses.append((f, e["type"], e["value"], lk, e.get("where")))
            if e.get("typed") or e.get("linked_to"):
                tok_n += 1
                tok_bad += [(f, e["value"], p) for p in token_checks(e, tm)]
        for m in TOKEN_RE.finditer(text):
            over.setdefault(m.group(1), set()).add(m.group(0).split(".")[0].rstrip("]"))
        if a.llm_check:
            print(f"  {f}: llm-check added {stats.get('llm_extra', 0)}, status {llm_mod.STATUS}")
    print("\nRECALL (value fully gone from masked output)")
    for t in sorted(tot):
        n, m = tot[t], miss_by_type.get(t, 0)
        print(f"  {t:8s} {n - m:4d}/{n:<4d} {100 * (n - m) / n:6.1f}%")
    n, m = sum(tot.values()), sum(miss_by_type.values())
    print(f"  {'ALL':8s} {n - m:4d}/{n:<4d} {100 * (n - m) / n:6.1f}%")
    ctrl_text = "\n".join(masked_text(os.path.join(out_dir, f + (".txt" if f.endswith((".eml", ".pdf")) else "")))
                          for f in files)
    src_text = "\n".join(masked_text(os.path.join(DATA, a.set, x)) if not x.endswith((".eml", ".pdf"))
                         else HANDLERS[os.path.splitext(x)[1]](os.path.join(DATA, a.set, x)).text
                         for x in files)
    ctrl = [c for c in gt["controls"] if c in src_text]
    kept = [c for c in ctrl if c in ctrl_text]
    print(f"\nCONTROL strings kept (not over-masked): {len(kept)}/{len(ctrl)}  lost: {sorted(set(ctrl) - set(kept))}")
    if tok_n:
        bad = {(f, v) for f, v, _ in tok_bad}
        print(f"\nTOKEN checks (type, name part linked): {tok_n - len(bad)}/{tok_n}")
        for x in tok_bad:
            print("  ", x)
    print("\nSPEED")
    for f, s in speed:
        print(f"  {f:16s} {s}")
    print("\nROUND TRIP exact:", {k: v for k, v in rt_ok.items()})
    if not a.quiet:
        print(f"\nMISSES ({len(misses)})")
        for x in misses:
            print("  ", x)


if __name__ == "__main__":
    main()
