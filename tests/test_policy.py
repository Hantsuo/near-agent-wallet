"""Assertions for the nine scenarios plus ledger behaviour.

Stdlib only: `python -m unittest discover -s tests` from the project root.
"""
from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import scenarios as sc                      # noqa: E402
from ledger import Ledger                   # noqa: E402


class TestScenarios(unittest.TestCase):
    def test_all_scenarios_hold(self):
        for r in sc.run_all():
            with self.subTest(scenario=r.name):
                self.assertTrue(r.passed, f"expected {r.expected}, got {r.actual}: {r.detail}")


class TestLedger(unittest.TestCase):
    def setUp(self):
        self.path = os.path.join(os.path.dirname(__file__), "_tmp_ledger.jsonl")
        if os.path.exists(self.path):
            os.unlink(self.path)

    def tearDown(self):
        if os.path.exists(self.path):
            os.unlink(self.path)

    def test_replay_survives_restart(self):
        engine, ledger, _ = sc._engine()
        ledger.path = self.path
        intent = sc._intent(1, "0.5")
        decision = engine.evaluate(intent, now=sc.T0)
        ledger.settle(intent, decision, at=sc.T0)

        reloaded = Ledger(self.path)
        self.assertTrue(reloaded.has_key(intent.idempotency_key),
                        "a restarted process must still refuse the same intent")

    def test_denied_intents_do_not_consume_budget(self):
        engine, ledger, _ = sc._engine()
        ledger.path = self.path
        denied = engine.evaluate(sc._intent(1, "1000"), now=sc.T0)
        self.assertEqual(denied.level, "deny")
        ledger.settle(sc._intent(1, "1000"), denied, at=sc.T0)
        self.assertEqual(ledger.total_since(sc.T0.replace(hour=0), "NEAR"), 0)

    def test_median_needs_history(self):
        ledger = Ledger(self.path)
        self.assertIsNone(ledger.median_amount("NEAR"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
