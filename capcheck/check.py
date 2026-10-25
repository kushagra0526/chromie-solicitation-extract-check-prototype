"""Check an AI-extracted solicitation record against the solicitation text and its amendments. Reads only the text.

Findings: QUOTE_NOT_FOUND, STALE_AMENDMENT, VALUE_MISMATCH, WEIGHTS_SUM, WEIGHT_MISMATCH, SETASIDE_MISMATCH, NAICS_MISMATCH, FIT_WRONG, UNREAD.
Verdict: VERIFIED / FIX (corrected value given) / HOLD (a person must look).
"""
import re
from datetime import datetime, timedelta
from .gen import MONTHS, OFFSET, sents, pick, eligible

HOLD = {"QUOTE_NOT_FOUND", "SETASIDE_MISMATCH", "FIT_WRONG", "UNREAD"}
SA_PATTERNS = [("hubzone", r"HUBZone"), ("8a", r"8\(a\)"), ("wosb", r"WOSB|women-owned"), ("sdvosb", r"SDVOSB|service-disabled"),
               ("total_small", r"Total Small Business|exclusively for small businesses"), ("none", r"full and open|open to all")]


def norm(s):
    return re.sub(r"\s+", " ", s).strip()


def parse_due(sentence):
    """UTC ISO string from 'H:MM AM/PM TZ on <date>' (month-name layouts). None if not readable."""
    t = re.search(r"(\d{1,2}):(\d{2}) (AM|PM)", sentence) or re.search(r"(12):(00) (noon)", sentence)
    z = re.search(r"\b(ET|CT|MT|PT)\b", sentence)
    if not z:
        z = re.search(r"\b(Eastern|Central|Mountain|Pacific)\b", sentence)
        z = z and re.match(r"(..)", z.group(1)[0] + "T")
    d = re.search(r"(" + "|".join(MONTHS) + r") (\d{1,2}), (\d{4})", sentence)
    if d:
        mo, day, yr = MONTHS.index(d.group(1)) + 1, int(d.group(2)), int(d.group(3))
    else:
        d = re.search(r"(\d{1,2}) (" + "|".join(MONTHS) + r") (\d{4})", sentence)
        n = re.search(r"(\d{2})/(\d{2})/(\d{4})", sentence)
        if d:
            day, mo, yr = int(d.group(1)), MONTHS.index(d.group(2)) + 1, int(d.group(3))
        elif n:
            mo, day, yr = int(n.group(1)), int(n.group(2)), int(n.group(3))
        else:
            return None
    if not (t and z):
        return None
    h = int(t.group(1)) % 12 + (12 if t.group(3) in ("PM", "noon") else 0)
    return (datetime(yr, mo, day, h, int(t.group(2))) - timedelta(hours=OFFSET[z.group(1)])).strftime("%Y-%m-%dT%H:%MZ")


def parse_pages(sentence):
    m = re.search(r"\((\d+)\) pages", sentence) or re.search(r"(\d+) pages", sentence)
    return int(m.group(1)) if m else None


def parse_weights(text):
    s = pick(text, "Evaluation factors:") or pick(text, "scored out of 100") or pick(text, "Relative weight of each factor:") or ""
    s = s.split(":", 1)[1] if ":" in s else s
    out = {}
    for item in re.split(r",\s*|;\s*", s.rstrip(".")):
        m = re.match(r"^(.*?)\s*(?:\((\d+)%\)|- (\d+) points|(\d+) percent)$", item.strip())
        if not m:
            return None
        out[m.group(1)] = int(m.group(2) or m.group(3) or m.group(4))
    return out or None


def parse_setaside(text):
    s = pick(text, "This acquisition is")
    for code, pat in SA_PATTERNS:
        if re.search(pat, s):
            return code
    return None


def check(text, rec, profile):
    f = []
    T = norm(text)

    def add(code, field, msg, fix=None):
        f.append(dict(code=code, field=field, msg=msg, fix=fix))

    # controlling sentence = last amendment that changes the value, else the original
    due_all = [x for x in sents(text) if "due date is changed" in x]
    orig = pick(text, "due no later than") or pick(text, "must be received")
    ctrl = due_all[-1] if due_all else orig
    versions = [parse_due(x) for x in ([orig] + due_all)]
    want = versions[-1]
    if want is None:
        add("UNREAD", "due", f"cannot read the due date in: {ctrl!r}")
    else:
        got = rec["due"]["value"]
        if norm(rec["due"]["quote"]) not in T:
            add("QUOTE_NOT_FOUND", "due", "due-date quote is not in the solicitation")
        if got != want:
            if got in versions[:-1]:
                add("STALE_AMENDMENT", "due", f"value is from before the last amendment; current {want} per: {ctrl!r}", want)
            else:
                add("VALUE_MISMATCH", "due", f"text gives {want} (UTC), record has {got}", want)
    pg_all = [x for x in sents(text) if "page limit is changed" in x]
    pg_orig = pick(text, "pages", "technical volume") or pick(text, "shall not exceed")
    pv = [parse_pages(x) for x in [pg_orig] + pg_all]
    if pv[-1] is None:
        add("UNREAD", "pages", f"cannot read the page limit in: {pg_orig!r}")
    else:
        if norm(rec["pages"]["quote"]) not in T:
            add("QUOTE_NOT_FOUND", "pages", "page-limit quote is not in the solicitation")
        if rec["pages"]["value"] != pv[-1]:
            code = "STALE_AMENDMENT" if rec["pages"]["value"] in pv[:-1] else "VALUE_MISMATCH"
            add(code, "pages", f"text gives {pv[-1]}, record has {rec['pages']['value']}", pv[-1])
    w = rec["weights"]
    if sum(w.values()) != 100:
        add("WEIGHTS_SUM", "weights", f"weights add to {sum(w.values())}, not 100")
    dw = parse_weights(text)
    if dw is None:
        add("UNREAD", "weights", "cannot read the evaluation weights")
    elif dw != w and sum(w.values()) == 100:
        add("WEIGHT_MISMATCH", "weights", f"text gives {dw}", dw)
    sa = parse_setaside(text)
    nm = re.search(r"NAICS code (\d{6})", text)
    sz = re.search(r"size standard is (\d+) employees", text)
    if sa is None:
        add("UNREAD", "set_aside", "cannot read the set-aside")
    elif rec["set_aside"]["value"] != sa:
        add("SETASIDE_MISMATCH", "set_aside", f"text says {sa}, record has {rec['set_aside']['value']}", sa)
    if nm and rec["naics"] != nm.group(1):
        add("NAICS_MISMATCH", "naics", f"text says {nm.group(1)}, record has {rec['naics']}", nm.group(1))
    if sa and nm:
        size = int(sz.group(1)) if sz else None
        if sa == "total_small" and size is None:
            add("UNREAD", "fit", "small-business set-aside without a readable size standard")
        else:
            want_fit = eligible(sa, nm.group(1), size, profile)
            if rec["fit"] != want_fit:
                add("FIT_WRONG", "fit", f"profile says eligible={want_fit} for {sa}, NAICS {nm.group(1)}", want_fit)
    for q in rec["requirements"]:
        if norm(q["quote"]) not in T:
            add("QUOTE_NOT_FOUND", "requirements", f"quote not in solicitation: {q['quote']!r}")
    verdict = "VERIFIED" if not f else "HOLD" if any(x["code"] in HOLD for x in f) else "FIX"
    return verdict, f


def baseline(text, rec):
    """Quote-exists check only: what a citation requirement alone gives."""
    T = norm(text)
    quotes = [rec["due"]["quote"], rec["pages"]["quote"]] + [q["quote"] for q in rec["requirements"]]
    return "VERIFIED" if all(norm(q) in T for q in quotes) else "HOLD"
