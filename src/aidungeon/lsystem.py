from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Mapping, Sequence, Tuple


@dataclass(frozen=True)
class RuleOption:
    production: str
    weight: float


class LSystem:
    def __init__(
        self,
        axiom: str,
        rules: Mapping[str, Sequence[RuleOption]],
        seed: int | None = None,
    ) -> None:
        self.axiom = axiom
        self._random = random.Random(seed)
        self._rules = {
            symbol: self._prepare_options(symbol, options)
            for symbol, options in rules.items()
        }

    @staticmethod
    def _prepare_options(
        symbol: str, options: Sequence[RuleOption]
    ) -> Tuple[float, Sequence[Tuple[float, str]]]:
        cumulative: list[Tuple[float, str]] = []
        total = 0.0
        for option in options:
            production = option.production
            if not production:
                raise ValueError(f"Empty production detected for symbol '{symbol}'.")
            weight = float(option.weight)
            if weight <= 0:
                raise ValueError(f"Weight must be positive for symbol '{symbol}'.")
            total += weight
            cumulative.append((total, production))
        if not cumulative:
            raise ValueError(f"No valid productions provided for symbol '{symbol}'.")
        return total, tuple(cumulative)

    def expand(self, iterations: int) -> str:
        current = self.axiom
        for _ in range(max(iterations, 0)):
            next_parts = []
            for symbol in current:
                choice = self._rules.get(symbol)
                if not choice:
                    next_parts.append(symbol)
                    continue
                total, cumulative = choice
                if len(cumulative) == 1:
                    next_parts.append(cumulative[0][1])
                    continue
                pick = self._random.random() * total
                for threshold, production in cumulative:
                    if pick <= threshold:
                        next_parts.append(production)
                        break
                else:  # pragma: no cover - safety fallback
                    next_parts.append(cumulative[-1][1])
            current = "".join(next_parts)
        return current
