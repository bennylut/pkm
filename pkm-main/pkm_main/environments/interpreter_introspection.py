import json
import platform
import subprocess
from io import UnsupportedOperation
from pathlib import Path


class InterpreterIntrospection:
    def __init__(self, version: str):
        self.version = version

    @classmethod
    def local(cls) -> "InterpreterIntrospection":
        return InterpreterIntrospection(platform.python_version())

    @classmethod
    def remote(cls, interpreter: Path) -> "InterpreterIntrospection":
        out = subprocess.run([str(interpreter.absolute()), __file__], capture_output=True)
        if out.returncode != 0:
            raise UnsupportedOperation(f"cannot introspect interpreter {interpreter}, errorcode: {out.returncode}")
        return InterpreterIntrospection(**json.loads(out.stdout))


if __name__ == '__main__':
    print(json.dumps(InterpreterIntrospection.local().__dict__))
    exit(0)
