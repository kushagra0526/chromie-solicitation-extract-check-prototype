import sys, pathlib, unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from capcheck.gen import make, extract, KINDS
from capcheck.check import check, baseline, parse_due


class T(unittest.TestCase):
    def test_clean_records_verify(self):
        for seed in range(30):
            for L in "AB":
                sol = make(seed, L)
                v, f = check(sol["text"], extract(sol, seed, ()), sol["profile"])
                self.assertEqual((v, f), ("VERIFIED", []), (seed, L))

    def test_every_planted_error_is_stopped(self):
        for seed in range(30):
            for L in "AB":
                sol = make(seed, L)
                for k in KINDS:
                    bad = extract(sol, seed, (k,))
                    if bad:
                        self.assertNotEqual(check(sol["text"], bad, sol["profile"])[0], "VERIFIED", (seed, L, k))

    def test_stale_value_passes_quote_check_but_not_checker(self):
        for seed in range(60):
            sol = make(seed, "A")
            bad = extract(sol, seed, ("stale",))
            if bad:
                self.assertEqual(baseline(sol["text"], bad), "VERIFIED")
                v, f = check(sol["text"], bad, sol["profile"])
                self.assertIn("STALE_AMENDMENT", [x["code"] for x in f])
                return
        self.fail("no amended solicitation in 60 seeds")

    def test_time_zone_conversion(self):
        self.assertEqual(parse_due("Offers are due no later than 2:00 PM ET on August 21, 2026."), "2026-08-21T18:00Z")
        self.assertEqual(parse_due("by 4:00 PM Pacific Time (PT) on 3 September 2026"), "2026-09-03T23:00Z")

    def test_unreadable_layout_is_held_not_passed(self):
        sol = make(1, "C")
        v, f = check(sol["text"], extract(sol, 1, ()), sol["profile"])
        self.assertEqual(v, "HOLD")
        self.assertIn("UNREAD", [x["code"] for x in f])


if __name__ == "__main__":
    unittest.main()
