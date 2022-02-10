from time import sleep

from pkm.api.pkm import pkm
from pkm.resolution.resolution_monitor import DependencyResolutionMonitoredOp, DependencyResolutionIterationEvent, \
    DependencyResolutionConclusionEvent
from pkm.utils.http.http_monitors import FetchResourceMonitoredOp, FetchResourceCacheHitEvent, \
    FetchResourceDownloadStartEvent
from pkm.utils.monitors import Monitor
from pkm.utils.processes import ProcessExecutionMonitoredOp, ProcessExecutionExitEvent
from pkm.utils.strings import startswith_any
from pkm_cli.display.display import Display
from pkm_cli.display.progress import Progress
from pkm_cli.display.spinner import Spinner


def with_external_proc_execution(e: ProcessExecutionMonitoredOp):
    # def on_output(oe: ProcessExecutionOutputLineEvent):
    #     Display.print(f"[{e.id}]: {oe.line}", use_markup=False)

    def on_exit(ee: ProcessExecutionExitEvent):
        Display.print(f"[{e.execution_name}]: Ended with exit code: {ee.exit_code}", use_markup=False)

    with e.listen(**locals()), Display.show(Spinner(f"Executing process {e.execution_name}: '{' '.join(e.cmd)}'")):
        yield


def with_fetch_resource(e: FetchResourceMonitoredOp):
    if startswith_any(e.resource_name, ("matching packages for", "metadata for")):
        return  # do not monitor these resources for now..

    done: bool = False

    def on_cache_hit(_: FetchResourceCacheHitEvent):
        Display.print(f"{e.resource_name} found in cache, using it.")

    def on_download(download: FetchResourceDownloadStartEvent):

        def monitor():
            with Display.show(Progress(f"Fetch {e.resource_name}", download.file_size)) as progress:
                while not done:
                    newsize = download.store_path.stat().st_size if download.store_path.exists() else 0
                    progress.completed = newsize
                    sleep(0.25)

        pkm.threads.submit(monitor)

    with e.listen(**locals()):
        try:
            yield
        finally:
            done = True


def with_dependency_resolution(e: DependencyResolutionMonitoredOp):
    progress = Progress("Dependency Resolution", 1)

    def on_iteration(ie: DependencyResolutionIterationEvent):
        progress.completed = len(ie.packages_completed)
        progress.total = len(ie.packages_requested)

    def on_conclusion(ce: DependencyResolutionConclusionEvent):
        d = {**ce.decisions}
        del d['installation-request']
        Display.print(f"Reached decision: {d}")

    with e.listen(**locals()), Display.show(progress):
        yield


# def with_package_build(e: BuildPackageMonitoredOp):
# we need component stack..


_listeners = locals()


def listen():
    Monitor.add_listeners(**_listeners)
