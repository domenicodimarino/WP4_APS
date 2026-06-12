"""
Identity Provider — Fase 1 (Identificazione e Rilascio del Gettone).

Stato DETENUTO SOLO DALL'IdP (isolamento => dimostra la separazione dei
registri richiesta dall'assunzione di non-collusione IdP-Urna):
  - SK_Sign_IdP / PK_Sign_IdP : coppia di firma del Token (RSA-PSS)
  - anagrafe elettorale        : insieme degli aventi diritto
  - registro 'gettone rilasciato' (NON 'ha votato')

Operazione esposta:
  op = "request_token", credentials -> Token = (T_ID, sig_IdP(T_ID))

L'IdP marca l'utente come "gettone rilasciato" e rifiuta una seconda
emissione (unicita' a monte). Non vede mai il voto e non partecipa alla Fase 3.
"""
from __future__ import annotations

import threading
from typing import Dict

from .. import config
from .. import crypto_primitives as cp
from ..transport import b64e
from .server_base import JsonServer


class IdentityProvider:
    def __init__(self, anagrafe: set[str]):
        self.sign_sk, self.sign_pk = cp.generate_keypair()
        self.anagrafe = set(anagrafe)            # credenziali valide (aventi diritto)
        self.gettone_rilasciato: set[str] = set()
        self._lock = threading.Lock()
        self.server = JsonServer(config.IDP_HOST, config.IDP_PORT, "IdP")
        self.server.register("request_token", self._request_token)

    # -- handler Fase 1 --
    def _request_token(self, req: Dict) -> Dict:
        cred = req.get("credentials")
        # 2-3. Verifica avente diritto
        if cred not in self.anagrafe:
            return {"ok": False, "error": "Elettore non in anagrafe"}
        with self._lock:  # unicita' del rilascio (operazione critica)
            if cred in self.gettone_rilasciato:
                return {"ok": False, "error": "Gettone gia' rilasciato"}
            # 4. Nonce T_ID ad alta entropia
            t_id = cp.random_bytes(32)
            # 5. Firma RSA-PSS del Token
            sig = cp.rsa_sign(self.sign_sk, t_id)
            # 6. Marca utente come 'gettone rilasciato'
            self.gettone_rilasciato.add(cred)
        return {"ok": True, "t_id": b64e(t_id), "sig": b64e(sig)}

    def start(self):
        self.server.start()

    def stop(self):
        self.server.stop()
