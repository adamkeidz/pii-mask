"""mask / unmask command line. Prints counts and output paths only, never a detected value."""
import argparse
import datetime
import json
import os
import sys
import time
import traceback



def _data_root():
    """PII_MASK_ROOT env var, else "root" in ~/.pii-mask.json, else ~/ClientData."""
    if os.environ.get("PII_MASK_ROOT"):
        return os.path.abspath(os.path.expanduser(os.environ["PII_MASK_ROOT"]))
    try:
        with open(os.path.join(os.path.expanduser("~"), ".pii-mask.json"), encoding="utf-8") as f:
            root = json.load(f).get("root")
        if root:
            return os.path.abspath(os.path.expanduser(root))
    except (OSError, ValueError, AttributeError):
        pass
    return os.path.join(os.path.expanduser("~"), "ClientData")


ROOT = _data_root()
DIRS = {k: os.path.join(ROOT, k) for k in ("raw", "keys", "masked", "restored")}
INDEX = os.path.join(DIRS["keys"], "index.json")


def _log_error(where):
    os.makedirs(DIRS["keys"], exist_ok=True)
    with open(os.path.join(DIRS["keys"], "errors.log"), "a", encoding="utf-8") as f:
        f.write(f"--- {datetime.datetime.now().isoformat()} {where}\n{traceback.format_exc()}\n")


def _index_load():
    try:
        with open(INDEX, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def _index_save(idx):
    with open(INDEX, "w", encoding="utf-8") as f:
        json.dump(idx, f, indent=1, ensure_ascii=False)


def _collect(target):
    from .formats import SUPPORTED
    if os.path.isfile(target):
        return [target], os.path.dirname(target)
    files = []
    for d, _, fs in os.walk(target):
        for f in sorted(fs):
            if os.path.splitext(f)[1].lower() in SUPPORTED and not f.startswith("~$"):
                files.append(os.path.join(d, f))
    return files, target


def _safe_name_part(s):
    return "".join("_" if ch in '<>:"/\\|?*' else ch for ch in s)


def cmd_mask(args):
    t0 = time.time()
    target = os.path.abspath(args.path)
    if not os.path.exists(target):
        print("error: input not found")
        return 2
    from .engine import offline_guard
    offline_guard()
    from .engine import Detector, TokenMap, mask_units, apply_spans
    from .formats import HANDLERS, load_config
    from . import llm as llm_mod

    files, base = _collect(target)
    if not files:
        print("error: no supported files (.csv .xlsx .txt .md .eml .docx .pdf)")
        return 2
    for d in DIRS.values():
        os.makedirs(d, exist_ok=True)
    config = load_config(args.config, target)
    from .engine import add_keep_terms
    add_keep_terms((config or {}).get("keep_terms"))

    llm = None
    if args.llm_check:
        if not llm_mod.available():
            print("error: --llm-check needs Ollama running on 127.0.0.1 with qwen3:8b pulled")
            return 3
        llm = llm_mod.check

    det = Detector(model_name=args.model, threshold=args.threshold, use_gliner=not args.no_gliner)
    t_load = time.time() - t0

    docs, units, forced, owners, failed = [], [], {}, [], 0
    for n, f in enumerate(files, 1):
        ext = os.path.splitext(f)[1].lower()
        try:
            doc = HANDLERS[ext](f, config)
        except Exception as e:
            _log_error(f"read file #{n}")
            print(f"skipped file #{n} ({ext}): could not read ({type(e).__name__}); details in keys\\errors.log")
            failed += 1
            continue
        start = len(units)
        for i, u in enumerate(doc.units):
            if i in doc.forced:
                forced[start + i] = doc.forced[i]
            units.append(u)
        # The file name itself may hold a client name, so it is masked as one more unit.
        rel = os.path.relpath(f, base)
        units.append(os.path.splitext(rel)[0].replace("_", " "))  # extension stays readable
        docs.append((f, rel, doc, start, len(units) - 1))

    folder_name = os.path.basename(os.path.normpath(target))
    folder_i = None
    if os.path.isdir(target):
        units.append(folder_name.replace("_", " "))
        folder_i = len(units) - 1
    key_name = args.key or "pending"
    tmap_path = None
    if args.key:
        tmap_path = os.path.join(DIRS["keys"], args.key + ".json")
        tmap = TokenMap.load(tmap_path) if os.path.exists(tmap_path) else TokenMap()
    else:
        tmap = TokenMap()

    stats = {}
    t1 = time.time()
    name_units = {d[4] for d in docs} | ({folder_i} if folder_i is not None else set())
    spans = mask_units(units, det, tmap, forced=forced, llm=llm, stats=stats, regex_only=name_units)
    t_detect = time.time() - t1

    idx = _index_load()
    outputs = []
    for f, rel, doc, start, name_i in docs:
        try:
            stem, ext_ = os.path.splitext(rel)
            masked_rel = apply_spans(stem, spans[name_i]) + ext_  # same offsets as the unit
            masked_rel = os.path.join(*[_safe_name_part(p) for p in masked_rel.split(os.sep)])
            if folder_i is not None:
                masked_rel = os.path.join(_safe_name_part(apply_spans(folder_name, spans[folder_i])),
                                          masked_rel)
            out = os.path.join(DIRS["masked"], masked_rel + doc.out_suffix)
            os.makedirs(os.path.dirname(out), exist_ok=True)
            doc.write(spans[start:start + len(doc.units)], out, apply_spans)
            outputs.append(out)
            idx[os.path.abspath(out).lower()] = key_name
        except Exception as e:
            _log_error(f"write output for {rel!r}")
            print(f"failed writing one file ({type(e).__name__}); details in keys\\errors.log")
            failed += 1

    # key name is derived from the masked form of the input name
    if not args.key:
        key_name = _safe_name_part(os.path.splitext(os.path.basename(outputs[0]))[0]) if \
            (len(outputs) == 1 and os.path.isfile(target)) else key_name
        if os.path.isdir(target):
            key_name = "batch-" + datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        for o in outputs:
            idx[os.path.abspath(o).lower()] = key_name
        tmap_path = os.path.join(DIRS["keys"], key_name + ".json")
    tmap.save(tmap_path, meta={"created": datetime.datetime.now().isoformat(), "files": len(outputs)})
    _index_save(idx)

    counts = tmap.counts()
    mentions = stats.get("mentions", {})
    print(f"masked {len(outputs)} file(s), {failed} failed")
    for typ in sorted(set(counts) | set(mentions)):
        print(f"  {typ:8s} {counts.get(typ, 0):5d} unique  {mentions.get(typ, 0):6d} replaced")
    if args.llm_check:
        print(f"  llm-check: {stats.get('llm_extra', 0)} extra value(s) found and masked, "
              f"{llm_mod.STATUS['chunks']} chunk(s) reviewed, {llm_mod.STATUS['failed']} failed")
    for o in outputs:
        print(f"  -> {o}")
    print(f"key: keys\\{key_name}.json")
    print(f"time: load {t_load:.1f}s, detect {t_detect:.1f}s, total {time.time() - t0:.1f}s")
    return 0 if not failed else 1


def cmd_unmask(args):
    from .engine import TokenMap, unmask_text
    from .formats import HANDLERS
    src = os.path.abspath(args.path)
    if not os.path.isfile(src):
        print("error: file not found")
        return 2
    idx = _index_load()
    key = args.key or idx.get(src.lower())
    if not key:
        keys = [k for k in os.listdir(DIRS["keys"]) if k.endswith(".json") and k != "index.json"]
        if not keys:
            print("error: no keys found")
            return 2
        key = max(keys, key=lambda k: os.path.getmtime(os.path.join(DIRS["keys"], k)))[:-5]
        print(f"note: no key recorded for this file, using the latest key: {key}")
    kp = os.path.join(DIRS["keys"], key + ".json")
    if not os.path.isfile(kp):
        print("error: key not found")
        return 2
    rev = TokenMap.load(kp).reverse()
    missing, n = set(), [0]

    def sub(text):
        out, miss = unmask_text(text, rev)
        missing.update(miss)
        from .engine import TOKEN_RE
        n[0] += len(TOKEN_RE.findall(text)) - len(miss)
        return out

    rel = os.path.relpath(src, DIRS["masked"]) if src.lower().startswith(DIRS["masked"].lower()) \
        else os.path.basename(src)
    dst_rel, _ = unmask_text(rel, rev)
    dst = os.path.join(DIRS["restored"], *[_safe_name_part(p) for p in dst_rel.split(os.sep)])
    ext = os.path.splitext(src)[1].lower()
    handler = HANDLERS.get(ext, HANDLERS[".txt"])
    if handler.__name__ in ("EmlDoc", "PdfDoc"):
        handler = HANDLERS[".txt"]
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    try:
        handler.unmask(src, dst, sub)
    except Exception as e:
        _log_error("unmask")
        print(f"error: could not restore ({type(e).__name__}); details in keys\\errors.log")
        return 1
    print(f"restored {n[0]} token(s) using key {key}")
    if missing:
        print(f"warning: {len(missing)} token(s) not in this key were left as they are")
    print(f"  -> {dst}")
    return 0


def main(argv=None):
    prog = os.path.basename(sys.argv[0]) if argv is None else "pii"
    p = argparse.ArgumentParser(prog="pii-mask")
    sub = p.add_subparsers(dest="cmd", required=True)
    m = sub.add_parser("mask", help="mask a file or folder into ClientData\\masked")
    m.add_argument("path")
    m.add_argument("--llm-check", action="store_true", help="second pass with local qwen3:8b")
    m.add_argument("--key", help="reuse/extend keys\\<KEY>.json so tokens match an earlier run")
    m.add_argument("--config", help="column config JSON (default: pii-columns.json next to input)")
    m.add_argument("--model", default=None, help="GLiNER model id (offline cache)")
    m.add_argument("--threshold", type=float, default=0.35)
    m.add_argument("--fast", action="store_true", help="one GLiNER model instead of two (lower name recall)")
    m.add_argument("--no-gliner", action="store_true", help="regex only (fast, misses free-text names)")
    u = sub.add_parser("unmask", help="restore tokens into ClientData\\restored")
    u.add_argument("path")
    u.add_argument("--key", help="key name in keys\\ (default: the key recorded for the file)")
    args = p.parse_args(argv)
    try:
        if args.cmd == "mask":
            from .engine import DEFAULT_MODEL, FAST_MODEL
            args.model = args.model or (FAST_MODEL if args.fast else DEFAULT_MODEL)
            return cmd_mask(args)
        return cmd_unmask(args)
    except Exception as e:
        _log_error(args.cmd)
        print(f"error: {type(e).__name__}; details in keys\\errors.log")
        return 1


if __name__ == "__main__":
    sys.exit(main())
