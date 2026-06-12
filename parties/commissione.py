"""
Commissione di Scrutinio — Fase 4 (Scrutinio).

Detiene PK_Comm (pubblica, usata dal client per cifrare C_key) e una versione
di SK_Comm posta SOTTO SOGLIA (t, n) tramite Shamir (dichiarato simulato):

  setup:
    - genera (PK_Comm, SK_Comm)
    - estrae un segreto S a 256 bit, lo frammenta in n share Shamir (soglia t)
    - cifra SK_Comm (PEM) con AES-256-CBC sotto chiave K = SHA256(S)
    - distrugge SK_Comm in chiaro; conserva solo {blob cifrato, IV} e le share

  scrutinio (a urne chiuse, con >= t share):
    1. ricompone S via Lagrange -> K -> decifra e ricarica SK_Comm
    2. shuffle stocastico dei ciphertext (anti de-anonimizzazione temporale)
    3. per ogni scheda: D_OAEP(C_key) -> k_enc||k_mac
       VERIFICA HMAC su IV||C_sym  (Encrypt-then-MAC) PRIMA di toccare il padding
       -> se fallisce: "nulla per violazione integrita'" (blocco Padding Oracle)
       -> altrimenti D_AES(IV, C_sym) -> V, poi validazione semantica
    4. aggrega e pubblica risultati + lista {V} (verificabilita' universale)
"""
from __future__ import annotations

import json
import secrets

from .. import config
from .. import crypto_primitives as cp
from .. import shamir
from ..transport import b64d


class Commissione:
    def __init__(self, t: int = config.SHAMIR_T, n: int = config.SHAMIR_N):
        self.t, self.n = t, n
        # 1. coppia di cifratura della Commissione
        sk_comm, self.pk_comm = cp.generate_keypair()
        # 2. segreto S e frammentazione Shamir (t, n)  -- "simulato"
        secret_int = secrets.randbits(256)
        self.shares = shamir.split_secret(secret_int, t, n)
        # 3. cifra SK_Comm sotto K = SHA256(S); distrugge SK_Comm in chiaro
        wrap_key = shamir.secret_to_key(secret_int)
        self._wrap_iv = cp.random_bytes(cp.IV_LEN)
        self._sk_comm_blob = cp.aes_cbc_encrypt(
            wrap_key, self._wrap_iv, cp.privkey_to_pem(sk_comm)
        )
        del sk_comm, secret_int, wrap_key  # nessun SPOF: la chiave non esiste piu' in chiaro

    # --- ricomposizione della chiave a soglia (cerimonia) ---
    def _reconstruct_sk(self, provided_shares):
        if len(provided_shares) < self.t:
            raise PermissionError(
                f"Soglia non raggiunta: {len(provided_shares)} share su {self.t} richieste"
            )
        secret_int = shamir.reconstruct_secret(provided_shares[: self.t])
        wrap_key = shamir.secret_to_key(secret_int)
        pem = cp.aes_cbc_decrypt(wrap_key, self._wrap_iv, self._sk_comm_blob)
        return cp.pem_to_privkey(pem)

    # --- Fase 4 ---
    def tally(self, ciphertexts, provided_shares):
        """Esegue lo spoglio. Ritorna (risultati, schede in chiaro, statistiche)."""
        sk_comm = self._reconstruct_sk(provided_shares)

        # 2. shuffle stocastico (rompe la correlazione ordine-arrivo / ordine-spoglio)
        idx = list(range(len(ciphertexts)))
        secrets.SystemRandom().shuffle(idx)
        shuffled = [ciphertexts[i] for i in idx]

        plain_votes = []
        nulle_integrita = nulle_semantica = valide = 0
        agg_sindaci, agg_liste, agg_consiglieri = {}, {}, {}

        for C in shuffled:
            c_key = b64d(C["c_key"])
            c_sym = b64d(C["c_sym"])
            tag = b64d(C["tag"])
            iv = b64d(C["iv"])

            # 3a. estrazione chiavi simmetriche
            try:
                km = cp.rsa_decrypt(sk_comm, c_key)
            except Exception:
                nulle_integrita += 1
                continue
            k_enc, k_mac = km[:cp.SYM_KEY_LEN], km[cp.SYM_KEY_LEN:]

            # 3b. VERIFICA HMAC su IV||C_sym PRIMA del padding (anti Padding Oracle)
            if not cp.hmac_verify(k_mac, iv + c_sym, tag):
                nulle_integrita += 1
                continue

            # 3c. solo ora si decifra (padding mai usato come oracle)
            try:
                v_bytes = cp.aes_cbc_decrypt(k_enc, iv, c_sym)
                v = json.loads(v_bytes.decode("utf-8"))
            except Exception:
                nulle_integrita += 1
                continue

            # 4. validazione semantica
            if not config.scheda_valida_semantica(v):
                nulle_semantica += 1
                plain_votes.append({"valida": False, "voto": v})
                continue

            valide += 1
            plain_votes.append({"valida": True, "voto": v})
            agg_sindaci[v["sindaco"]] = agg_sindaci.get(v["sindaco"], 0) + 1
            agg_liste[v["lista"]] = agg_liste.get(v["lista"], 0) + 1
            for c in v["consiglieri"]:
                agg_consiglieri[c] = agg_consiglieri.get(c, 0) + 1

        risultati = {
            "sindaci": agg_sindaci,
            "liste": agg_liste,
            "consiglieri": agg_consiglieri,
        }
        stats = {
            "totali": len(ciphertexts),
            "valide": valide,
            "nulle_integrita": nulle_integrita,
            "nulle_semantica": nulle_semantica,
        }
        return risultati, plain_votes, stats
