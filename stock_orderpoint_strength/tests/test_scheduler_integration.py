# Copyright 2026 Ariel Barreiros <arielbarreiros96@icloud.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from datetime import date

from odoo.tests.common import TransactionCase


class TestSchedulerIntegration(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.warehouse = cls.env.ref("stock.warehouse0")
        cls.hub = cls.warehouse.lot_stock_id
        cls.product = cls.env["product.product"].create(
            {"name": "Strength Test Product", "is_storable": True}
        )
        cls.spoke_a = cls.env["stock.location"].create(
            {
                "name": "Spoke A",
                "usage": "internal",
                "location_id": cls.warehouse.view_location_id.id,
            }
        )
        cls.spoke_b = cls.env["stock.location"].create(
            {
                "name": "Spoke B",
                "usage": "internal",
                "location_id": cls.warehouse.view_location_id.id,
            }
        )
        cls.route = cls.env["stock.route"].create({"name": "Hub to Spokes"})
        internal_picking_type = cls.env.ref("stock.picking_type_internal")
        cls.env["stock.rule"].create(
            {
                "name": "Hub -> Spoke A",
                "action": "pull",
                "location_src_id": cls.hub.id,
                "location_dest_id": cls.spoke_a.id,
                "route_id": cls.route.id,
                "picking_type_id": internal_picking_type.id,
                "warehouse_id": cls.warehouse.id,
            }
        )
        cls.env["stock.rule"].create(
            {
                "name": "Hub -> Spoke B",
                "action": "pull",
                "location_src_id": cls.hub.id,
                "location_dest_id": cls.spoke_b.id,
                "route_id": cls.route.id,
                "picking_type_id": internal_picking_type.id,
                "warehouse_id": cls.warehouse.id,
            }
        )
        cls.strength_model = cls.env["stock.orderpoint.strength"]
        cls.move_model = cls.env["stock.move"]

    def _create_orderpoint(self, location):
        return self.env["stock.warehouse.orderpoint"].create(
            {
                "product_id": self.product.id,
                "location_id": location.id,
                "warehouse_id": self.warehouse.id,
                "route_id": self.route.id,
                "product_min_qty": 10,
                "product_max_qty": 15,
                "trigger": "auto",
            }
        )

    def _set_hub_quantity(self, qty):
        self.env["stock.quant"]._update_available_quantity(self.product, self.hub, qty)

    def _run_scheduler(self):
        self.env["stock.rule"]._run_scheduler_tasks(company_id=self.env.company.id)

    def _moves_for(self, orderpoint):
        return self.move_model.search([("orderpoint_id", "=", orderpoint.id)])

    def test_contended_run(self):
        self._set_hub_quantity(6)
        orderpoint_a = self._create_orderpoint(self.spoke_a)
        orderpoint_b = self._create_orderpoint(self.spoke_b)
        self.strength_model.create(
            {
                "location_id": self.spoke_b.id,
                "strength": 2.0,
                "date_start": date(2000, 1, 1),
                "date_stop": date(2100, 1, 1),
            }
        )
        self._run_scheduler()
        self.assertEqual(
            sum(self._moves_for(orderpoint_a).mapped("product_uom_qty")), 2
        )
        self.assertEqual(
            sum(self._moves_for(orderpoint_b).mapped("product_uom_qty")), 4
        )

    def test_no_contention(self):
        self._set_hub_quantity(40)
        orderpoint_a = self._create_orderpoint(self.spoke_a)
        orderpoint_b = self._create_orderpoint(self.spoke_b)
        self.strength_model.create(
            {
                "location_id": self.spoke_b.id,
                "strength": 2.0,
                "date_start": date(2000, 1, 1),
                "date_stop": date(2100, 1, 1),
            }
        )
        self._run_scheduler()
        self.assertEqual(
            sum(self._moves_for(orderpoint_a).mapped("product_uom_qty")), 15
        )
        self.assertEqual(
            sum(self._moves_for(orderpoint_b).mapped("product_uom_qty")), 15
        )

    def test_stock_in_transit_reduces_request(self):
        self._set_hub_quantity(6)
        orderpoint_a = self._create_orderpoint(self.spoke_a)
        orderpoint_b = self._create_orderpoint(self.spoke_b)
        self.strength_model.create(
            {
                "location_id": self.spoke_b.id,
                "strength": 2.0,
                "date_start": date(2000, 1, 1),
                "date_stop": date(2100, 1, 1),
            }
        )
        self._run_scheduler()
        self.assertEqual(
            sum(self._moves_for(orderpoint_a).mapped("product_uom_qty")), 2
        )
        self.assertEqual(orderpoint_a.qty_to_order_computed, 13)

        self._set_hub_quantity(100)
        self._run_scheduler()
        self.assertEqual(
            sum(self._moves_for(orderpoint_a).mapped("product_uom_qty")), 2 + 13
        )

    def test_no_strength_records_splits_evenly(self):
        self._set_hub_quantity(10)
        orderpoint_a = self._create_orderpoint(self.spoke_a)
        orderpoint_b = self._create_orderpoint(self.spoke_b)
        self._run_scheduler()
        self.assertEqual(
            sum(self._moves_for(orderpoint_a).mapped("product_uom_qty")), 5
        )
        self.assertEqual(
            sum(self._moves_for(orderpoint_b).mapped("product_uom_qty")), 5
        )

    def test_single_orderpoint_group_caps_at_available(self):
        self._set_hub_quantity(4)
        orderpoint_a = self._create_orderpoint(self.spoke_a)
        self._run_scheduler()
        self.assertEqual(
            sum(self._moves_for(orderpoint_a).mapped("product_uom_qty")), 4
        )
