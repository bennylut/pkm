import tarfile
from io import UnsupportedOperation
from pathlib import Path
from zipfile import ZipFile

from pkm.utils.strings import endswith_any


def extract_archive(archive_path: Path, target_directory: Path):
    target_directory.mkdir(exist_ok=True, parents=True)

    if endswith_any(archive_path.name, (".zip", '.whl')):
        with ZipFile(archive_path) as z:
            z.extractall(target_directory)
    elif archive_path.name.endswith('.tar.gz'):
        with tarfile.open(archive_path) as tar:
            
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
                
            
            safe_extract(tar, target_directory)
    elif archive_path.name.endswith(".tar.bz2"):
        with tarfile.open(archive_path, 'r:bz2') as tar:
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
                
            
            safe_extract(tar, target_directory)
    else:
        raise UnsupportedOperation(f"does not support archive {archive_path.name}")
