from dataclasses import dataclass
from typing import TYPE_CHECKING

from pkm.api.packages.package import PackageDescriptor
from pkm.utils.monitors import MonitoredOperation

if TYPE_CHECKING:
    from pkm.api.packages.package_installation import PackageOperation


@dataclass
class PackageOperationMonitoredOp(MonitoredOperation):
    package: PackageDescriptor
    operation: "PackageOperation"
