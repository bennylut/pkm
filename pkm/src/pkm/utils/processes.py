import os
import platform
import subprocess
import sys
from dataclasses import dataclass
from subprocess import CompletedProcess
from typing import List, NoReturn, Mapping

from pkm.utils.monitors import MonitoredOperation, MonitoredEvent

_IS_WINDOWS = platform.system() == 'Windows'


def execvpe(cmd: str, args: List[str], env: Mapping[str, str]) -> NoReturn:
    if _IS_WINDOWS:
        sys.exit(subprocess.run([cmd, *args], env=env).returncode)

    os.execvpe(cmd, [cmd, *args], env)


def monitored_run(execution_name: str, cmd: List[str], **subprocess_run_kwargs) -> CompletedProcess:
    with ProcessExecutionMonitoredOp(execution_name, cmd) as mpo:
        subprocess_run_kwargs['stdout'] = subprocess.PIPE
        subprocess_run_kwargs['stderr'] = subprocess.STDOUT
        proc = subprocess.Popen(cmd, **subprocess_run_kwargs)
        stdout = proc.stdout

        def decode(line):  # noqa
            nonlocal decode
            if hasattr(line, 'decode'):
                decode = lambda line: line.decode()  # noqa
            else:
                decode = lambda line: line  # noqa

            return decode(line)

        while (line := stdout.readline()) or (rcode := proc.poll()) is None:
            ProcessExecutionOutputLineEvent(decode(line).strip()).notify(mpo)

        ProcessExecutionExitEvent(rcode).notify(mpo)
        return CompletedProcess(cmd, rcode)


@dataclass
class ProcessExecutionMonitoredOp(MonitoredOperation):
    execution_name: str
    cmd: List[str]


@dataclass
class ProcessExecutionOutputLineEvent(MonitoredEvent):
    line: str


@dataclass
class ProcessExecutionExitEvent(MonitoredEvent):
    exit_code: int
