# Copyright 2026 Ariel Barreiros <arielbarreiros96@icloud.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from datetime import timedelta

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class StockOrderpointStrength(models.Model):
    _name = "stock.orderpoint.strength"
    _description = "Stock Orderpoint Strength"

    active = fields.Boolean(default=True)
    strength = fields.Float(
        required=True,
        default=1.0,
        help="Weight of this location's claim on contended stock. Has no "
        "effect when supply is enough for every competing orderpoint to "
        "reach its target.",
    )
    date_start = fields.Date(required=True, string="From")
    date_stop = fields.Date(required=True, string="To")
    location_id = fields.Many2one(
        comodel_name="stock.location", string="Location", required=True
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Company",
        default=lambda self: self.env.company,
    )

    @api.constrains("strength")
    def _check_strength_positive(self):
        for record in self:
            if record.strength <= 0:
                raise ValidationError(self.env._("Strength must be greater than 0."))

    @api.constrains("date_start", "date_stop")
    def _check_date_window(self):
        for record in self:
            if record.date_stop < record.date_start:
                raise ValidationError(
                    self.env._("The end date must not precede the start date.")
                )

    @api.model
    def _get_effective_strength(self, location, run_date, lead_days=0.0):
        reference_date = run_date + timedelta(days=lead_days)
        records = self.search(
            [
                ("location_id", "=", location.id),
                ("date_start", "<=", reference_date),
                ("date_stop", ">=", reference_date),
            ]
        )
        effective = 1.0
        for record in records:
            effective *= record.strength
        return effective
