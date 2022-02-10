from __future__ import annotations

from dataclasses import dataclass
from typing import Dict

from pkm.api.versions.version import Version
from pkm.utils.monitors import MonitoredOperation, MonitoredEvent
from pkm.utils.types import IterableWithLen


class DependencyResolutionMonitoredOp(MonitoredOperation):
    ...


@dataclass
class DependencyResolutionIterationEvent(MonitoredEvent):
    packages_completed: IterableWithLen[str]
    packages_requested: IterableWithLen[str]
    current_package: str


@dataclass
class DependencyResolutionConclusionEvent(MonitoredEvent):
    decisions: Dict[str, Version]
