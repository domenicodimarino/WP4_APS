"""Server TCP minimale: un handler per connessione, dispatch su 'op'."""
from __future__ import annotations

import json
import socket
import struct
import threading
from typing import Any, Callable, Dict

HEADER = struct.Struct(">I")


def _recv_exact(sock: socket.socket, n: int) -> bytes:
    buf = b""
    while len(buf) < n:
        chunk = sock.recv(n - len(buf))
        if not chunk:
            raise ConnectionError("Connessione chiusa")
        buf += chunk
    return buf


class JsonServer:
    """Espone un dispatch {op -> handler(payload) -> dict} su una porta TCP."""

    def __init__(self, host: str, port: int, name: str):
        self.host, self.port, self.name = host, port, name
        self.handlers: Dict[str, Callable[[Dict[str, Any]], Dict[str, Any]]] = {}
        self._sock: socket.socket | None = None
        self._thread: threading.Thread | None = None
        self._running = False

    def register(self, op: str, handler: Callable[[Dict[str, Any]], Dict[str, Any]]):
        self.handlers[op] = handler

    def _handle(self, conn: socket.socket):
        try:
            (length,) = HEADER.unpack(_recv_exact(conn, HEADER.size))
            req = json.loads(_recv_exact(conn, length).decode("utf-8"))
            op = req.get("op")
            handler = self.handlers.get(op)
            if handler is None:
                resp = {"ok": False, "error": f"op sconosciuta: {op}"}
            else:
                try:
                    resp = handler(req)
                except Exception as exc:  # errore applicativo -> risposta strutturata
                    resp = {"ok": False, "error": str(exc)}
            data = json.dumps(resp).encode("utf-8")
            conn.sendall(HEADER.pack(len(data)) + data)
        finally:
            conn.close()

    def _serve(self):
        assert self._sock is not None
        while self._running:
            try:
                conn, _ = self._sock.accept()
            except OSError:
                break
            threading.Thread(target=self._handle, args=(conn,), daemon=True).start()

    def start(self):
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._sock.bind((self.host, self.port))
        self._sock.listen(64)
        self._running = True
        self._thread = threading.Thread(target=self._serve, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        if self._sock:
            self._sock.close()
