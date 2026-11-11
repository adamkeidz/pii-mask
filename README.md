# pii-mask

Mask Malaysian personal data on your own PC before a document goes anywhere near a cloud AI tool,
then put the real values back into whatever the AI writes.

Detection, masking and the optional LLM review all run locally. The process refuses every
non-loopback network connection while it masks.

```
raw\  --mask-->  masked\  --(AI reads and writes here)-->  unmask  -->  restored\
            keys\  (token map, stays private)
```

`Ahmad bin Ismail (IC 900101-14-5678) called from 012-000 1234` becomes
`[NAME_1] (IC [IC_1]) called from [PHONE_1]`. The same value gets the same token across a whole
file or batch, so the AI can still reason about "the customer" and "his phone".

## Quick start

1. Put the original files in `ClientData\raw\` (under your user folder by default).
2. Run `mask ClientData\raw\customers.xlsx` (or a whole folder). It prints counts per type and
   the output path. It never prints a detected value.
3. Give the AI only the files in `ClientData\masked\`.
4. Save the AI's answer (still full of tokens) into `ClientData\masked\`, then run
   `unmask ClientData\masked\answer.md`. The real text lands in `ClientData\restored\`.
5. Before sharing anything, open the masked file yourself once and check nothing slipped through.

## Install (Windows, tested with Python 3.11)

```powershell
git clone <this repo> pii-mask; cd pii-mask
py -3.11 -m venv .venv
.venv\Scripts\python -m pip install torch==2.11.0 --index-url https://download.pytorch.org/whl/cu128   # or the CPU build
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python scripts\download_models.py      # one time, online: GLiNER checkpoints into .\hf-cache
```

Add the folder to your user PATH so `mask` and `unmask` (the `.cmd` wrappers) work from any
terminal, or call `pii-mask\mask.cmd` by its full path.

Optional second pass with a local LLM: install [Ollama](https://ollama.com) (it listens on
127.0.0.1 only by default), run `ollama pull qwen3:8b`, then block its internet access with
`block-ollama-outbound.ps1` from an Administrator PowerShell.

## Usage

```
mask <file-or-folder> [--llm-check] [--key NAME] [--config cols.json] [--fast] [--no-gliner]
unmask <file> [--key NAME]
```

| Option | What it does |
|---|---|
| `--llm-check` | After masking, a local `qwen3:8b` reads the MASKED text and lists leftovers. They are masked too and counted, never printed. |
| `--key NAME` | Reuse and extend `keys\NAME.json`, so a second run gives the same tokens as the first. |
| `--config` | Column rules for spreadsheets (see below). By default `pii-columns.json` next to the input is used if present. |
| `--fast` | One detection model instead of two. About twice as fast, slightly lower recall on lone first names. |
| `--no-gliner` | Regex only. Fast, but misses most names written in sentences. |

Output: masked files keep their format (`.csv`, `.xlsx`, `.docx`, `.txt`, `.md`). `.eml` and `.pdf`
become `.txt` (headers and body for email, page text for PDF). File names are masked too.
The key is written to `keys\<name>.json`; `keys\index.json` records which key belongs to which
masked file, so `unmask` finds it. For a file the AI wrote, `unmask` uses the newest key unless you
pass `--key`.

### Data root

Default: `%USERPROFILE%\ClientData` with `raw`, `keys`, `masked` and `restored` inside. Change it with
the `PII_MASK_ROOT` environment variable, or with `{"root": "D:\\Private\\ClientData"}` in
`%USERPROFILE%\.pii-mask.json`. The model cache path can be moved with `PII_MASK_MODELS`.

### Spreadsheet columns

Headers are matched automatically (Name/Nama, IC/NRIC/MyKad/No. KP, Phone/Tel/HP, Email/Emel,
Address/Alamat, TIN/No. Cukai, BRN/SSM/Registration, Company/Syarikat, Account No/Akaun). A matched
column is masked as a whole cell, without guessing. Every other text cell is scanned. To override,
copy `pii-columns.example.json` to `pii-columns.json` next to your files:

- `"NAME"`, `"IC"`, `"PHONE"`, `"ADDRESS"`, `"ORG"`, `"EMAIL"`, `"TIN"`, `"BRN"`, `"ACCT"`: mask the whole cell as that type.
- `"SCAN"`: run the detectors on the cell. `"KEEP"`: leave the column untouched.
- `"auto": false` turns off header matching. `"keep_terms"` lists words that must never be masked.

## What it catches

| Token | Detector |
|---|---|
| `[IC_n]` | MyKad numbers, 12 digits with or without dashes or spaces; the birth date and place-of-birth code are validated |
| `[TIN_n]` | LHDN TIN: IG/SG/OG + digits, C, CS, D, E, F, FA, PT, TA, TC, TN, TR, TP, J, LE + digits |
| `[BRN_n]` | SSM numbers: new 12-digit format (YYYY + type 01-06 + 6 digits) and old `123456-A` |
| `[PHONE_n]` | Malaysian mobiles and landlines with +60, 60 or 0, spaces, dashes, brackets |
| `[EMAIL_n]` | Email addresses |
| `[NAME_n]` | Names: bin/binti/bt/b./a/l/a/p/s/o/d/o/anak patterns, honorifics (Encik, Puan, Cik, Tuan, Dato', Datin, Tan Sri, Haji, Hajah, Dr and more, which stay visible), common Chinese surnames, plus two GLiNER models for everything else |
| `[ADDRESS_n]` | Unit numbers, Jalan/Lorong/Taman/Kampung/Persiaran..., postcode + town, state; fragments are merged into one span |
| `[ORG_n]` | Company suffixes (Sdn Bhd, Berhad, Enterprise, PLT, Trading...) and GLiNER |
| `[ACCT_n]` | 10 to 16 digit numbers next to a bank or account word |
| `[CARD_n]` | Card numbers that pass the Luhn check |

Every value found anywhere in a batch is also masked wherever else it appears.

Name parts: after detection, each detected name gives its given-name words, and those are masked
wherever they appear on their own in the same file or batch. `Puan Siti binti Demo ... once Siti
confirms` becomes `Puan [NAME_1] ... once [NAME_1.2] confirms`. The part keeps the full name's number
with a variant suffix, so the AI can tell it is the same person, and unmask puts back the exact word.
The rules:

- Honorifics are dropped, and so are bin/binti/bt/a/l/a/p/s/o/d/o/anak and everything after them
  (the father's name is never masked on its own). The first Chinese surname is dropped too.
- Prefixes such as Mohd, Nur or Siti count only when they are the whole given name
  (`Siti binti Demo` gives `Siti`, `Siti Hajar binti Demo` gives `Hajar`).
- A part needs at least 3 letters and a capital. It is matched whole-word and case-sensitively, as
  written, in Title case or in capitals, never in lower case, and never inside another token.
- A part that is also a common English or Malay word, a month or a place (April, Grace, Indah, Jaya,
  Kuala) is not masked on its own. The stoplist is `PART_STOP` in `pii_mask/lists.py`.
- A part shared by two different people in the batch is still masked, but gets its own token, so it
  is not wrongly linked to either.

A span that starts with an honorific or contains bin/binti/a/l/a/p is treated as a name, not an
organisation, unless it also has a company word (Sdn Bhd, Enterprise, Klinik and so on).

## Measured on the fake test set

The test set (`tests/gen_testdata.py`) is synthetic: invented names, `012-000 xxxx` phones,
`example.com` emails, "Demo"/"Contoh" companies. A value counts as caught only if it, or for
addresses any of its parts, no longer appears anywhere in the masked output.

Recall (values fully removed), RTX 3070 8 GB, CUDA build of PyTorch:

| Set | Default (2 models) | `--fast` (1 model) | Regex only |
|---|---|---|---|
| Main set: 11 files (csv, xlsx, 5 notes, 2 emails, docx, pdf), 969 labelled values | 969/969 | 969/969 | 964/969 (names 97.2%) |
| Same, spreadsheet header rules switched off (detectors only) | 969/969 | not re-run | not re-run |
| Holdout: different phrasing and harder cases, 5 random seeds, 140 values | 140/140 | 138/140 | 22/28 on one seed (names 60%) |

Per type on the main set every type (IC, TIN, BRN, PHONE, EMAIL, ADDRESS, ORG, NAME, ACCT) is at
100% with the default models. Every miss seen during testing was a lone first name inside a sentence.
Token checks on the main set: an honorific name alone on a line gets a NAME token (not ORG), and a lone
given name gets the full name's linked token (`[NAME_1.2]`).
`--llm-check` lifted regex-only holdout recall from 22/28 to 27/28, but did not recover the lone-name
misses left by `--fast`.

Over-masking check: 12 non-personal control strings (invoice numbers, amounts, LHDN, a city, and
"April 2027" next to a person whose given name is April). 11 survive by default (a customer ID becomes
a token). With `--llm-check`, 9 of the first 11 survived.

Speed:

| Input | Default | `--fast` | With `--llm-check` |
|---|---|---|---|
| 1,000-row, 11-column .xlsx | 24 s (about 42 rows/s) | 20 s (about 49 rows/s) | not measured at this size |
| 50-row .xlsx / .csv | 1.3 to 2.2 s | | 32 to 35 s (about 1.5 rows/s) |
| Text, per 3,000-character page | 0.1 to 0.16 s | | 2 to 4.4 s (8 s for the .docx) |

Loading the models adds 12 to 16 s per run, so mask a folder in one go rather than file by file.
Round trip: unmasking restored every format exactly (`.txt` and `.md` byte for byte, `.csv` and
`.xlsx` cell values, `.docx` paragraph text, the `.eml` and `.pdf` text renderings).

## Safety design

- **Offline while masking.** The package sets Hugging Face offline mode and patches the socket layer
  so any connection to a non-loopback address raises. Models load only from the local cache.
- **No values on screen.** `mask` and `unmask` print counts, key names and output paths only. Errors
  print the exception type; the traceback goes to `keys\errors.log`.
- **Ollama.** `--llm-check` talks only to `127.0.0.1:11434` and only sees masked text. The firewall
  scripts block Ollama's own outbound traffic (loopback is unaffected).
- **AI assistants.** `docs/claude-code-hook/` has an example Claude Code PreToolUse hook and
  permission rules that stop the assistant from touching `raw`, `keys` and `restored`, while still
  letting it run the `mask` and `unmask` wrappers. Adapt the paths before use.

## Known gaps

- It is a filter, not a guarantee. Recall on real documents will be lower than on the fake set.
  Always look at the masked file before you send it.
- Lone first names that never appear in full in the same file or batch ("once Rosli confirms" with
  no "Rosli bin ..." anywhere) are the weakest spot. The two-model default and `--llm-check` help;
  `--fast` and `--no-gliner` miss more. When the full name is detected somewhere in the batch, the
  lone given name is masked too (see "Name parts" above).
- A given name that is also a common word or place (April, Grace, Indah, Jaya) is not masked on its
  own, and neither is a bare prefix like Mohd or Siti when the given name has another word.
- Names in all lowercase, nicknames, and names written without any Malaysian pattern can slip.
- Not detected: old IC numbers (e.g. A1234567), passport numbers, vehicle plates, dates of birth on
  their own, salary figures, bank accounts without a nearby bank word, foreign phone numbers.
- Over-masking happens: product names, capitalised words and IDs (like `CUST-1001`) may become
  `[ORG_n]` or `[NAME_n]`. Use `keep_terms` or `KEEP` columns.
- `.docx`: body, tables, headers and footers are masked; comments, footnotes, text boxes, embedded
  objects and tracked changes are not read. When a value spans several runs, the token takes the
  first run's formatting. Author fields are cleared.
- `.xlsx`: cell values only. Formulas, charts, pivot caches, sheet names and data validation lists
  are not scanned. Cell comments and author fields are removed.
- `.pdf`: text layer only. Scanned PDFs (images) produce no text; run OCR first.
- `.eml`: headers and the main body only. Attachments are listed by name and not read.
- If an original already contains text shaped like a token (`[NAME_1]`), unmask will replace it.
- `--llm-check` findings are only used when the exact text appears in the file.

## Updating models

Masking never downloads. To update a model, allow the network for that step only:

```powershell
# Administrator PowerShell
powershell -ExecutionPolicy Bypass -File .\unblock-ollama-outbound.ps1
ollama pull qwen3:8b
powershell -ExecutionPolicy Bypass -File .\block-ollama-outbound.ps1
# GLiNER checkpoints (normal PowerShell):
.venv\Scripts\python scripts\download_models.py
```

## Tests

```powershell
.venv\Scripts\python tests\gen_testdata.py            # writes fake data to tests\data
.venv\Scripts\python tests\evaluate.py                # recall, speed, round trip
.venv\Scripts\python tests\evaluate.py --set holdout  # phrasing not used while tuning
.venv\Scripts\python tests\evaluate.py --no-columns   # detectors only, no header rules
.venv\Scripts\python tests\evaluate.py --llm-check    # with the Ollama pass
```

## Licence

MIT, see `LICENSE`. Third-party components and their licences are listed in `THIRD_PARTY.md`.
