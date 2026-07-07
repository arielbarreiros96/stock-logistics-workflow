# Copyright 2026 Ariel Barreiros <arielbarreiros96@icloud.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.tests.common import BaseCase

from odoo.addons.stock_orderpoint_strength.allocation import StrengthLine, allocate


class TestAllocation(BaseCase):
    def test_no_contention(self):
        lines = [
            StrengthLine("A", requested=15, weight=1, increment=1),
            StrengthLine("B", requested=15, weight=2, increment=1),
        ]
        self.assertEqual(allocate(lines, 30), {"A": 15, "B": 15})

    def test_proportional_split(self):
        lines = [
            StrengthLine("A", requested=15, weight=1, increment=1),
            StrengthLine("B", requested=15, weight=2, increment=1),
        ]
        self.assertEqual(allocate(lines, 6), {"A": 2, "B": 4})

    def test_cap_and_redistribute(self):
        lines = [
            StrengthLine("A", requested=15, weight=1, increment=1),
            StrengthLine("B", requested=15, weight=2, increment=1),
        ]
        self.assertEqual(allocate(lines, 23), {"A": 8, "B": 15})

    def test_factor_below_1(self):
        lines = [
            StrengthLine("A", requested=10, weight=1, increment=1),
            StrengthLine("B", requested=10, weight=0.5, increment=1),
        ]
        self.assertEqual(allocate(lines, 6), {"A": 4, "B": 2})

    def test_indivisible_increment(self):
        lines = [
            StrengthLine("A", requested=30, weight=1, increment=10),
            StrengthLine("B", requested=30, weight=1, increment=10),
        ]
        self.assertEqual(allocate(lines, 12), {"A": 10, "B": 0})

    def test_total_never_exceeds_available(self):
        lines = [
            StrengthLine("A", requested=17, weight=3, increment=4),
            StrengthLine("B", requested=11, weight=1, increment=3),
        ]
        result = allocate(lines, 13)
        self.assertLessEqual(sum(result.values()), 13)
        for line in lines:
            self.assertLessEqual(result[line.id], line.requested)
            units = result[line.id] / line.increment
            self.assertAlmostEqual(units, round(units))
