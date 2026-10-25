"""python -m capcheck.run <first_seed> <n_seeds> <layouts e.g. AB> [out.json]"""
import json, sys
from collections import Counter
from .gen import make, extract, KINDS
from .check import check, baseline

WANT = dict(stale="STALE_AMENDMENT", tz="VALUE_MISMATCH", pages="VALUE_MISMATCH", weights_sum="WEIGHTS_SUM", weight_swap="WEIGHT_MISMATCH",
            setaside="SETASIDE_MISMATCH", naics="NAICS_MISMATCH", fit="FIT_WRONG", invented="QUOTE_NOT_FOUND")


def run(first, n, layouts):
    R = dict(planted=Counter(), caught=Counter(), named=Counter(), base=Counter(), clean=0, clean_flag=0, base_clean_flag=0, clean_codes=Counter())
    for seed in range(first, first + n):
        for L in layouts:
            sol = make(seed, L)
            rec = extract(sol, seed, ())
            R["clean"] += 1
            v, f = check(sol["text"], rec, sol["profile"])
            if v != "VERIFIED":
                R["clean_flag"] += 1
                R["clean_codes"].update(x["code"] for x in f)
            R["base_clean_flag"] += baseline(sol["text"], rec) != "VERIFIED"
            for k in KINDS:
                bad = extract(sol, seed, (k,))
                if bad is None:
                    continue
                R["planted"][k] += 1
                v, f = check(sol["text"], bad, sol["profile"])
                R["caught"][k] += v != "VERIFIED"
                R["named"][k] += any(x["code"] == WANT[k] for x in f)
                R["base"][k] += baseline(sol["text"], bad) != "VERIFIED"
    return R


if __name__ == "__main__":
    first, n, layouts = int(sys.argv[1]), int(sys.argv[2]), sys.argv[3]
    R = run(first, n, layouts)
    print(f"seeds {first}..{first + n - 1}, layouts {layouts}")
    print(f"planted errors {sum(R['planted'].values())}: checker stopped {sum(R['caught'].values())}, named right {sum(R['named'].values())}; "
          f"quote-exists baseline stopped {sum(R['base'].values())}")
    for k in KINDS:
        print(f"  {k:12s} planted {R['planted'][k]:4d}  stopped {R['caught'][k]:4d}  named {R['named'][k]:4d}  baseline {R['base'][k]:4d}")
    print(f"clean records {R['clean']}: checker flagged {R['clean_flag']} {dict(R['clean_codes'])}; baseline flagged {R['base_clean_flag']}")
    if len(sys.argv) > 4:
        json.dump({k: (dict(v) if isinstance(v, Counter) else v) for k, v in R.items()}, open(sys.argv[4], "w"), indent=1)
