from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Optional


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    parameters: dict[str, Any]


ToolFn = Callable[..., Awaitable[Any]]


class ToolRegistry:
    def __init__(self) -> None:
        self._specs: dict[str, ToolSpec] = {}
        self._fns: dict[str, ToolFn] = {}

    def register(self, spec: ToolSpec, fn: ToolFn) -> None:
        self._specs[spec.name] = spec
        self._fns[spec.name] = fn

    def get_spec(self, name: str) -> Optional[ToolSpec]:
        return self._specs.get(name)

    def get_fn(self, name: str) -> Optional[ToolFn]:
        return self._fns.get(name)

    def list_specs(self) -> list[ToolSpec]:
        return list(self._specs.values())

    def list_names(self) -> list[str]:
        return list(self._specs.keys())
