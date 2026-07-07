# Copyright 2026 Ariel Barreiros <arielbarreiros96@icloud.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from datetime import date

from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase


class TestStrengthResolution(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.strength_model = cls.env["stock.orderpoint.strength"]
        cls.location = cls.env["stock.location"].create(
            {"name": "Test Spoke", "usage": "internal"}
        )

    def test_no_record_defaults_to_one(self):
        effective = self.strength_model._get_effective_strength(
            self.location, date(2026, 7, 20)
        )
        self.assertEqual(effective, 1.0)

    def test_multiplicative_stacking(self):
        self.strength_model.create(
            {
                "location_id": self.location.id,
                "strength": 2.0,
                "date_start": date(2026, 6, 1),
                "date_stop": date(2026, 8, 31),
            }
        )
        self.strength_model.create(
            {
                "location_id": self.location.id,
                "strength": 0.5,
                "date_start": date(2026, 7, 20),
                "date_stop": date(2026, 7, 20),
            }
        )
        effective = self.strength_model._get_effective_strength(
            self.location, date(2026, 7, 20)
        )
        self.assertEqual(effective, 1.0)

    def test_window_offset_by_lead_time(self):
        self.strength_model.create(
            {
                "location_id": self.location.id,
                "strength": 3.0,
                "date_start": date(2026, 7, 20),
                "date_stop": date(2026, 7, 20),
            }
        )
        active_run = self.strength_model._get_effective_strength(
            self.location, date(2026, 7, 17), lead_days=3
        )
        inactive_run = self.strength_model._get_effective_strength(
            self.location, date(2026, 7, 20), lead_days=3
        )
        self.assertEqual(active_run, 3.0)
        self.assertEqual(inactive_run, 1.0)

    def test_strength_must_be_positive(self):
        with self.assertRaises(ValidationError):
            self.strength_model.create(
                {
                    "location_id": self.location.id,
                    "strength": 0,
                    "date_start": date(2026, 1, 1),
                    "date_stop": date(2026, 12, 31),
                }
            )

    def test_date_window_constraint(self):
        with self.assertRaises(ValidationError):
            self.strength_model.create(
                {
                    "location_id": self.location.id,
                    "strength": 1.0,
                    "date_start": date(2026, 12, 31),
                    "date_stop": date(2026, 1, 1),
                }
            )
