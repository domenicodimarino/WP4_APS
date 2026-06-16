"""
Client dell'Elettore — Fasi 1, 2, 3 e verifica individuale.

Trust anchor hardcoded (distribuzione out-of-band, WP2):
  - PK_Comm       : cifratura della scheda (C_key)
  - PK_Sign_Urna  : verifica della ricevuta R e dello STH
(PK_Sign_IdP e' verificato dall'Urna, non dal client.)

Carico crittografico lato client (volutamente minimale): 1 nonce, 1 AES-CBC,
1 HMAC-SHA256, 1 RSA-OAEP. Tempi nell'ordine dei millisecondi.
"""
from __future__ import annotations

import json
import random
import time

from .. import config
from .. import crypto_primitives as cp
from .. import merkle
from .. import transport
from ..parties.urna import leaf_hash
from ..transport import b64d, b64e


class VoterClient:
    def __init__(self, credentials: str, pk_comm, urna_sign_pk):
        self.credentials = credentials
        self.pk_comm = pk_comm
        self.urna_sign_pk = urna_sign_pk
        # risultati di sessione
        self.token = None
        self.C = None
        self.leaf = None
        self.receipt = None
        self.metrics = {}

    # ---------------- Fase 1 ----------------
    def fase1_richiedi_token(self):
        t0 = time.perf_counter()
        # NB: la verifica è significativa a urne congelate (frozen): il BB non
        # cambia tra inclusion_proof e get_sth, quindi le due root coincidono.
        resp, sent, recv = transport.request(
            config.IDP_HOST, config.IDP_PORT,
            {"op": "request_token", "credentials": self.credentials},
        )
        self.metrics["fase1_rtt_ms"] = (time.perf_counter() - t0) * 1000
        self.metrics["token_bytes"] = recv
        if not resp.get("ok"):
            raise RuntimeError(f"IdP: {resp.get('error')}")
        self.token = {"t_id": resp["t_id"], "sig": resp["sig"]}
        return self.token

    # ---------------- Fase 2 (locale) ----------------
    def fase2_cifra_scheda(self, sindaco: int, lista: int, consiglieri: list[int]):
        V = {"sindaco": sindaco, "lista": lista, "consiglieri": consiglieri}
        v_bytes = json.dumps(V).encode("utf-8")

        t0 = time.perf_counter()
        k_enc = cp.random_bytes(cp.SYM_KEY_LEN)
        k_mac = cp.random_bytes(cp.SYM_KEY_LEN)
        iv = cp.random_bytes(cp.IV_LEN)
        c_sym = cp.aes_cbc_encrypt(k_enc, iv, v_bytes)          # AES-256-CBC
        tag = cp.hmac_sha256(k_mac, iv + c_sym)                 # Encrypt-then-MAC
        c_key = cp.rsa_encrypt(self.pk_comm, k_enc + k_mac)     # RSA-OAEP
        self.metrics["fase2_crypto_ms"] = (time.perf_counter() - t0) * 1000

        self.C = {"c_key": b64e(c_key), "c_sym": b64e(c_sym),
                  "tag": b64e(tag), "iv": b64e(iv)}
        self.leaf = leaf_hash(self.C)                          # H(C) locale
        self.metrics["payload_C_bytes"] = sum(len(self.C[k]) for k in self.C)
        return self.C

    # ---------------- random delay (privacy temporale) ----------------
    def attesa_stocastica(self):
        d = random.uniform(config.RANDOM_DELAY_MIN_S, config.RANDOM_DELAY_MAX_S)
        time.sleep(d)
        self.metrics["random_delay_s"] = d

    # ---------------- Fase 3 ----------------
    def fase3_sottometti(self):
        t0 = time.perf_counter()
        resp, sent, recv = transport.request(
            config.URNA_HOST, config.URNA_PORT,
            {"op": "submit", "C": self.C, "token": self.token},
        )
        self.metrics["fase3_rtt_ms"] = (time.perf_counter() - t0) * 1000
        self.metrics["submit_sent_bytes"] = sent
        if not resp.get("ok"):
            raise RuntimeError(f"Urna: {resp.get('error')}")
        # coerenza H(C) locale vs foglia restituita
        if resp["leaf"] != self.leaf:
            raise RuntimeError("H(C) restituito incoerente con quello locale")
        self.receipt = b64d(resp["receipt"])
        # verifica ricevuta R = Sign_Urna(H(C))
        if not cp.rsa_verify(self.urna_sign_pk, bytes.fromhex(self.leaf), self.receipt):
            raise RuntimeError("Ricevuta non valida")
        self.metrics["receipt_bytes"] = len(self.receipt)
        return self.receipt

    # ---------------- Verifica individuale ----------------
    def verifica_individuale(self):
        """Interroga il BB per la prova di inclusione e verifica STH + root."""
        t0 = time.perf_counter()
        resp, _, _ = transport.request(
            config.URNA_HOST, config.URNA_PORT,
            {"op": "inclusion_proof", "leaf": self.leaf},
        )
        if not resp.get("ok"):
            return False
        proof = [tuple(p) for p in resp["proof"]]
        root = resp["root"]
        ok_proof = merkle.verify_proof(self.leaf, proof, root)

        sth_resp, _, _ = transport.request(
            config.URNA_HOST, config.URNA_PORT, {"op": "get_sth"})
        ok_sth = sth_resp.get("ok") and merkle.verify_sth(sth_resp["sth"], self.urna_sign_pk)
        ok_root = sth_resp.get("ok") and sth_resp["sth"]["root"] == root
        self.metrics["verifica_individuale_ms"] = (time.perf_counter() - t0) * 1000
        return bool(ok_proof and ok_sth and ok_root)

    # ---------------- Edge case: query asincrona dopo drop di rete ----------------
    def query_stato_voto(self):
        resp, _, _ = transport.request(
            config.URNA_HOST, config.URNA_PORT,
            {"op": "inclusion_proof", "leaf": self.leaf},
        )
        return bool(resp.get("ok"))
