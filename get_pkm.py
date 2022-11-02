import json
import sys
import tarfile
from argparse import ArgumentParser, Namespace
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import List
from urllib.request import urlopen

_PYPI_LIST_EP = "https://pypi.org/pypi/pkm/json"


def _install(args: Namespace):
    version = args.version
    with urlopen(_PYPI_LIST_EP) as request:
        response = json.load(request)

    release = list(response["releases"].values())[-1]
    sdist = next(it for it in release if it["packagetype"] == 'sdist')

    with urlopen(sdist["url"]) as request, TemporaryDirectory() as tdir:
        pkm_sdist = Path(tdir) / "pkm.tar.gz"
        pkm_sdist.write_bytes(request.read())

        pkm_unzip = pkm_sdist.parent / "pkm"
        pkm_unzip.mkdir(parents=True)
        with tarfile.open(pkm_sdist) as tar:
            
            import os
            
            def is_within_directory(directory, target):
                
                abs_directory = os.path.abspath(directory)
                abs_target = os.path.abspath(target)
            
                prefix = os.path.commonprefix([abs_directory, abs_target])
                
                return prefix == abs_directory
            
            def safe_extract(tar, path=".", members=None, *, numeric_owner=False):
            
                for member in tar.getmembers():
                    member_path = os.path.join(path, member.name)
                    if not is_within_directory(path, member_path):
                        raise Exception("Attempted Path Traversal in Tar File")
            
                tar.extractall(path, members, numeric_owner=numeric_owner) 
                
            
            safe_extract(tar, pkm_unzip)

        pkm_import = str(next(pkm_unzip.iterdir()) / "src")
        sys.path.insert(1, pkm_import)

        from pkm.api.environments.environment import Environment
        from pkm.api.dependencies.dependency import Dependency
        print("Installing...")
        Environment.current().install([Dependency.parse(f'pkm-cli {version}')])
        print("Done!")


def main(args: List[str]):
    arg_parser = ArgumentParser()
    arg_parser.add_argument("-v", "--version", default="*")

    parsed_args = arg_parser.parse_args(args)
    _install(parsed_args)


if __name__ == '__main__':
    main(sys.argv[1:])
