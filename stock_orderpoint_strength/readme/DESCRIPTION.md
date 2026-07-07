Odoo's automatic replenishment is greedy: when several locations compete
for the same limited stock, whichever orderpoint reaches the scheduler
queue first claims what it needs, starving the rest. This is especially
problematic in a Hub & Spoke model, where limited stock at the hub should
be distributed across several shops rather than saturating one and
starving the others.

This module introduces a **strength**: a temporary weight assigned to a
location that determines how much of the contested stock an orderpoint
replenishing that location is entitled to claim relative to the others,
when there is not enough free stock to satisfy every competing orderpoint
at once. The orderpoint itself already pins down the product and route;
the strength only scopes by location. It has no effect when supply is
sufficient for everyone to reach their target.
