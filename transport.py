"""
Trasporto di rete del prototipo.

Messaggi JSON incorniciati (length-prefixed, 4 byte big-endian) su socket TCP
di localhost. I campi binari viaggiano in base64.

[ASSUNZIONE DICHIARATA — "TLS FUORI PERIMETRO"]
Il protocollo WP2 prevede TLS 1.3 a protezione del canale. Nel prototipo il
canale e' in CHIARO: TLS e' esplicitamente escluso dal perimetro di
implementazione. Cio' NON indebolisce le proprieta' applicative dimostrate
(autenticita' del Token via RSA-PSS, segretezza del voto via schema ibrido
RSA-OAEP+AES, integrita' via HMAC), che non dipendono dal canale. L'unica
proprieta' demandata a TLS in WP2 — la riservatezza delle credenziali
anagrafiche in Fase 1 e la protezione anti-eavesdropping di rete — e' fuori
dal perimetro della simulazione e va assunta garantita in deployment.
"""
from __future__ import annotations

import base64
import json
import socket
import struct
from typing import Any, Dict

HEADER = struct.Struct(">I")  # lunghezza payload, 4 byte


def b64e(b: bytes) -> str:
    return base64.b64encode(b).decode("ascii")


def b64d(s: str) -> bytes:
    return base64.b64decode(s.encode("ascii"))


def _send(sock: socket.socket, obj: Dict[str, Any]) -> int:
    data = json.dumps(obj).encode("utf-8")
    sock.sendall(HEADER.pack(len(data)) + data)
    return len(data)


def _recv_exact(sock: socket.socket, n: int) -> bytes:
    buf = b""
    while len(buf) < n:
        chunk = sock.recv(n - len(buf))
        if not chunk:
            raise ConnectionError("Connessione chiusa prematuramente")
        buf += chunk
    return buf


def _recv(sock: socket.socket) -> Dict[str, Any]:
    (length,) = HEADER.unpack(_recv_exact(sock, HEADER.size))
    return json.loads(_recv_exact(sock, length).decode("utf-8"))


def request(host: str, port: int, obj: Dict[str, Any]) -> tuple[Dict[str, Any], int, int]:
    """Apre una connessione, invia obj, riceve la risposta e chiude.

    Ritorna (risposta, byte_inviati, byte_ricevuti) per la misura della
    dimensione dei messaggi scambiati (richiesta dal WP4).
    """
    with socket.create_connection((host, port)) as sock:
        sent = _send(sock, obj)
        # misura grezza dei byte ricevuti
        (length,) = HEADER.unpack(_recv_exact(sock, HEADER.size))
        raw = _recv_exact(sock, length)
        recv = HEADER.size + length
        return json.loads(raw.decode("utf-8")), sent, recv
