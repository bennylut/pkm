from dataclasses import dataclass

from pkm.api.packages.package import PackageDescriptor
from pkm.utils.monitors import MonitoredOperation, MonitoredEvent


class BuildPackageMonitoredOp(MonitoredOperation):
    def __init__(self, package: PackageDescriptor):
        self.package = package


@dataclass
class BuildPackageHookExecutionEvent(MonitoredEvent):
    package: PackageDescriptor
    hook: str
