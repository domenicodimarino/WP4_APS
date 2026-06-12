"""
Configurazione del prototipo: scheda elettorale del Comune di Cava de' Tirreni,
parametri di rete e parametri crittografici/protocollari.
"""
from __future__ import annotations

# --- Rete (localhost). TLS DICHIARATO FUORI PERIMETRO: socket TCP in chiaro;
#     la sicurezza e' demandata interamente alle primitive applicative
#     (firme RSA-PSS, RSA-OAEP, HMAC). Vedi README, sez. "Assunzioni". ---
IDP_HOST, IDP_PORT = "127.0.0.1", 9101
URNA_HOST, URNA_PORT = "127.0.0.1", 9102

# --- Parametri protocollo ---
MAX_PAYLOAD_BYTES = 2048          # pre-validazione dimensionale anti-DoS (Fase 3)
MAX_PREFERENZE_CONSIGLIERI = 2    # vincolo semantico verificato in Fase 4

# --- Shamir (t, n) per SK_Comm (dichiarato simulato) ---
SHAMIR_T = 3
SHAMIR_N = 5

# --- Random delay client-side (privacy temporale). Ridotto per la demo;
#     in produzione: da pochi secondi a qualche minuto. ---
RANDOM_DELAY_MIN_S = 0.0
RANDOM_DELAY_MAX_S = 0.05

# --- Scheda elettorale: candidati Sindaco, liste collegate, consiglieri ---
SINDACI = {
    1: "Mario Rossi",
    2: "Lucia Bianchi",
    3: "Giuseppe Verdi",
}

LISTE = {
    10: "Cava Civica",
    11: "Insieme per Cava",
    12: "Cava nel Cuore",
}

CONSIGLIERI = {
    101: "Esposito A.", 102: "Romano B.", 103: "Ferrara C.",
    104: "Gallo D.",    105: "De Luca E.", 106: "Santoro F.",
    107: "Greco G.",    108: "Conte H.",   109: "Marino I.",
}


def scheda_valida_semantica(v: dict) -> bool:
    """Validazione semantica di un voto V decifrato (usata in Fase 4)."""
    if v.get("sindaco") not in SINDACI:
        return False
    if v.get("lista") not in LISTE:
        return False
    cons = v.get("consiglieri", [])
    if not isinstance(cons, list):
        return False
    if len(cons) > MAX_PREFERENZE_CONSIGLIERI:
        return False
    if len(set(cons)) != len(cons):           # nessuna preferenza ripetuta
        return False
    if any(c not in CONSIGLIERI for c in cons):
        return False
    return True
