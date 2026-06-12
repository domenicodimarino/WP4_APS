# WP4 — Implementazione e Prestazioni

Prototipo del protocollo di voto elettronico progettato nel WP2 (elezione
comunale di Cava de' Tirreni), realizzato come **applicazione stand-alone in
ambiente simulato**, come richiesto dalla traccia. Gli attori comunicano via
socket TCP locali a **stato isolato** (nessuna memoria condivisa), così da
rendere concreta la separazione dei ruoli e l'assunzione di non-collusione
IdP–Urna.

## Assunzioni dichiarate

1. **Shamir (t, n) — simulato.** Lo schema di Shamir's Secret Sharing è
   matematicamente reale (polinomio di grado `t-1` su `GF(2^521-1)`,
   interpolazione di Lagrange in `x=0`; `t-1` share non rivelano nulla). È
   dichiarato *simulato* perché la cerimonia di distribuzione/ricomposizione
   avviene in un unico processo e non si implementa una Distributed Key
   Generation: `SK_Comm` è generata centralmente e posta sotto soglia cifrandola
   con AES-256 sotto una chiave derivata dal segreto Shamir. Vedi `shamir.py` e
   `parties/commissione.py`.

2. **TLS 1.3 — fuori perimetro.** Il canale di trasporto è in chiaro. Le
   proprietà applicative dimostrate (autenticità del Token via RSA-PSS,
   segretezza via schema ibrido RSA-OAEP+AES, integrità via HMAC) **non
   dipendono dal canale**. L'unica garanzia demandata a TLS nel WP2
   (riservatezza delle credenziali in Fase 1, anti-eavesdropping di rete) è
   assunta fornita in deployment. Vedi `transport.py`.

## Mappatura al protocollo (WP2)

| Componente | File | Fase |
|---|---|---|
| Primitive (RSA-OAEP/PSS, AES-256-CBC, HMAC, SHA-256) | `crypto_primitives.py` | — |
| Shamir (t, n) | `shamir.py` | 4 |
| Bulletin Board (Merkle + STH) | `merkle.py` | 3–4 |
| Identity Provider | `parties/idp.py` | 1 |
| Urna + Blacklist atomica + BB | `parties/urna.py` | 3 |
| Commissione di Scrutinio | `parties/commissione.py` | 4 |
| Client Elettore + verifica individuale | `parties/client.py` | 1–2–3 |
| Orchestratore + casi limite | `run_election.py` | tutte |
| GUI desktop (intera elezione + scrutinio) | `gui.py` | tutte |
| Anchoring on-chain STH (Lab 5) | `blockchain/` | 4 |

Le primitive replicano fedelmente i laboratori: RSA-OAEP/PSS (Lab 2,
`1_authenticated_encryption_rsa.py`), AES-CBC+PKCS#7 (`3_padding_oracle.py`),
Merkle (`0_merkle_tree.py`), blockchain con solc/web3/Ganache (Lab 5).

## Esecuzione

```bash
pip install -r requirements.txt

# Interfaccia grafica: intera elezione + pannello di scrutinio
python -m wp4.gui

# Simulazione end-to-end da terminale (default 8 elettori): fasi 1-4, casi limite, verifiche
python -m wp4.run_election 8

# Prestazioni (microbench primitive + dimensioni messaggi + latenze + interazione)
python -m wp4.benchmark 16 200      # -> wp4/benchmark_report.md
```

La GUI (`gui.py`, Tkinter, nessuna dipendenza esterna) pilota gli stessi attori
del prototipo: avvio sistema, scheda elettorale (Sindaco/Lista/Consiglieri),
voto singolo o batch casuale, Bulletin Board live con verifica di inclusione,
ricevuta + verifica individuale, e tab "Scrutinio" per la Fase 4 (soglia
Shamir, shuffle, Encrypt-then-MAC, risultati aggregati, STH finale, verifica
universale). Non implementa nuove primitive: è solo un front-end didattico.

> **macOS**: se `python -m wp4.gui` dà `ModuleNotFoundError: No module named
> 'tkinter'`, installa il binding Tk con `brew install python-tk` (oppure usa
> il Python ufficiale da python.org, che lo include).

### Anchoring on-chain (opzionale, richiede Ganache)

```bash
cd blockchain
npm install
node compile.js                     # genera ABI + bytecode
GANACHE_URL=http://127.0.0.1:7545 node deploy.js   # deploy su Ganache
node anchor.js                      # ancora sth_final.json e rilegge la root
```
`sth_final.json` è prodotto dalla simulazione Python. La radice di Merkle
ancorata on-chain è immutabile e timestamp-ata: qualsiasi alterazione
retroattiva del BB diverge dalla root pubblicata, rafforzando *Integrità
registro post-chiusura* e *Verificabilità Universale*.

## Proprietà di sicurezza dimostrate

- **Autenticità** — Token RSA-PSS verificato dall'Urna; token falso rifiutato.
- **Unicità** — unicità del rilascio (IdP) + blacklist atomica test-and-set
  (Urna); doppio rilascio e replay rifiutati.
- **Segretezza** — schema ibrido (Urna cieca, non possiede `SK_Comm`) +
  soglia Shamir + shuffle in Fase 4.
- **Integrità** — Encrypt-then-MAC: la verifica HMAC precede l'unpad PKCS#7;
  un ciphertext manomesso è marcato nullo **prima** di toccare il padding
  (neutralizzazione del Padding Oracle).
- **Verificabilità individuale** — ricevuta `R = Sign_Urna(H(C))` + prova di
  inclusione di Merkle verso lo STH firmato.
- **Verificabilità universale** — ricalcolo pubblico degli aggregati da `{V}`;
  ancoraggio on-chain della root.

I casi limite (doppio rilascio, replay, token falso, padding oracle, soglia
insufficiente) sono dimostrati automaticamente da `run_election.py`.
