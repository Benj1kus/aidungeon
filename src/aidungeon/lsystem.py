from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping


@dataclass(frozen=True)
class LSystem:
    axiom: str
    rules: Mapping[str, str]

    def expand(self, iterations: int) -> str:
        current = self.axiom
        for _ in range(max(iterations, 0)):
            next_str = []
            for symbol in current:
                replacement = self.rules.get(symbol)
                next_str.append(replacement if replacement is not None else symbol)
            current = "".join(next_str)
        return current
