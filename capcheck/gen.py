"""Synthetic solicitations (3 layouts), amendments, a company profile, and a simulated AI extractor with planted errors.

Fictional agencies and numbers only. Layout C is held out: the checker was written without seeing it.
"""
import random, re
from datetime import datetime, timedelta

MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
OFFSET = {"ET": -4, "CT": -5, "MT": -6, "PT": -7}         # all generated dates fall in daylight time
TZNAME = {"ET": "Eastern Time", "CT": "Central Time", "MT": "Mountain Time", "PT": "Pacific Time"}
FACTORS = ["Technical Approach", "Past Performance", "Management Plan", "Price", "Key Personnel", "Transition Plan"]
SETASIDES = {"total_small": "Total Small Business Set-Aside", "8a": "8(a) Program Set-Aside",
             "wosb": "Women-Owned Small Business (WOSB) Set-Aside", "sdvosb": "Service-Disabled Veteran-Owned Small Business (SDVOSB) Set-Aside",
             "hubzone": "HUBZone Set-Aside", "none": "full and open competition"}
SETASIDES_C = {"total_small": "reserved exclusively for small businesses", "8a": "reserved for participants in the SBA 8(a) Business Development program",
               "wosb": "reserved for women-owned small businesses", "sdvosb": "reserved for service-disabled veteran-owned small businesses",
               "hubzone": "reserved for HUBZone small businesses", "none": "open to all responsible sources"}
NAICS = ["541512", "541519", "541611", "561210", "238220", "541330", "621111"]
CERTS = ["8a", "wosb", "sdvosb", "hubzone"]
SHALL = ["The Contractor shall provide 24x7 help desk coverage.", "The Contractor shall maintain FedRAMP Moderate authorization.",
         "The Contractor shall deliver a monthly status report by the fifth business day.", "The Contractor shall staff all key personnel with U.S. citizens.",
         "The Contractor shall complete transition within 60 days of award.", "The Contractor shall encrypt data at rest using FIPS 140-3 validated modules."]
NUMW = {20: "twenty", 25: "twenty-five", 30: "thirty", 35: "thirty-five", 40: "forty", 15: "fifteen", 45: "forty-five", 50: "fifty"}


def ampm(h, m):
    return f"{(h - 1) % 12 + 1}:{m:02d} {'AM' if h < 12 else 'PM'}"


def fmt_date(d, layout):
    if layout == "A":
        return f"{MONTHS[d.month - 1]} {d.day}, {d.year}"
    if layout == "B":
        return f"{d.day} {MONTHS[d.month - 1]} {d.year}"
    return f"{d.month:02d}/{d.day:02d}/{d.year}"


def fmt_due(d, h, m, tz, layout):
    if layout == "A":
        return f"{ampm(h, m)} {tz} on {fmt_date(d, 'A')}"
    if layout == "B":
        return f"{ampm(h, m)} {TZNAME[tz]} ({tz}) on {fmt_date(d, 'B')}"
    t = "12:00 noon" if (h, m) == (12, 0) else ampm(h, m)
    return f"{fmt_date(d, 'C')} {t} {TZNAME[tz].split()[0]}"


def to_utc(d, h, m, tz):
    return (datetime(d.year, d.month, d.day, h, m) - timedelta(hours=OFFSET[tz])).strftime("%Y-%m-%dT%H:%MZ")


def pages_text(n, layout):
    if layout == "C":
        return f"The technical volume is not to exceed {NUMW[n]} ({n}) pages."
    if layout == "B":
        return f"The page limit for the technical volume is {n} pages; the cover page and table of contents do not count."
    return f"Proposals shall not exceed {n} pages."


def weights_text(fw, layout):
    items = list(fw.items())
    if layout == "A":
        return "Evaluation factors: " + ", ".join(f"{k} ({v}%)" for k, v in items) + "."
    if layout == "B":
        return "Offers are scored out of 100 points: " + "; ".join(f"{k} - {v} points" for k, v in items) + "."
    return "Relative weight of each factor: " + ", ".join(f"{k} {v} percent" for k, v in items) + "."


def make(seed, layout):
    r = random.Random(seed)
    tz = r.choice(list(OFFSET))
    d0 = datetime(2026, r.randint(6, 10), r.randint(1, 26))
    h0, m0 = r.choice([(14, 0), (16, 0), (12, 0), (17, 0), (11, 30), (15, 0)])
    pages0 = r.choice([15, 20, 25, 30, 35, 40])
    nf = r.randint(3, 5)
    names = r.sample(FACTORS, nf)
    cuts = sorted(r.sample(range(1, 20), nf - 1))
    parts = [(b - a) * 5 for a, b in zip([0] + cuts, cuts + [20])]
    fw = dict(zip(names, parts))
    sa = r.choice(list(SETASIDES))
    naics = r.choice(NAICS)
    size = r.choice([250, 500, 1000])
    reqs = r.sample(SHALL, 3)
    due, pages, amends = (d0, h0, m0, tz), pages0, []
    d, h, m = d0, h0, m0
    for i in range(r.choice([0, 0, 1, 2])):
        what = r.choice(["due", "pages", "both"])
        parts_a = []
        if what in ("due", "both"):
            d = d + timedelta(days=r.randint(3, 10)); h, m = r.choice([(14, 0), (16, 0), (12, 0), (17, 0)])
            parts_a.append(f"The offer due date is changed to {fmt_due(d, h, m, tz, layout)}.")
        if what in ("pages", "both"):
            pages = r.choice([p for p in (15, 20, 25, 30, 35, 40, 45, 50) if p != pages])
            parts_a.append(f"The page limit is changed to {pages} pages.")
        amends.append(f"AMENDMENT {i + 1:04d}: " + " ".join(parts_a))
    body = [f"SOLICITATION 7{r.randint(10000, 99999)}-26-R-{r.randint(1000, 9999)}",
            f"SECTION B. This acquisition is {SETASIDES_C[sa] if layout == 'C' else 'a ' + SETASIDES[sa] if sa != 'none' else 'under ' + SETASIDES[sa]}.",
            f"NAICS code {naics}; the size standard is {size} employees." if sa != "none" else f"NAICS code {naics}.",
            "SECTION C. " + " ".join(reqs),
            "SECTION L. INSTRUCTIONS TO OFFERORS. " + pages_text(pages0, layout),
            f"Offers are due no later than {fmt_due(d0, h0, m0, tz, layout)}." if layout != "B" else f"Responses must be received by {fmt_due(d0, h0, m0, tz, layout)}.",
            "SECTION M. EVALUATION. " + weights_text(fw, layout)]
    text = "\n".join(body) + ("\n" + "\n".join(amends) if amends else "")
    profile = dict(naics=r.sample(NAICS, 3), employees=r.choice([60, 200, 450, 700, 1500]), certs=r.sample(CERTS, r.randint(0, 2)))
    truth = dict(due=to_utc(d, h, m, tz), due0=to_utc(d0, h0, m0, tz), tz=tz, pages=pages, pages0=pages0, weights=fw, set_aside=sa, naics=naics,
                 size=size if sa != "none" else None, reqs=reqs, amended=bool(amends))
    return dict(seed=seed, layout=layout, text=text, profile=profile, truth=truth)


def eligible(set_aside, naics, size, profile):
    if naics not in profile["naics"]:
        return False
    if set_aside == "none":
        return True
    if set_aside == "total_small":
        return profile["employees"] <= size
    return set_aside in profile["certs"]


def sents(text):
    text = re.sub(r"AMENDMENT \d+: ", "", text)
    return [x.strip() for x in re.split(r"(?<=\.)\s+|\n", text) if x.strip()]


def pick(text, *needles, last=False):
    hits = [x for x in sents(text) if all(n in x for n in needles)]
    return (hits[-1] if last else hits[0]) if hits else ""


def extract(sol, seed, kinds=()):
    """Simulated AI extractor. Each kind in `kinds` plants one error; quotes are copied from the text unless invented."""
    r = random.Random(seed * 7 + 1)
    t, text = sol["truth"], sol["text"]
    due, pages = t["due"], t["pages"]
    am_due, am_pg = pick(text, "due date is changed", last=True), pick(text, "page limit is changed", last=True)
    due_q = am_due or pick(text, "due no later than") or pick(text, "must be received")
    pages_q = am_pg or pick(text, "pages", "technical volume") or pick(text, "shall not exceed")
    if "stale" in kinds and t["amended"]:
        due, pages = t["due0"], t["pages0"]
    elif "stale" in kinds:
        return None                                          # cannot plant staleness without an amendment
    if "tz" in kinds:
        h = r.choice([-3, 3])
        due = (datetime.strptime(due, "%Y-%m-%dT%H:%MZ") + timedelta(hours=h)).strftime("%Y-%m-%dT%H:%MZ")
    if "pages" in kinds:
        pages = pages + r.choice([-5, 5])
    w = dict(t["weights"])
    names = list(w)
    if "weights_sum" in kinds:
        w[names[0]] += 5
    if "weight_swap" in kinds:
        a, b = names[0], names[-1]
        if w[a] == w[b]:
            return None
        w[a], w[b] = w[b], w[a]
    sa = t["set_aside"]
    if "setaside" in kinds:
        sa = r.choice([s for s in SETASIDES if s != sa])
    naics = t["naics"]
    if "naics" in kinds:
        naics = naics[:4] + naics[5] + naics[4]
        if naics == t["naics"]:
            return None
    fit = eligible(t["set_aside"], t["naics"], t["size"], sol["profile"])
    if "fit" in kinds:
        fit = not fit
    reqs = [dict(text=q, quote=q) for q in t["reqs"]]
    if "invented" in kinds:
        reqs.append(dict(text="The Contractor shall provide on-site staff in Washington, DC.", quote="The Contractor shall provide on-site staff in Washington, DC."))
    return dict(due=dict(value=due, quote=due_q), pages=dict(value=pages, quote=pages_q),
                weights=w, set_aside=dict(value=sa), naics=naics, fit=fit, requirements=reqs)


KINDS = ["stale", "tz", "pages", "weights_sum", "weight_swap", "setaside", "naics", "fit", "invented"]
