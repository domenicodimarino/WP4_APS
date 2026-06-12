"""
Orchestratore della simulazione end-to-end.

Avvia i tre attori infrastrutturali come server/oggetti a stato ISOLATO
(IdP, Urna, Commissione), distribuisce i trust anchor (hardcoding out-of-band),
fa votare N elettori (Fasi 1-2-3), esegue lo scrutinio (Fase 4) e le verifiche
individuale e universale. Dimostra inoltre i casi limite del WP2.

Uso:  python -m wp4.run_election [N_elettori]
"""
from __future__ import annotations

import copy
import os
import random
import sys
import time

from . import config
from . import crypto_primitives as cp
from .parties.client import VoterClient
from .parties.commissione import Commissione
from .parties.idp import IdentityProvider
from .parties.urna import Urna, leaf_hash
from .transport import b64d, b64e, request


def sezione(titolo: str):
    print("\n" + "=" * 70)
    print(titolo)
    print("=" * 70)


def voto_casuale():
    sindaco = random.choice(list(config.SINDACI))
    lista = random.choice(list(config.LISTE))
    
    # Estrae i candidati disponibili solo per la lista estratta casualmente
    consiglieri_disponibili = list(config.CONSIGLIERI.get(lista, {}).keys())
    
    # Seleziona un numero di preferenze da 0 al massimo consentito
    k_preferenze = random.randint(0, min(config.MAX_PREFERENZE_CONSIGLIERI, len(consiglieri_disponibili)))
    consiglieri_scelti = random.sample(consiglieri_disponibili, k=k_preferenze)
    
    return sindaco, lista, consiglieri_scelti


def main(n_elettori: int = 8):
    random.seed()

    # ---- Setup attori (stato isolato) ----
    sezione("SETUP — generazione chiavi e distribuzione trust anchor")
    anagrafe = {f"elettore_{i}" for i in range(n_elettori)}
    idp = IdentityProvider(anagrafe)
    urna = Urna(idp.sign_pk)                       # PK_Sign_IdP hardcoded nell'Urna
    commissione = Commissione()                    # SK_Comm sotto soglia Shamir (t,n)
    idp.start(); urna.start()
    time.sleep(0.2)
    print(f"IdP, Urna avviati. Anagrafe: {n_elettori} aventi diritto.")
    print(f"Commissione: SK_Comm frammentata Shamir (t={config.SHAMIR_T}, n={config.SHAMIR_N}).")
    print("TLS fuori perimetro; canale in chiaro, sicurezza applicativa attiva.")

    pk_comm = commissione.pk_comm
    urna_sign_pk = urna.sign_pk

    # ---- Fasi 1-2-3 per ogni elettore ----
    sezione("FASI 1-2-3 — autenticazione, cifratura e sottomissione")
    clients = []
    voti_attesi = {"sindaci": {}, "liste": {}, "consiglieri": {}}
    for i in range(n_elettori):
        c = VoterClient(f"elettore_{i}", pk_comm, urna_sign_pk)
        c.fase1_richiedi_token()
        s, l, cons = voto_casuale()
        c.fase2_cifra_scheda(s, l, cons)
        c.attesa_stocastica()
        c.fase3_sottometti()
        clients.append(c)
        voti_attesi["sindaci"][s] = voti_attesi["sindaci"].get(s, 0) + 1
        voti_attesi["liste"][l] = voti_attesi["liste"].get(l, 0) + 1
        for x in cons:
            voti_attesi["consiglieri"][x] = voti_attesi["consiglieri"].get(x, 0) + 1
    print(f"{n_elettori} elettori hanno votato. Ricevute verificate.")
    print(f"Dimensione BB (foglie): {urna.bb.size()}")

    # ---- Casi limite ----
    sezione("CASI LIMITE")
    # 1) doppio rilascio gettone dallo stesso elettore (unicita' a monte)
    dup, _, _ = request(config.IDP_HOST, config.IDP_PORT,
                        {"op": "request_token", "credentials": "elettore_0"})
    print(f"[Unicita' IdP]  secondo gettone a elettore_0 -> ok={dup['ok']} ({dup.get('error','')})")

    # 2) replay dello stesso Token sull'Urna
    replay_c = VoterClient("elettore_1", pk_comm, urna_sign_pk)
    replay_c.token = clients[1].token            # riusa un Token gia' speso
    replay_c.fase2_cifra_scheda(1, 10, [101])
    try:
        replay_c.fase3_sottometti()
        print("[Replay Urna]   ERRORE: replay accettato")
    except RuntimeError as e:
        print(f"[Replay Urna]   replay rifiutato -> {e}")

    # 3) Token con firma manomessa
    forged = VoterClient("elettore_2", pk_comm, urna_sign_pk)
    forged.token = {"t_id": b64e(cp.random_bytes(32)), "sig": b64e(cp.random_bytes(256))}
    forged.fase2_cifra_scheda(1, 10, [101])
    try:
        forged.fase3_sottometti()
        print("[Forge Token]   ERRORE: token falso accettato")
    except RuntimeError as e:
        print(f"[Forge Token]   token falso rifiutato -> {e}")

    # 4) manipolazione bit del ciphertext -> intercettata da HMAC (anti Padding Oracle)
    tampered = copy.deepcopy(clients[0].C)
    raw = bytearray(b64d(tampered["c_sym"]))
    raw[0] ^= 0x01
    tampered["c_sym"] = b64e(bytes(raw))
    tampered_ct = [tampered]
    _, _, stats_t = commissione.tally(tampered_ct, commissione.shares)
    print(f"[Padding Oracle] scheda manomessa -> nulle_integrita={stats_t['nulle_integrita']} "
          f"(HMAC blocca prima dell'unpad)")

    # ---- Fase 4: scrutinio ----
    sezione("FASE 4 — scrutinio (soglia Shamir, shuffle, Encrypt-then-MAC)")
    freeze, _, _ = request(config.URNA_HOST, config.URNA_PORT, {"op": "freeze"})
    ciphertexts = freeze["ciphertexts"]
    sth_finale = freeze["sth"]

    # soglia insufficiente -> rifiuto
    try:
        commissione.tally(ciphertexts, commissione.shares[: config.SHAMIR_T - 1])
        print("[Soglia]        ERRORE: scrutinio con t-1 share")
    except PermissionError as e:
        print(f"[Soglia]        t-1 share insufficienti -> {e}")

    # soglia raggiunta -> scrutinio
    risultati, plain_votes, stats = commissione.tally(ciphertexts, commissione.shares)
    print(f"Schede: {stats}")
    print(f"STH finale firmato: n={sth_finale['n']}, root={sth_finale['root'][:16]}...")
    print("\nRisultati Sindaco:")
    for sid, v in sorted(risultati["sindaci"].items(), key=lambda x: -x[1]):
        print(f"  {config.SINDACI[sid]:<18} {v}")

    # ---- Verifica individuale ----
    sezione("VERIFICA INDIVIDUALE (campione di 3 elettori)")
    for c in clients[:3]:
        ok = c.verifica_individuale()
        print(f"  {c.credentials}: prova di Merkle + STH -> {'OK' if ok else 'FALLITA'}")

    # ---- Verifica universale ----
    sezione("VERIFICA UNIVERSALE (ricalcolo pubblico aggregati)")
    ric = {"sindaci": {}, "liste": {}, "consiglieri": {}}
    for pv in plain_votes:
        if not pv["valida"]:
            continue
        v = pv["voto"]
        ric["sindaci"][v["sindaco"]] = ric["sindaci"].get(v["sindaco"], 0) + 1
        ric["liste"][v["lista"]] = ric["liste"].get(v["lista"], 0) + 1
        for x in v["consiglieri"]:
            ric["consiglieri"][x] = ric["consiglieri"].get(x, 0) + 1
    coerente = (ric == risultati == voti_attesi)
    print(f"  Aggregati ricalcolati == pubblicati == attesi: {coerente}")

    # ---- Export STH finale per l'anchoring on-chain (Lab 5) ----
    import json
    sth_path = os.path.join(os.path.dirname(__file__), "blockchain", "sth_final.json")
    with open(sth_path, "w") as f:
        json.dump(sth_finale, f, indent=2)
    print(f"\nSTH finale esportato in {sth_path} (input per blockchain/anchor.js).")

    idp.stop(); urna.stop()
    print("Simulazione completata.")


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 8
    main(n)
