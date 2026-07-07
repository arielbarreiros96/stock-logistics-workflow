# Copyright 2026 Ariel Barreiros <arielbarreiros96@icloud.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging

from odoo import models
from odoo.tools import split_every

_logger = logging.getLogger(__name__)


class StockRule(models.Model):
    _inherit = "stock.rule"

    def _run_scheduler_tasks(self, use_new_cursor=False, company_id=False):
        if use_new_cursor:
            self.env["ir.cron"]._commit_progress(
                remaining=self._get_scheduler_tasks_to_do()
            )

        domain = self._get_orderpoint_domain(company_id=company_id)
        orderpoints = self.env["stock.warehouse.orderpoint"].search(domain)
        orderpoints.sudo()._compute_qty_to_order_computed()
        orderpoints.sudo()._compute_deadline_date()
        orderpoints.sudo()._apply_strength_weighting()
        # _procure_orderpoint_confirm opens a fresh cursor per batch when
        # use_new_cursor=True; commit so those cursors see our writes.
        if use_new_cursor:
            self.env.cr.commit()
        orderpoints.sudo()._procure_orderpoint_confirm(
            use_new_cursor=use_new_cursor,
            company_id=company_id,
            raise_user_error=False,
        )

        if use_new_cursor:
            self.env["ir.cron"]._commit_progress(1)

        domain = self._get_moves_to_assign_domain(company_id)
        moves_to_assign = self.env["stock.move"].search(
            domain,
            limit=None,
            order="reservation_date, priority desc, date asc, id asc",
        )
        for moves_chunk in split_every(1000, moves_to_assign.ids):
            self.env["stock.move"].browse(moves_chunk).sudo()._action_assign()
            if use_new_cursor:
                self.env.cr.commit()
                _logger.info(
                    "A batch of %d moves are assigned and committed", len(moves_chunk)
                )

        if use_new_cursor:
            self.env["ir.cron"]._commit_progress(1)

        self.env["stock.quant"]._quant_tasks()

        if use_new_cursor:
            self.env["ir.cron"]._commit_progress(1)
