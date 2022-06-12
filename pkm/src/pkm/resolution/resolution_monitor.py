from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Any

from pkm.api.versions.version import Version
from pkm.utils.monitors import MonitoredOperation, MonitoredEvent
from pkm.utils.types import MeasuredIterable


@dataclass
class DependencyResolutionMonitoredOp(MonitoredOperation):
    ...


@dataclass
class DependencyResolutionIterationEvent(MonitoredEvent):
    packages_completed: MeasuredIterable[str]
    packages_requested: MeasuredIterable[str]
    current_package: Any


@dataclass
class DependencyResolutionConclusionEvent(MonitoredEvent):
    decisions: Dict[Any, Version]
