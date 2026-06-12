"""
Shamir's Secret Sharing (t, n)  --  WP4.

[ASSUNZIONE DICHIARATA — "SHAMIR SIMULATO"]
Lo schema implementato di seguito e' matematicamente reale (polinomio di grado
t-1 su un campo finito GF(p), ricostruzione via interpolazione di Lagrange in
x = 0). E' pero' dichiarato "simulato" perche':
  1. la cerimonia di distribuzione e ricomposizione avviene in un unico
     processo, non in un protocollo distribuito tra n dispositivi fisici;
  2. non si implementa una Distributed Key Generation: la SK_Comm e' generata
     centralmente e poi posta sotto una "soglia" tramite il meccanismo
     descritto in commissione.py (la chiave privata PEM viene cifrata con
     AES-256 sotto un segreto a 256 bit, ed e' quest'ultimo ad essere
     condiviso con Shamir). t share su n sono necessarie e sufficienti per
     ricostruire il segreto e quindi decifrare SK_Comm.

Proprieta' garantita (e verificata nei test): t-1 share non rivelano alcuna
informazione sul segreto (sicurezza incondizionata, perfect secrecy).
"""
from __future__ import annotations

import secrets
from typing import List, Tuple

# Primo di Mersenne 2^521 - 1: campo abbastanza grande per un segreto da 256 bit.
PRIME = 2 ** 521 - 1

Share = Tuple[int, int]  # (x, y)


def _eval_poly(coeffs: List[int], x: int) -> int:
    """Valuta il polinomio (Horner) in x mod PRIME. coeffs[0] = termine noto."""
    acc = 0
    for c in reversed(coeffs):
        acc = (acc * x + c) % PRIME
    return acc


def split_secret(secret_int: int, t: int, n: int) -> List[Share]:
    """Frammenta secret_int in n share con soglia t. Termine noto = segreto."""
    if not (0 < t <= n):
        raise ValueError("Richiesto 0 < t <= n")
    if secret_int >= PRIME:
        raise ValueError("Segreto troppo grande per il campo scelto")
    # Polinomio: a_0 = segreto, a_1..a_{t-1} casuali.
    coeffs = [secret_int] + [secrets.randbelow(PRIME) for _ in range(t - 1)]
    return [(x, _eval_poly(coeffs, x)) for x in range(1, n + 1)]


def reconstruct_secret(shares: List[Share]) -> int:
    """Ricompone il segreto da >= t share via interpolazione di Lagrange in 0."""
    if not shares:
        raise ValueError("Nessuna share fornita")
    secret = 0
    for j, (xj, yj) in enumerate(shares):
        num, den = 1, 1
        for m, (xm, _) in enumerate(shares):
            if m == j:
                continue
            num = (num * (-xm)) % PRIME
            den = (den * (xj - xm)) % PRIME
        lagrange = (num * pow(den, -1, PRIME)) % PRIME
        secret = (secret + yj * lagrange) % PRIME
    return secret % PRIME


def secret_to_key(secret_int: int) -> bytes:
    """Deriva una chiave AES-256 (32 byte) dal segreto ricostruito."""
    from .crypto_primitives import sha256
    return sha256(secret_int.to_bytes(66, "big"))
