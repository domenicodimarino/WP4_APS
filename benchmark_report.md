# WP4 — Report Prestazioni

Parametri: N_elettori=16, ripetizioni microbench=200, Shamir (t=3, n=5), RSA-2048.

### Costo operazioni crittografiche

| Operazione | Media (ms) | Dev. std (ms) |
|---|---:|---:|
| RSA-2048 keygen (Gen) | 79.0534 | 43.1017 |
| RSA-OAEP encrypt (E_pk) | 0.0300 | 0.0088 |
| RSA-OAEP decrypt (D_sk) | 0.7095 | 0.1281 |
| RSA-PSS sign (Sign) | 0.6857 | 0.0721 |
| RSA-PSS verify (Verify) | 0.0336 | 0.0068 |
| AES-256-CBC encrypt | 0.0085 | 0.0089 |
| AES-256-CBC decrypt | 0.0076 | 0.0026 |
| HMAC-SHA256 | 0.0034 | 0.0024 |
| SHA-256 | 0.0019 | 0.0006 |
| Shamir split (t=3,n=5) | 0.0071 | 0.0048 |
| Shamir reconstruct | 0.0081 | 0.0045 |

### Strutture autenticate (Bulletin Board)

| Operazione | Media (ms) | Dev. std (ms) |
|---|---:|---:|
| Merkle build (16 foglie) | 0.0194 | 0.0056 |
| Merkle proof gen | 0.0008 | 0.0002 |
| Merkle proof verify | 0.0051 | 0.0019 |

### Tempi di interazione e latenza di verifica

| Operazione | Media (ms) | Dev. std (ms) |
|---|---:|---:|
| Fase 1 — RTT richiesta Token | 1.1506 | 0.6198 |
| Fase 2 — cifratura client (locale) | 0.1008 | 0.0236 |
| Fase 3 — RTT submit + ricevuta | 1.0843 | 0.1096 |
| Verifica individuale (proof+STH) | 1.3960 | 0.1271 |

### Dimensione dei messaggi scambiati

| Messaggio | Dimensione (byte) |
|---|---:|
| Token (T_ID + firma), risposta IdP | 427 |
| Payload voto C = (C_key,C_sym,T,IV) | 500 |
| Richiesta submit completa (C+Token) | 992 |
| Ricevuta R (firma RSA-PSS) | 256 |
| STH (n,ts,root,firma) | 626 |
| Prova di inclusione Merkle | 316 |
