# nuovo_wp4/config.py
from __future__ import annotations

MAX_PAYLOAD_BYTES = 2048
MAX_PREFERENZE_CONSIGLIERI = 2
SHAMIR_T = 3
SHAMIR_N = 5
RANDOM_DELAY_MIN_S = 0.0
RANDOM_DELAY_MAX_S = 0.05

IDP_HOST, IDP_PORT = "127.0.0.1", 9101
URNA_HOST, URNA_PORT = "127.0.0.1", 9102

SINDACI = {
    1: "LUIGI PETRONE",
    2: "EUGENIO CANORA",
    3: "RAFFAELE GIORDANO",
    4: "GIANCARLO ACCARINO",
    5: "ARMANDO LAMBERTI"
}

LISTE = {
    10: "Nuovi Orizzonti", 11: "La Fratellanza",
    20: "Cava Sia",
    30: "Le Frazioni al Centro", 31: "Fratelli d'Italia", 32: "Noi Moderati", 33: "Prima Cava",
    40: "Uniti per Accarino", 41: "Movimento 2050", 42: "Avanti", 43: "Partito Democratico", 44: "Cava è Domani",
    50: "Cava Ci Appartiene"
}

# Mappatura gerarchica per il rendering grafico della scheda (Screenshot 2026-06-13 alle 11.10.05.jpg)
COALIZIONI = {
    1: [10, 11],
    2: [20],
    3: [30, 31, 32, 33],
    4: [40, 41, 42, 43, 44],
    5: [50]
}

CONSIGLIERI = {
    10: {101: "Abate A.", 102: "Adinolfi B."},
    11: {111: "Baldi C.", 112: "Bianchi D."},
    20: {201: "Canora E.", 202: "Conte F."},
    30: {301: "De Luca G.", 302: "D'Amico H."},
    31: {311: "Esposito I.", 312: "Evoli J."},
    32: {321: "Ferrara K.", 322: "Fiore L."},
    33: {331: "Gallo M.", 332: "Grimaldi N."},
    40: {401: "Lamberti O.", 402: "Longobardi P."},
    41: {411: "Marino Q.", 412: "Mazzotta R."},
    42: {421: "Napolitano S.", 422: "Novi T."},
    43: {431: "Orlando U.", 432: "Pagano V."},
    44: {441: "Quaranta W.", 442: "Riccio X."},
    50: {501: "Santoro Y.", 502: "Sorrentino Z."}
}

def scheda_valida_semantica(v: dict) -> bool:
    if v.get("sindaco") not in SINDACI:
        return False
    chosen_lista = v.get("lista")
    if chosen_lista not in LISTE:
        return False
    cons = v.get("consiglieri", [])
    if not isinstance(cons, list) or len(cons) > MAX_PREFERENZE_CONSIGLIERI:
        return False
    if len(set(cons)) != len(cons):
        return False
    consiglieri_validi = CONSIGLIERI.get(chosen_lista, {})
    if any(c not in consiglieri_validi for c in cons):
        return False
    return True