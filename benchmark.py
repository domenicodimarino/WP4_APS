"""
Misura delle prestazioni richiesta dal WP4:
  - costo computazionale delle operazioni crittografiche
  - dimensione dei messaggi scambiati
  - latenza delle operazioni di verifica
  - tempi di interazione (round-trip delle fasi)

Uso:  python -m wp4.benchmark [N_elettori] [N_ripetizioni]
Salva un report in formato Markdown in wp4/benchmark_report.md
"""
from __future__ import annotations

import json
import os
import statistics
import sys
import time

from . import config
from . import crypto_primitives as cp
from . import merkle
from . import shamir
from .parties.client import VoterClient
from .parties.commissione import Commissione
from .parties.idp import IdentityProvider
from .parties.urna import Urna
from .transport import request


def bench(fn, reps: int):
    """Ritorna (media_ms, dev_std_ms) su 'reps' esecuzioni di fn."""
    samples = []
    for _ in range(reps):
        t0 = time.perf_counter()
        fn()
        samples.append((time.perf_counter() - t0) * 1000)
    mean = statistics.mean(samples)
    sd = statistics.stdev(samples) if len(samples) > 1 else 0.0
    return mean, sd


def microbench(reps: int):
    """Microbenchmark delle primitive crittografiche."""
    sk, pk = cp.generate_keypair()
    km = cp.random_bytes(64)
    iv = cp.random_bytes(cp.IV_LEN)
    ballot = json.dumps({"sindaco": 1, "lista": 10, "consiglieri": [101, 102]}).encode()
    c_sym = cp.aes_cbc_encrypt(km[:32], iv, ballot)
    c_key = cp.rsa_encrypt(pk, km)
    tag = cp.hmac_sha256(km[32:], iv + c_sym)
    sig = cp.rsa_sign(sk, cp.sha256(ballot))
    secret = 12345678901234567890

    rows = []
    rows.append(("RSA-2048 keygen (Gen)", *bench(lambda: cp.generate_keypair(), max(3, reps // 50))))
    rows.append(("RSA-OAEP encrypt (E_pk)", *bench(lambda: cp.rsa_encrypt(pk, km), reps)))
    rows.append(("RSA-OAEP decrypt (D_sk)", *bench(lambda: cp.rsa_decrypt(sk, c_key), reps)))
    rows.append(("RSA-PSS sign (Sign)", *bench(lambda: cp.rsa_sign(sk, cp.sha256(ballot)), reps)))
    rows.append(("RSA-PSS verify (Verify)", *bench(lambda: cp.rsa_verify(pk, cp.sha256(ballot), sig), reps)))
    rows.append(("AES-256-CBC encrypt", *bench(lambda: cp.aes_cbc_encrypt(km[:32], iv, ballot), reps)))
    rows.append(("AES-256-CBC decrypt", *bench(lambda: cp.aes_cbc_decrypt(km[:32], iv, c_sym), reps)))
    rows.append(("HMAC-SHA256", *bench(lambda: cp.hmac_sha256(km[32:], iv + c_sym), reps)))
    rows.append(("SHA-256", *bench(lambda: cp.sha256(ballot), reps)))
    rows.append((f"Shamir split (t={config.SHAMIR_T},n={config.SHAMIR_N})",
                 *bench(lambda: shamir.split_secret(secret, config.SHAMIR_T, config.SHAMIR_N), reps)))
    sh = shamir.split_secret(secret, config.SHAMIR_T, config.SHAMIR_N)
    rows.append(("Shamir reconstruct", *bench(lambda: shamir.reconstruct_secret(sh[:config.SHAMIR_T]), reps)))
    return rows


def merklebench(n_leaves: int, reps: int):
    leaves = [cp.sha256_hex(cp.random_bytes(32)) for _ in range(n_leaves)]
    _, tree = merkle.build_merkle_tree(leaves)
    proof = merkle.generate_proof(0, tree)
    root = tree[-1][0]
    rows = []
    rows.append((f"Merkle build ({n_leaves} foglie)", *bench(lambda: merkle.build_merkle_tree(leaves), reps)))
    rows.append(("Merkle proof gen", *bench(lambda: merkle.generate_proof(0, tree), reps)))
    rows.append(("Merkle proof verify", *bench(lambda: merkle.verify_proof(leaves[0], proof, root), reps)))
    return rows


def interactionbench(n_elettori: int):
    """Esegue un'elezione e raccoglie tempi di interazione e dimensioni messaggi."""
    anagrafe = {f"e{i}" for i in range(n_elettori)}
    idp = IdentityProvider(anagrafe)
    urna = Urna(idp.sign_pk)
    commissione = Commissione()
    idp.start(); urna.start()
    time.sleep(0.2)

    f1, f2, f3, vi = [], [], [], []
    sizes = {}
    for i in range(n_elettori):
        c = VoterClient(f"e{i}", commissione.pk_comm, urna.sign_pk)
        c.fase1_richiedi_token()
        c.fase2_cifra_scheda(1, 10, [101, 102])
        c.fase3_sottometti()
        c.verifica_individuale()
        f1.append(c.metrics["fase1_rtt_ms"])
        f2.append(c.metrics["fase2_crypto_ms"])
        f3.append(c.metrics["fase3_rtt_ms"])
        vi.append(c.metrics["verifica_individuale_ms"])
        sizes = c.metrics

    sth = request(config.URNA_HOST, config.URNA_PORT, {"op": "get_sth"})[0]["sth"]
    sth_bytes = len(json.dumps(sth))
    pr = request(config.URNA_HOST, config.URNA_PORT,
                {"op": "inclusion_proof", "leaf": urna.bb.leaves[0]})[0]
    proof_bytes = len(json.dumps(pr["proof"]))

    idp.stop(); urna.stop()

    timings = [
        ("Fase 1 — RTT richiesta Token", statistics.mean(f1), statistics.pstdev(f1)),
        ("Fase 2 — cifratura client (locale)", statistics.mean(f2), statistics.pstdev(f2)),
        ("Fase 3 — RTT submit + ricevuta", statistics.mean(f3), statistics.pstdev(f3)),
        ("Verifica individuale (proof+STH)", statistics.mean(vi), statistics.pstdev(vi)),
    ]
    msg_sizes = [
        ("Token (T_ID + firma), risposta IdP", sizes["token_bytes"]),
        ("Payload voto C = (C_key,C_sym,T,IV)", sizes["payload_C_bytes"]),
        ("Richiesta submit completa (C+Token)", sizes["submit_sent_bytes"]),
        ("Ricevuta R (firma RSA-PSS)", sizes["receipt_bytes"]),
        ("STH (n,ts,root,firma)", sth_bytes),
        ("Prova di inclusione Merkle", proof_bytes),
    ]
    return timings, msg_sizes


def fmt_time_table(title, rows):
    out = [f"### {title}", "", "| Operazione | Media (ms) | Dev. std (ms) |", "|---|---:|---:|"]
    for name, mean, sd in rows:
        out.append(f"| {name} | {mean:.4f} | {sd:.4f} |")
    return "\n".join(out) + "\n"


def fmt_size_table(title, rows):
    out = [f"### {title}", "", "| Messaggio | Dimensione (byte) |", "|---|---:|"]
    for name, size in rows:
        out.append(f"| {name} | {size} |")
    return "\n".join(out) + "\n"


def main(n_elettori=16, reps=200):
    print(f"Benchmark in corso (N={n_elettori}, reps={reps})...")
    crypto_rows = microbench(reps)
    merkle_rows = merklebench(n_elettori, reps)
    timings, msg_sizes = interactionbench(n_elettori)

    report = ["# WP4 — Report Prestazioni",
              "",
              f"Parametri: N_elettori={n_elettori}, ripetizioni microbench={reps}, "
              f"Shamir (t={config.SHAMIR_T}, n={config.SHAMIR_N}), RSA-2048.",
              "",
              fmt_time_table("Costo operazioni crittografiche", crypto_rows),
              fmt_time_table("Strutture autenticate (Bulletin Board)", merkle_rows),
              fmt_time_table("Tempi di interazione e latenza di verifica", timings),
              fmt_size_table("Dimensione dei messaggi scambiati", msg_sizes)]
    text = "\n".join(report)

    out_path = os.path.join(os.path.dirname(__file__), "benchmark_report.md")
    with open(out_path, "w") as f:
        f.write(text)
    print(text)
    print(f"\nReport salvato in {out_path}")


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 16
    r = int(sys.argv[2]) if len(sys.argv) > 2 else 200
    main(n, r)
