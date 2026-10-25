# capcheck: check an AI-extracted solicitation before a firm bids on it

Government-contracting tools read a solicitation and extract the due date, page limit, evaluation weights, set-aside and mandatory requirements, each with a quote. A quote that exists can still carry a stale value (an amendment moved the date), the wrong time zone, or weights that don't add up. This prototype checks an extraction record against the solicitation text and its amendments only, and returns **VERIFIED / FIX (with the corrected value) / HOLD** with the reason.

Problem links: Capto's own page says every extracted requirement cites its source and that tracked notices are monitored for amendments (https://gocapto.com).

## What it checks
`QUOTE_NOT_FOUND`, `STALE_AMENDMENT` (value from before the last amendment), `VALUE_MISMATCH` (e.g. time zone), `WEIGHTS_SUM`, `WEIGHT_MISMATCH`, `SETASIDE_MISMATCH`, `NAICS_MISMATCH`, `FIT_WRONG` (eligibility vs a company profile: NAICS, size standard, certifications), and `UNREAD` (text it cannot parse is held, never passed).

## Results (synthetic solicitations, simulated extractor with one planted error at a time)
Dev: seeds 0-99, layouts A and B: 1,612/1,612 planted errors stopped, 0/200 clean records flagged.

Held-out: seeds 1000-1199, three layouts, layout C (numeric dates, "12:00 noon Central", spelled-out page limits, "N percent" weights, different set-aside wording) never seen when the checker was written. The seeds and layout list were committed before the first run.

| | quote-exists check | capcheck |
|---|---|---|
| planted errors stopped | 600 / 4,911 | 4,908 / 4,911 (the 3 misses are one seed where two amendments cancel out, so the planted "stale" value equals the current one) |
| named with the right code | - | 4,872 / 4,911 |
| clean records flagged | 0 / 600 | 0 / 600 |

First run, before any fix: 200/600 clean records were held as `UNREAD` (every layout C record: the date parser did not handle numeric dates, "noon", spelled time zones, "N percent" weights), and 4,645 errors were named correctly. Two fixes later (and one stray backspace character in a regex from my own tooling) the numbers above. Held-out results are in `out/heldout_run1.txt` and `out/heldout_run2.txt`.

## Limits (read these)
- The generator, the extractor and the checker are all mine, so this is near-circular: it shows the checks work, not that Capto has these errors.
- The quote-exists baseline is weak by construction, because the simulated extractor always copies real sentences.
- Fictional solicitations, three phrasings, daylight-time dates only. Real solicitations are far messier (tables, PDFs, scanned attachments).
- Not tested on any real extractor, and nothing here touches Capto/Chromie systems.

## Run
```
python -m unittest tests.test_capcheck
python -m capcheck.run 0 100 AB
python -m capcheck.run 1000 200 ABC
```
Python 3 standard library only.

Unofficial prototype by Kushagra Pratap Singh. Not affiliated with Chromie or Capto.
