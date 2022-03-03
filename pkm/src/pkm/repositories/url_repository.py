from pathlib import Path
from typing import List

from pkm.api.dependencies.dependency import Dependency
from pkm.api.packages.package import Package, PackageDescriptor
from pkm.api.packages.standard_package import PackageArtifact, AbstractPackage
from pkm.api.pkm import pkm
from pkm.api.repositories.repository import AbstractRepository
from pkm.utils.http.http_client import Url


class UrlRepository(AbstractRepository):

    def __init__(self):
        super().__init__('url')

    def _do_match(self, dependency: Dependency) -> List[Package]:
        if not (vurl := dependency.version_spec.specific_url()):
            return []

        return [UrlPackage(PackageDescriptor(dependency.package_name, vurl), vurl.url)]


class UrlPackage(AbstractPackage):
    def __init__(self, desc: PackageDescriptor, url: str):
        purl = Url.parse(url)
        file_name = Path(purl.path).name
        super().__init__(desc, [PackageArtifact(file_name)])
        self._url = url

    def _retrieve_artifact(self, artifact: PackageArtifact) -> Path:
        return pkm.httpclient.fetch_resource(str(self._url)).data
