from pathlib import Path

from pkm.api.environments.environment import Environment

from pkm_main.repositories.pypi_repository import PyPiRepository
from pkm_main.utils.http.http_client import HttpClient

workspace = Path("/home/bennyl/projects/pkm-new/workspace")

# _METADATA_FILE_RX = re.compile("[^/]*\.dist-info/METADATA")
# numpy_whl = Path("/home/bennyl/projects/pkm-new/workspace/tmp/numpy-1.21.5-cp38-cp38-linux_x86_64.whl")
# with ZipFile(numpy_whl) as zip:
#     for file in zip.namelist():
#         if file.endswith("/METADATA"):
#             print(_METADATA_FILE_RX.fullmatch(file))
#             print("HERE")
#             zip.extract(file, workspace/"tmp/meta")
#
env_path = Path("/home/bennyl/projects/pkm-new/workspace/env-zoo/envs/yyy")
env = Environment(env_path)
http = HttpClient(workspace / "cache/http")
pypi = PyPiRepository(http)

import time

start = time.time()
env.install('allennlp', pypi)
# env.install(['wheel', 'pip', 'setuptools'], pypi)
end = time.time()
print(f"TOOK: {end - start}")

# env.install()
#
#
# with TemporaryDirectory() as tdir:
#     tdir_path = Path(tdir)
#     with ZipFile(numpy_source) as zip:
#         zip.extractall(tdir_path)
#
#     desc = PackageDescriptor('numpy', Version.parse('1.21.5'))
#     package = builder.build(desc, tdir_path / 'numpy-1.21.5', env, pypi)
#     package.install_to(env)
#
#     print("DONE")