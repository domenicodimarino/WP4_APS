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
    1: "Raffaele Giordano",
    2: "Luigi Petrone",
    3: "Eugenio Canora",
    4: "Giancarlo Accarino",
    5: "Armando Lamberti"    
}

LISTE = {
    10: "Fratelli d'Italia",
    11: "La Fratellanza",
    12: "Cava Sia"
}

CONSIGLIERI = {
    10: {101: "Candidato A", 102: "Candidato B"},
    11: {201: "Candidato C (Lista 11)", 202: "Candidato D (Lista 11)"},
    12: {301: "Candidato E (Lista 12)", 302: "Candidato F (Lista 12)"},
}


def scheda_valida_semantica(v: dict) -> bool:
    """Validazione semantica di un voto V decifrato (usata in Fase 4)."""
    if v.get("sindaco") not in SINDACI:
        return False
    
    chosen_lista = v.get("lista")
    if chosen_lista not in LISTE:
        return False
        
    cons = v.get("consiglieri", [])
    if not isinstance(cons, list):
        return False
    if len(cons) > MAX_PREFERENZE_CONSIGLIERI:
        return False
    if len(set(cons)) != len(cons):           # nessuna preferenza ripetuta
        return False
        
    # Preleva i consiglieri validi SOLO per la lista votata
    consiglieri_validi_per_lista = CONSIGLIERI.get(chosen_lista, {})
    if any(c not in consiglieri_validi_per_lista for c in cons):
        return False
        
    return True
