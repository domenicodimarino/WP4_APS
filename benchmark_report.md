# WP4 — Report Prestazioni

Parametri: N_elettori=16, ripetizioni microbench=200, Shamir (t=3, n=5), RSA-2048.

### Costo operazioni crittografiche

| Operazione | Media (ms) | Dev. std (ms) |
|---|---:|---:|
| RSA-2048 keygen (Gen) | 65.8880 | 40.7186 |
| RSA-OAEP encrypt (E_pk) | 0.0340 | 0.0047 |
| RSA-OAEP decrypt (D_sk) | 1.0137 | 0.2190 |
| RSA-PSS sign (Sign) | 1.0249 | 0.2249 |
| RSA-PSS verify (Verify) | 0.0365 | 0.0038 |
| AES-256-CBC encrypt | 0.0062 | 0.0032 |
| AES-256-CBC decrypt | 0.0052 | 0.0018 |
| HMAC-SHA256 | 0.0024 | 0.0014 |
| SHA-256 | 0.0012 | 0.0005 |
| Shamir split (t=3,n=5) | 0.0046 | 0.0014 |
| Shamir reconstruct | 0.0050 | 0.0013 |

### Strutture autenticate (Bulletin Board)

| Operazione | Media (ms) | Dev. std (ms) |
|---|---:|---:|
| Merkle build (16 foglie) | 0.0072 | 0.0019 |
| Merkle proof gen | 0.0004 | 0.0001 |
| Merkle proof verify | 0.0018 | 0.0009 |

### Tempi di interazione e latenza di verifica

| Operazione | Media (ms) | Dev. std (ms) |
|---|---:|---:|
| Fase 1 — RTT richiesta Token | 1.5260 | 1.4200 |
| Fase 2 — cifratura client (locale) | 0.0660 | 0.0239 |
| Fase 3 — RTT submit + ricevuta | 1.3083 | 0.3657 |
| Verifica individuale (proof+STH) | 1.3959 | 0.0648 |

### Dimensione dei messaggi scambiati

| Messaggio | Dimensione (byte) |
|---|---:|
| Token (T_ID + firma), risposta IdP | 427 |
| Payload voto C = (C_key,C_sym,T,IV) | 500 |
| Richiesta submit completa (C+Token) | 992 |
| Ricevuta R (firma RSA-PSS) | 256 |
| STH (n,ts,root,firma) | 626 |
| Prova di inclusione Merkle | 316 |
