"""
Server di Raccolta — Urna (Fase 3: Sottomissione e Ricevuta) + Bulletin Board.

Stato DETENUTO SOLO DALL'URNA (isolato dall'IdP):
  - SK_Sign_Urna / PK_Sign_Urna : firma di ricevute e STH (RSA-PSS)
  - PK_Sign_IdP                 : trust anchor hardcoded (verifica del Token)
  - blacklist dei T_ID usati    : operazione atomica test-and-set
  - Bulletin Board (Merkle)     : registro append-only dei voti cifrati

L'Urna accetta C "ciecamente": non possiede SK_Comm, non puo' decifrare il voto.

Operazioni esposte:
  op = "submit"          -> Fase 3 (verifica Token, blacklist, append BB, ricevuta R)
  op = "inclusion_proof" -> prova di Merkle per H(C) (verifica individuale / edge case)
  op = "get_sth"         -> STH corrente firmato
  op = "freeze"          -> congela l'urna e trasferisce {C_j} + STH finale (Fase 4)
"""
from __future__ import annotations

import threading
from typing import Dict

from .. import config
from .. import crypto_primitives as cp
from .. import merkle
from ..transport import b64d, b64e
from .server_base import JsonServer


def leaf_hash(C: Dict) -> str:
    """H(C) = SHA-256(C_key || C_sym || T || IV), in hex. Deterministico."""
    raw = b"".join(b64d(C[k]) for k in ("c_key", "c_sym", "tag", "iv"))
    return cp.sha256_hex(raw)


class Urna:
    def __init__(self, idp_sign_pk):
        self.sign_sk, self.sign_pk = cp.generate_keypair()
        self.idp_sign_pk = idp_sign_pk             # hardcoded out-of-band (WP2)
        self.blacklist: set[str] = set()
        self.bb = merkle.BulletinBoard()
        self._lock = threading.Lock()
        self.frozen = False
        self.rejected_log = []                     # log di sicurezza append-only

        self.server = JsonServer(config.URNA_HOST, config.URNA_PORT, "Urna")
        self.server.register("submit", self._submit)
        self.server.register("inclusion_proof", self._inclusion_proof)
        self.server.register("get_sth", self._get_sth)
        self.server.register("freeze", self._freeze)

    # ----- Fase 3 -----
    def _submit(self, req: Dict) -> Dict:
        if self.frozen:
            return {"ok": False, "error": "Urna chiusa"}
        C = req.get("C", {})
        token = req.get("token", {})

        # 2. Pre-validazione dimensionale (anti-DoS) + struttura attesa
        total = sum(len(C.get(k, "")) for k in ("c_key", "c_sym", "tag", "iv"))
        if total > config.MAX_PAYLOAD_BYTES * 2:    # *2: stima base64 vs byte
            self.rejected_log.append("payload oversize")
            return {"ok": False, "error": "Payload oltre la soglia (DoS)"}
        if not all(k in C for k in ("c_key", "c_sym", "tag", "iv")):
            return {"ok": False, "error": "Formato C non valido"}
        if not all(k in token for k in ("t_id", "sig")):
            return {"ok": False, "error": "Token malformato"}

        # 3. Verifica firma IdP sul Token
        t_id = b64d(token["t_id"])
        if not cp.rsa_verify(self.idp_sign_pk, t_id, b64d(token["sig"])):
            self.rejected_log.append("token signature invalid")
            return {"ok": False, "error": "Firma Token non valida"}

        t_id_hex = t_id.hex()
        l = leaf_hash(C)

        # 4. Blacklist atomica (test-and-set) + archiviazione
        with self._lock:
            if t_id_hex in self.blacklist:
                self.rejected_log.append("replay/multi-voto")
                return {"ok": False, "error": "Token gia' usato (replay)"}
            self.blacklist.add(t_id_hex)
            self.bb.append(l, C)

        # 5. Ricevuta R = Sign_{SK_Sign_Urna}(H(C))
        R = cp.rsa_sign(self.sign_sk, bytes.fromhex(l))
        return {"ok": True, "leaf": l, "receipt": b64e(R)}

    # ----- Verifica individuale / edge case (query asincrona) -----
    def _inclusion_proof(self, req: Dict) -> Dict:
        res = self.bb.inclusion_proof(req["leaf"])
        if res is None:
            return {"ok": False, "error": "Foglia non presente nel BB"}
        idx, proof, root = res
        return {"ok": True, "index": idx, "proof": proof, "root": root}

    def _get_sth(self, req: Dict) -> Dict:
        if self.bb.size() == 0:
            return {"ok": False, "error": "BB vuoto"}
        sth = merkle.build_sth(self.bb.size(), self.bb.current_root(), self.sign_sk)
        return {"ok": True, "sth": sth}

    # ----- Fase 4: congelamento e trasferimento alla Commissione -----
    def _freeze(self, req: Dict) -> Dict:
        with self._lock:
            self.frozen = True
            n = self.bb.size()
            root = self.bb.current_root()
            sth = merkle.build_sth(n, root, self.sign_sk)
            ciphertexts = list(self.bb.payloads)
        return {"ok": True, "ciphertexts": ciphertexts, "sth": sth, "leaves": self.bb.leaves}

    def start(self):
        self.server.start()

    def stop(self):
        self.server.stop()
