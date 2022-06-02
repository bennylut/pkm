from __future__ import annotations

import multiprocessing
import socket
import socketserver
from http.server import SimpleHTTPRequestHandler
from pathlib import Path
from socketserver import ThreadingMixIn
from threading import Thread, Lock, Condition, RLock
from time import sleep
from typing import Set

from lxml import etree
from sphinx.application import Sphinx
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from utils.generate_api_docs import BUILD_API_LIST_CONFIG_KEY, APIGenerator

_RELOAD_KEEP_SCROLL = [".documentwrapper"]

_RELOAD_SCRIPT = f"""
    reloadKeepScroll = {repr(_RELOAD_KEEP_SCROLL)};
    
    function reload() {{
        let keepScrollElements = {{}};
        for (let r of reloadKeepScroll){{
            selection = document.querySelector(r);
            if (selection) {{
                keepScrollElements[r] = selection.scrollTop;
            }}
        }}
        
        localStorage['__hot_reload_scroll__'] = JSON.stringify(keepScrollElements);
        location.reload();
    }}
    
    function restoreScroll() {{
        scrolls = JSON.parse(localStorage['__hot_reload_scroll__'] || "{{}}");
        localStorage.removeItem('__hot_reload_scroll__');
        for (let r of reloadKeepScroll){{
            scroll = scrolls[r];
            if (scroll) {{
                selection = document.querySelector(r);
                if (selection) {{
                    selection.scrollTop = scroll;
                }}
            }}
        }}
    }}
    
    window.addEventListener("load", restoreScroll);
    
    const evtSource = new EventSource("__hot_reload__");
    evtSource.onmessage = function(event) {{
        if (event.data == 'reload') reload();
        
    }} 
    
    window.addEventListener('beforeunload', function() {{
        evtSource.close();
    }});
"""


class SphinxAutoreloadHandler(SimpleHTTPRequestHandler):

    def __init__(self, request: bytes, client_address: tuple[str, int], server: SphinxAutoreloadServer):
        self.watcher = server.watcher
        self.output_dir = server.output_dir
        super().__init__(request, client_address, server, directory=str(server.output_dir))

    def rewrite_html(self, source: Path) -> bytes:
        tree = etree.fromstring(source.read_text())
        script = etree.Element("script")
        script.text = _RELOAD_SCRIPT
        tree.xpath("//html/head")[0].append(script)
        return etree.tostring(tree, encoding="utf-8", method="html")

    def do_GET(self) -> None:
        if self.path.endswith("/__hot_reload__"):
            def post_events():
                self.connection.setblocking(True)
                while True:
                    try:
                        if self.watcher.await_changes():
                            self.connection.send(f"data: reload\n\n".encode())
                        else:
                            self.connection.send(f"data: heartbeat\n\n".encode())
                    except ConnectionError:
                        return

            self.send_response(200)
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Type", "text/event-stream")
            self.end_headers()

            post_events()
            return

        path = self.output_dir / self.path.lstrip("/")
        if path.is_dir() and (index := path / "index.html").exists():
            path = index

        if path.exists() and path.suffix == ".html":
            rewrite = self.rewrite_html(path)
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.send_header("Content-Length", str(len(rewrite)))
            self.end_headers()

            self.wfile.write(rewrite)
            return

        super().do_GET()


class SphinxAutoreloadServer(ThreadingMixIn, socketserver.TCPServer):
    def __init__(self, source_dir: Path, output_dir: Path, port: int = 8000):
        super().__init__(("", port), SphinxAutoreloadHandler)

        sphinx = Sphinx(
            str(source_dir), str(source_dir), str(output_dir), str(output_dir / ".doctrees"), "html",
            parallel=multiprocessing.cpu_count())

        self.watcher = SphinxWatcher(sphinx)
        self._port = port
        self.output_dir = output_dir
        self.daemon_threads = True

    # https://stackoverflow.com/questions/6380057/python-binding-socket-address-already-in-use
    def server_bind(self):
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.bind(self.server_address)

    def serve_forever(self, *args, **kwargs) -> None:
        self.watcher.start()
        super().serve_forever(*args, **kwargs)


class SphinxWatcher(FileSystemEventHandler):
    def __init__(self, sphinx: Sphinx):
        self.sphinx = sphinx
        self._changed_files: Set[Path] = set()
        self._throttle_thread = Thread(target=self._throttle, daemon=True)
        self._observer = Observer()
        self._observer.daemon = True
        self._lock = Lock()

        self._reschedule()
        self._change_lock = RLock()
        self._change_condition = Condition(self._change_lock)

    def _reschedule(self):
        sphinx = self.sphinx
        self._observer.unschedule_all()
        self._observer.schedule(self, str(Path(sphinx.confdir) / 'conf.py'), False)
        self._observer.schedule(self, sphinx.srcdir, True)
        packages = getattr(sphinx.config, BUILD_API_LIST_CONFIG_KEY, [])
        for package in packages:
            self._observer.schedule(self, str(APIGenerator.path_for(package)), True)

    def start(self):
        self.sphinx.build()
        self._throttle_thread.start()
        self._observer.start()

    def on_any_event(self, event):
        path = Path(event.src_path).resolve()
        if path.is_dir() and event.event_type == "modified":
            return

        if not path.name.endswith("~"):
            with self._lock:
                self._changed_files.add(path)

    def _throttle(self):
        while True:
            changes = None
            with self._lock:
                if self._changed_files:
                    changes = self._changed_files
                    self._changed_files = set()
            if changes:
                self._handle_changes(changes)
            sleep(1)

    def await_changes(self, timeout: int = 3) -> bool:
        with self._change_lock:
            return self._change_condition.wait(timeout)

    def _handle_changes(self, changes: Set[Path]):
        sphinx = self.sphinx
        conf_path = Path(sphinx.confdir) / 'conf.py'

        rst_files = []
        build_mode = "selected_files"

        for change in changes:
            if change == conf_path:
                build_mode = "restart"
                break

            if change.suffix == ".rst":
                rst_files.append(change)
                continue

            build_mode = "all_files"

        if build_mode == "restart":
            self.sphinx = Sphinx(sphinx.srcdir, sphinx.confdir, sphinx.outdir, sphinx.doctreedir, sphinx.builder.name,
                                 parallel=sphinx.parallel)

            self.sphinx.build()
        elif build_mode == "all_files":
            self.sphinx.build()
        else:
            self.sphinx.build(filenames=[str(p) for p in rst_files])

        with self._change_lock:
            self._change_condition.notify_all()
