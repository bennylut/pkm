# # # from pkm.utils.http.http_client import HttpClient
# # # from pathlib import Path
# # #
# # # workspace = Path("/home/bennyl/projects/pkm-new/workspace")
# # # http = HttpClient(workspace / "test-artifacts")
# # #
# # # http.fetch_resource("https://stackoverflow.com/questions/3947120/does-python-urllib2-automatically-uncompress-gzip-data-fetched-from-webpage")
# #
# # #
# # from pathlib import Path
# #
# # from pkm.api.environments.environment import Environment
# # #
# # # from pkm_main.repositories.pypi_repository import PyPiRepository
# # # from pkm_main.utils.http.http_client import HttpClient
# # #
# # #
# # # # _METADATA_FILE_RX = re.compile("[^/]*\.dist-info/METADATA")
# # # # numpy_whl = Path("/home/bennyl/projects/pkm-new/workspace/tmp/numpy-1.21.5-cp38-cp38-linux_x86_64.whl")
# # # # with ZipFile(numpy_whl) as zip:
# # # #     for file in zip.namelist():
# # # #         if file.endswith("/METADATA"):
# # # #             print(_METADATA_FILE_RX.fullmatch(file))
# # # #             print("HERE")
# # # #             zip.extract(file, workspace/"tmp/meta")
# # # #
# # from pkm.api.pkm import pkm
# #
# # env_path = Path("/home/bennyl/projects/pkm-new/workspace/env-zoo/envs/yyy")
# # env = Environment(env_path)
# # # http = HttpClient(workspace / "cache/http")
# # # pypi = PyPiRepository(http)
# # #
# # import time
# # env.install(['pip', 'setuptools', 'wheel'], pkm.repositories.pypi)
# # # env.remove('allennlp')
# # # start = time.time()
# # # env.install('allennlp', pkm.repositories.pypi)
# # # end = time.time()
# # # print(f"TOOK: {end - start}")
# # #
# # # # env.install()
# # # #
# # # #
# # # # with TemporaryDirectory() as tdir:
# # # #     tdir_path = Path(tdir)
# # # #     with ZipFile(numpy_source) as zip:
# # # #         zip.extractall(tdir_path)
# # # #
# # # #     desc = PackageDescriptor('numpy', Version.parse('1.21.5'))
# # # #     package = builder.build(desc, tdir_path / 'numpy-1.21.5', env, pypi)
# # # #     package.install_to(env)
# # # #
# # # #     print("DONE")
# # from pkm.api.dependencies.dependency import Dependency
# #
# # d = Dependency.parse_pep508('bamba; extra==xxx')
# # print(d)
# # from pkm.api.packages.package import PackageDescriptor
# #
# # n = PackageDescriptor.normalize_name('bamba.-15__1ש150')
# # print(n)
# from pathlib import Path
#
# file = Path("/home/bennyl/projects/pkm-new/workspace/env-zoo/envs/yyy/lib/python3.8/site-packages/attrs")
# for f in file.rglob('*'):
#     print(f.relative_to(file))
from pathlib import Path

file = Path("x.tar.gz")
print(file.name[:-len('.tar.gz')])