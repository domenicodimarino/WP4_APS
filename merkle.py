"""
Bulletin Board come albero di Merkle autenticato append-only (WP2 sez. BB).

L'implementazione dell'albero, delle prove di inclusione e della loro verifica
e' adattata fedelmente da 0_merkle_tree.py del corso:
  - foglia        l_i = H(C_i)                       (hex SHA-256)
  - nodo interno  v   = H(figlio_sx || figlio_dx)
  - foglia spaiata duplicata (duplicate-last-if-odd)
  - prova = lista di (posizione, hash_fratello)

Sopra l'albero si definisce lo Signed Tree Head (STH), firmato dall'Urna in
RSA-PSS, che vincola (n, ts, root) e rende rilevabile ogni alterazione
retroattiva del registro.
"""
from __future__ import annotations

import hashlib
import time
from typing import List, Tuple

from . import crypto_primitives as cp


def _h(data: str) -> str:
    """SHA-256 su stringa esadecimale -> hex (come nel lab)."""
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def build_merkle_tree(leaves: List[str]) -> Tuple[str, List[List[str]]]:
    """Costruisce l'albero dai digest-foglia (gia' in hex). tree[0] = foglie."""
    if not leaves:
        raise ValueError("Nessuna foglia: Bulletin Board vuoto")
    tree = [list(leaves)]
    while len(tree[-1]) > 1:
        level = tree[-1]
        if len(level) % 2 == 1:
            level = level + [level[-1]]
        tree.append([_h(level[i] + level[i + 1]) for i in range(0, len(level), 2)])
    return tree[-1][0], tree


def generate_proof(leaf_index: int, tree: List[List[str]]) -> List[Tuple[str, str]]:
    """Prova di inclusione per la foglia leaf_index: [(posizione, hash), ...]."""
    proof, index = [], leaf_index
    for level in tree[:-1]:
        if len(level) % 2 == 1:
            level = level + [level[-1]]
        sibling = index ^ 1
        position = "right" if sibling > index else "left"
        proof.append((position, level[sibling]))
        index //= 2
    return proof


def verify_proof(leaf_hash: str, proof: List[Tuple[str, str]], root: str) -> bool:
    """Verifica che leaf_hash, ricomposto con la prova, dia esattamente root."""
    current = leaf_hash
    for position, sibling in proof:
        if position == "right":
            current = _h(current + sibling)
        else:
            current = _h(sibling + current)
    return current == root


class BulletinBoard:
    """Registro pubblico append-only. Detenuto dall'Urna; espone solo letture."""

    def __init__(self):
        self.leaves: List[str] = []     # H(C_i) in hex, in ordine di arrivo
        self.payloads: List[dict] = []  # C completo associato (per la Fase 4)

    def append(self, leaf_hash: str, payload: dict) -> int:
        """Aggiunge una foglia. Ritorna l'indice assegnato."""
        self.leaves.append(leaf_hash)
        self.payloads.append(payload)
        return len(self.leaves) - 1

    def current_root(self) -> str:
        root, _ = build_merkle_tree(self.leaves)
        return root

    def inclusion_proof(self, leaf_hash: str):
        """Ritorna (indice, prova, root) per una data foglia, o None se assente."""
        if leaf_hash not in self.leaves:
            return None
        idx = self.leaves.index(leaf_hash)
        root, tree = build_merkle_tree(self.leaves)
        return idx, generate_proof(idx, tree), root

    def size(self) -> int:
        return len(self.leaves)


def build_sth(n: int, root: str, urna_sign_sk) -> dict:
    """STH_n = (n, ts, root, Sign_{SK_Sign_Urna}(H(n || ts || root)))."""
    ts = int(time.time())
    message = f"{n}|{ts}|{root}".encode()
    signature = cp.rsa_sign(urna_sign_sk, message)
    return {"n": n, "ts": ts, "root": root, "sig": signature.hex()}


def verify_sth(sth: dict, urna_sign_pk) -> bool:
    """Verifica la firma RSA-PSS sullo STH."""
    message = f"{sth['n']}|{sth['ts']}|{sth['root']}".encode()
    return cp.rsa_verify(urna_sign_pk, message, bytes.fromhex(sth["sig"]))
