# Copyright 2026 Ariel Barreiros <arielbarreiros96@icloud.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import math
from collections.abc import Hashable
from dataclasses import dataclass

EPSILON = 1e-6


@dataclass(frozen=True)
class StrengthLine:
    id: Hashable
    requested: float
    weight: float
    increment: float


def allocate(lines: list[StrengthLine], available: float) -> dict[Hashable, float]:
    continuous = _water_fill(lines, available)
    return _round_to_increments(lines, continuous, available)


def _water_fill(lines: list[StrengthLine], available: float) -> dict[Hashable, float]:
    allocated = {line.id: 0.0 for line in lines}
    active = {line.id: line for line in lines}
    pool = available

    while active and pool > EPSILON:
        total_weight = sum(line.weight for line in active.values())
        if total_weight <= EPSILON:
            break

        capped_ids = []
        for line in active.values():
            share = pool * line.weight / total_weight
            remaining_capacity = line.requested - allocated[line.id]
            if share >= remaining_capacity - EPSILON:
                allocated[line.id] += remaining_capacity
                pool -= remaining_capacity
                capped_ids.append(line.id)

        if capped_ids:
            for line_id in capped_ids:
                del active[line_id]
            continue

        for line in active.values():
            allocated[line.id] += pool * line.weight / total_weight
        pool = 0.0
        break

    return allocated


def _round_to_increments(
    lines: list[StrengthLine],
    continuous: dict[Hashable, float],
    available: float,
) -> dict[Hashable, float]:
    allocated = {}
    leftover = available
    for line in lines:
        if line.increment > EPSILON:
            units = math.floor(continuous[line.id] / line.increment + EPSILON)
            allocated[line.id] = units * line.increment
        else:
            allocated[line.id] = continuous[line.id]
        leftover -= allocated[line.id]

    while True:
        eligible = [
            line
            for line in lines
            if line.increment > EPSILON
            and leftover >= line.increment - EPSILON
            and allocated[line.id] + line.increment <= line.requested + EPSILON
        ]
        if not eligible:
            break
        best = max(eligible, key=lambda line: line.weight)
        allocated[best.id] += best.increment
        leftover -= best.increment

    return allocated
