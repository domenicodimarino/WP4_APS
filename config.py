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
    30: "Le Frazioni al Centro", 31: "Fratelli d'Italia", 32: "Noi Moderati", 33: "Prima Cava", 34: "Siamo Cavesi", 35: "Forza Italia",
    40: "Uniti per Accarino", 41: "Movimento 5 Stelle", 42: "Avanti", 43: "Partito Democratico", 44: "Cava è Domani",
    50: "Cava Ci Appartiene"
}

# Mappatura gerarchica per il rendering grafico della scheda
COALIZIONI = {
    1: [10, 11],
    2: [20],
    3: [30, 31, 32, 33, 34, 35],
    4: [40, 41, 42, 43, 44],
    5: [50]
}

# ID consiglieri GLOBALMENTE UNICI: nuovo_id = id_lista * 1000 + progressivo.
# Questo elimina le collisioni tra liste diverse (es. il vecchio 344 valeva sia
# "Christian CONSIGLIO" lista 34 sia "Nicola SORRENTINO" lista 32).

CONSIGLIERI = {
    10: {10001: "Laura ANDRETTA", 10002: "Rosa AVOSSA", 10003: "Nunzia BELMONTE", 10004: "Antonella BISOGNO", 10005: "Gennaro CICALESE", 10006: "Raffaele CORRADO", 10007: "Roberto DELLA MONICA", 10008: "Adele FALIVENE", 10009: "Francesco GARGANO", 10010: "Antonio GEMINI", 10011: "Mirko LAMBERTI", 10012: "Carmen LAMBIASE", 10013: "Manuela PALLADINO", 10014: "Massimo PALLADINO", 10015: "Giovanni SANTORIELLO", 10016: "Salvatore SANTORIELLO", 10017: "Antonio ZARRA"},
    11: {11001: "Luca ALFIERI", 11002: "Annapia AMABILE", 11003: "Vincenzo AVAGLIANO", 11004: "Salvatore CARDAMONE", 11005: "Federica COPPOLA", 11006: "Immacolata CUCCURULLO", 11007: "Giovanni DESIDERIO VIGORITO", 11008: "Costantino DI FRAIA", 11009: "Alessandra FRANCHINI", 11010: "Danilo FUSCO", 11011: "Anna LAMBERTI", 11012: "Danilo LEO", 11013: "Elena MONETTI", 11014: "Domenico PISAPIA", 11015: "Brigida PIZZO", 11016: "Teresa RISPOLI", 11017: "Vincenzo RONCA", 11018: "Nancy Bek SALOMONE", 11019: "Pasquale SALSANO", 11020: "Miriana SENATORE", 11021: "Antonio SIANI", 11022: "Iolanda SPATUZZI", 11023: "Rocco URGESI", 11024: "Luca VITALE"},
    20: {20001: "Giovanna ALVIANI", 20002: "Laura ARMENANTE", 20003: "Filomena AVAGLIANO detta Mena", 20004: "Emiliano BOZZETTO", 20005: "Serena CANORA", 20006: "Pasquale D'ANTONIO", 20007: "Francesco DE SIMONE", 20008: "Basilio DESIDERIO detto Pupainiello", 20009: "Annachiara DI DONATO", 20010: "Gabriele DI MARINO", 20011: "Antonio Daniele D'URSI detto Totò", 20012: "Claudia FANCIULLO", 20013: "Francesca FINCH", 20014: "Leonardo LEONE", 20015: "Angela PAGANO", 20016: "Salvatore PALAZZO", 20017: "Andrea PALESTRA", 20018: "Aniello RUGGIERO", 20019: "Ciro SENATORE", 20020: "Emanuele SENATORE detto Nese", 20021: "Mara Francesca SENATORE detta Mara", 20022: "Alessandra SIANI", 20023: "Marco TAMBURELLO", 20024: "Marco VITALE"},
    30: {30001: "Vincenzo ACCARINO", 30002: "Antonio APICELLA detto Tony Bianco Blu", 30003: "Cinzia BISOGNO", 30004: "Alfonso CAVALIERE", 30005: "Luigi COPPOLA", 30006: "Maria DI MARTINO", 30007: "Mafalda FERRARA", 30008: "Raffaela FERRARA", 30009: "Cristiano LODATO", 30010: "Marco LOFFREDO", 30011: "Anna MAGLIANO", 30012: "Francesca MASSA", 30013: "Gianfranco MAZZARELLA", 30014: "Domenico MONETTA", 30015: "Antonella MOSCA", 30016: "Adriano PELLEGRINO", 30017: "Michele PISANI", 30018: "Carlotta PISCOPO", 30019: "Ornella SGAMBATI", 30020: "Gelsomina SIANI", 30021: "Walter SOCCI", 30022: "Stefania VIGILANTE", 30023: "Gennaro VITALE", 30024: "Gennaro ZITO"},
    31: {31001: "Cristiano ALIBERTI", 31002: "Lucio BISOGNO", 31003: "Liunet CAMPOS CASTILLO detta Luna", 31004: "Giada CAVALIERE", 31005: "Renato CIRIELLI DE MOLA detto Ciriello", 31006: "Giuseppe D'AMICO", 31007: "Gianpio DE ROSA", 31008: "Aldo DE SIMONE detto Canora", 31009: "Sara FARIELLO", 31010: "Clelia FERRARA", 31011: "Luca MANZO", 31012: "Sara MATONTI detta Sara", 31013: "Matilde MILITE", 31014: "Marco PALLADINO", 31015: "Sara PECORARO", 31016: "Giuseppe RAINONE", 31017: "Valerio RONCA", 31018: "Antonietta SALSANO", 31019: "Gaetano SANTORIELLO", 31020: "Gianluca SENATORE", 31021: "Carmine SIANI", 31022: "Maria SILVESTRI detta Maria", 31023: "Giovanni VAGLIA", 31024: "Rosario VIRNO"},
    32: {32001: "Bruno D'ELIA", 32002: "Gianluca BARRELLA", 32003: "Paola MOSCHILLO", 32004: "Alessandro DI LORENZO", 32005: "Francesco PEPE", 32006: "Umberto FERRIGNO", 32007: "Romina DI GREGORIO", 32008: "Dolores CARRATU'", 32009: "Candida MILIONE", 32010: "Maurizio VIGORITO", 32011: "Germano AVELLA", 32012: "Teresa MATONTI", 32013: "Gerardo BALDI", 32014: "Mario Antonio AVAGLIANO", 32015: "Massimo LAUDATO", 32016: "Ester ADINOLFI", 32017: "Maria DE CARO", 32018: "Michele Arcangelo COLELLA", 32019: "Chiara CASABURI", 32020: "Biagio LAMBIASE detto Biagio", 32021: "Bernardina RUSSO", 32022: "Pasquale SENATORE", 32023: "Alessia MASULLO", 32024: "Nicola SORRENTINO"},
    33: {33001: "Mirko GIORDANI", 33002: "Anna AMORE", 33003: "Biagio ANGRISANI", 33004: "Luca AVAGLIANO", 33005: "Lucia BISOGNO", 33006: "Fernanda D'ELIA", 33007: "Adriana DELLA CORTE", 33008: "Valeria DESIDERIO", 33009: "Angelo DI MARINO", 33010: "Giovanna DI MARINO", 33011: "Patrizia FOGLIO", 33012: "Giuseppe IRNO", 33013: "Anna LAMBIASE", 33014: "Vincenzo MILITO detto Enzo", 33015: "Nicla PANARESE", 33016: "Giuseppe PAOLILLO detto Pino", 33017: "Gilda PISAPIA", 33018: "Antonio PURGANTE", 33019: "Concetta SENATORE detta Conci", 33020: "Cosimo SENATORE", 33021: "Massimo SIANI", 33022: "Antonio SIANI", 33023: "Carlo SILVERIO", 33024: "Ludovica VENTRE"},
    34: {34001: "Antonella ANGRISANI", 34002: "Federico BARONE", 34003: "Mario CARDAMONE", 34004: "Christian CONSIGLIO", 34005: "Monica GIORDANO", 34006: "Francesco IOVINE", 34007: "Donatella LAMBERTI", 34008: "Vincenzo LAMBERTI detto Enzo", 34009: "Giorgia MADDALO", 34010: "Giuseppe MILITE", 34011: "Vincenzo PASSA detto Enzo", 34012: "Gerardo PISAPIA", 34013: "Nicola POLITO", 34014: "Gennaro PORTOFINO", 34015: "Clara RAGOSTA detta Maria", 34016: "Vincenzo RISI", 34017: "Clotilde SALSANO detta Titti", 34018: "Maddalena SANTORIELLO", 34019: "Concetta SENATORE detta Tina", 34020: "Daniela SENATORE", 34021: "Giovanni SENATORE", 34022: "Sabrina SENATORE", 34023: "Benito VENTRE", 34024: "Luisa VIGNES"},
    35: {35001: "Antonio BARBUTI", 35002: "Bernardo MANDARA detto Fernando", 35003: "Salvatore APICELLA", 35004: "Carmela BISOGNO", 35005: "Alessandro CASABURI", 35006: "Anna CUOMO", 35007: "Mariagrazia DE LUCA", 35008: "Luigi DE ROSA", 35009: "Francesco DELLA ROCCA", 35010: "Massimiliano DI MATTEO", 35011: "Anna FERONE", 35012: "Alessia FERRARA detta Ale", 35013: "Valentina FERRARA detta Vale", 35014: "Antonella FINELLI", 35015: "Monica FRANCESE", 35016: "Leandro GUARINO", 35017: "Diana LAMBERTI", 35018: "Patrizia LAMBIASE", 35019: "Manuela LUCIANO", 35020: "Soraya PISAPIA", 35021: "Assunta SORRENTINO", 35022: "Laura TORRE", 35023: "Barbara TURCO", 35024: "Salvatore VITALE"},
    40: {40001: "Antonella ALARI ESPOSITO", 40002: "Annamaria BARONE", 40003: "Enrico BASTOLLA", 40004: "Ivana CARPENTIERI", 40005: "Gerarda CARRATU'", 40006: "Federico DE FILIPPIS", 40007: "Giovanna DELLA PORTA", 40008: "Anna DI DOMENICO", 40009: "Giovanni DI DONATO", 40010: "Stefania FORLANI", 40011: "Giuseppe GALDI", 40012: "Paolo GRAVAGNUOLO", 40013: "Giuseppina IULIANO", 40014: "Angela LODATO", 40015: "Francesco MANZO detto Franco", 40016: "Antonio PALUMBO", 40017: "Luisa RISPOLI", 40018: "Alfonso SENATORE", 40019: "Rossella VECCHIO"},
    41: {41001: "Giuseppe BENEVENTO", 41002: "Elisabetta PAGANO", 41003: "Maurizio DI DOMENICO", 41004: "Valeria MANZO", 41005: "Matteo ARMENANTE", 41006: "Anna CASABURI", 41007: "Manuela ARMENANTE", 41008: "Fabiana BARONE", 41009: "Antonio BIASIO", 41010: "Bice BOVE", 41011: "Livio CUCCURULLO", 41012: "Luigi DE ROSA", 41013: "Dario FERRARA", 41014: "Gianluca CARLEO", 41015: "Antonio IOVINE", 41016: "Vincenzo PALAZZO", 41017: "Gaetano PISAPIA", 41018: "Alessio SALSANO", 41019: "Liliana VOZZELLA"},
    42: {42001: "Antonella GAROFALO", 42002: "Germano BALDI", 42003: "Valentina BUONADONNA", 42004: "Francesca CINQUE", 42005: "Fernando Francesco Amedeo CONSALVO", 42006: "Gianluca DI MARINO", 42007: "Gianluca DI GIACOMO", 42008: "Vincenzo Paolo GIORDANO", 42009: "Antonella IANNACO", 42010: "Mariateresa MADDALO detta Maresa", 42011: "Vincenzo MARINO", 42012: "Francesco MASSA", 42013: "Marta AMENDOLA", 42014: "Antonio ROMANO", 42015: "Felicia VANGONE", 42016: "Giuseppe VITALE", 42017: "Renata ZAPPILE", 42018: "Daniela PICOZZI", 42019: "Emanuele SENATORE"},
    43: {43001: "Francesco BISOGNO", 43002: "Elisabetta BRUNO detta Betty", 43003: "Arianna CIMINIELLO", 43004: "Silvana CODA", 43005: "Palmiro DENTE detto Danilo", 43006: "Vincenzo DI DOMENICO", 43007: "Vincenzo DI GIOVANNI", 43008: "Niccolò FARINA", 43009: "Annalaura FERRARA", 43010: "Carmine FERRARA", 43011: "Gaetano GAMBARDELLA", 43012: "Francesco GIORDANO", 43013: "Wladimiro IANNACE", 43014: "Lorena IULIANO", 43015: "Felice LANDI", 43016: "Paola LANDI", 43017: "Carmine MAGLIANO", 43018: "Ciro MILITE", 43019: "Luca NARBONE", 43020: "Anna PADOVANO SORRENTINO", 43021: "Ilaria PISAPIA", 43022: "Giuseppe ROSSETTI", 43023: "Rosaria SANTORIELLO", 43024: "Marika SPIEZIA"},
    44: {44001: "Luciano D'AMATO", 44002: "Barbara MAURO", 44003: "Wagner Carlo AVAGLIANO", 44004: "Francesco CAFARO", 44005: "Stefania CELENTANO", 44006: "Arlyn CRUZ", 44007: "Silvio DE ANGELIS", 44008: "Gerardina DE ROSA", 44009: "Eliana DOTI", 44010: "Loredana FERRARA", 44011: "Lucia GIGANTINO", 44012: "Lucia LABRACA", 44013: "Ciro LUCIANO", 44014: "Raffaele PALMIERI", 44015: "Angelica PELLEGRINO", 44016: "Fabio SENATORE", 44017: "Biagio SPATUZZI"},
    50: {50001: "Laura ATTANASIO", 50002: "Veneranda BISOGNO", 50003: "Alessandro BORGHINO", 50004: "Rocco CARRANO", 50005: "Fabrizio CASERTA", 50006: "Gianfranco D'ALESSIO", 50007: "Margherita DE ANGELIS", 50008: "Anita DE BLASI", 50009: "Vittorio DE ROSA", 50010: "Pio DI DOMENICO", 50011: "Paola DI FLORIO", 50012: "Nicola di SANTO", 50013: "Rocco DONVITO", 50014: "Anna FATO", 50015: "Rosanna FORTE", 50016: "Mario LAMBERTI", 50017: "Daniele MOLINO", 50018: "Nicoletta QUADRINO", 50019: "Rosa RICCIARDELLI", 50020: "Massimo SIANI", 50021: "Carmine VITALE"},
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