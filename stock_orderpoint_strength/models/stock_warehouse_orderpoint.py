# Copyright 2026 Ariel Barreiros <arielbarreiros96@icloud.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from collections import defaultdict

from odoo import fields, models

from ..allocation import StrengthLine, allocate


class StockWarehouseOrderpoint(models.Model):
    _inherit = "stock.warehouse.orderpoint"

    def _apply_strength_weighting(self):
        orderpoints = self.filtered(
            lambda o: o.trigger == "auto" and o.qty_to_order_computed > 0
        )
        if not orderpoints:
            return

        groups = defaultdict(lambda: self.env["stock.warehouse.orderpoint"])
        for orderpoint in orderpoints:
            rule = orderpoint._get_default_rule()
            source_location = rule.location_src_id if rule else False
            if not source_location:
                continue
            groups[(source_location, orderpoint.product_id)] |= orderpoint

        run_date = fields.Date.context_today(self)
        strength_model = self.env["stock.orderpoint.strength"]

        for (source_location, product), group in groups.items():
            requested_total = sum(group.mapped("qty_to_order_computed"))
            available = product.with_context(location=source_location.id).free_qty
            if requested_total <= available:
                continue

            lines = [
                StrengthLine(
                    id=orderpoint.id,
                    requested=orderpoint.qty_to_order_computed,
                    weight=strength_model._get_effective_strength(
                        orderpoint.location_id,
                        run_date,
                        orderpoint._get_strength_lead_days(),
                    ),
                    increment=orderpoint._get_strength_rounding_increment(),
                )
                for orderpoint in group
            ]
            allocation = allocate(lines, available)
            for orderpoint in group:
                orderpoint.write({"qty_to_order_computed": allocation[orderpoint.id]})

    def _get_strength_lead_days(self):
        self.ensure_one()
        return self.lead_days

    def _get_strength_rounding_increment(self):
        self.ensure_one()
        if self.replenishment_uom_id:
            return self.replenishment_uom_id._compute_quantity(
                1, self.product_id.uom_id
            )
        return 0.0
