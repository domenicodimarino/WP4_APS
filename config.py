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

# Mappatura gerarchica per il rendering grafico della scheda (Screenshot 2026-06-13 alle 11.10.05.jpg)
COALIZIONI = {
    1: [10, 11],
    2: [20],
    3: [30, 31, 32, 33, 34, 35],
    4: [40, 41, 42, 43, 44],
    5: [50]
}

CONSIGLIERI = {
    10: {101: "Laura ANDRETTA", 102: "Rosa AVOSSA", 103: "Nunzia BELMONTE", 104: "Antonella BISOGNO", 105: "Gennaro CICALESE", 106: "Raffaele CORRADO", 107: "Roberto DELLA MONICA", 108: "Adele FALIVENE", 109: "Francesco GARGANO", 110: "Antonio GEMINI", 111: "Mirko LAMBERTI", 112: "Carmen LAMBIASE", 113: "Manuela PALLADINO", 114: "Massimo PALLADINO", 115: "Giovanni SANTORIELLO", 116: "Salvatore SANTORIELLO", 117: "Antonio ZARRA"},
    11: {111: "Luca ALFIERI", 112: "Annapia AMABILE", 113: "Vincenzo AVAGLIANO", 114: "Salvatore CARDAMONE", 115: "Federica COPPOLA", 116: "Immacolata CUCCURULLO", 117: "Giovanni DESIDERIO VIGORITO", 118: "Costantino DI FRAIA", 119: "Alessandra FRANCHINI", 120: "Danilo FUSCO", 121: "Anna LAMBERTI", 122: "Danilo LEO", 123: "Elena MONETTI", 124: "Domenico PISAPIA", 125: "Brigida PIZZO", 126: "Teresa RISPOLI", 127: "Vincenzo RONCA", 128: "Nancy Bek SALOMONE", 129: "Pasquale SALSANO", 130: "Miriana SENATORE", 131: "Antonio SIANI", 132: "Iolanda SPATUZZI", 133: "Rocco URGESI", 134: "Luca VITALE"},
    20: {201: "Giovanna ALVIANI", 202: "Laura ARMENANTE", 203: "Filomena AVAGLIANO detta Mena", 204: "Emiliano BOZZETTO", 205: "Serena CANORA", 206: "Pasquale D'ANTONIO", 207: "Francesco DE SIMONE", 208: "Basilio DESIDERIO detto Pupainiello", 209: "Annachiara DI DONATO", 210: "Gabriele DI MARINO", 211: "Antonio Daniele D'URSI detto Totò", 212: "Claudia FANCIULLO", 213: "Francesca FINCH", 214: "Leonardo LEONE", 215: "Angela PAGANO", 216: "Salvatore PALAZZO", 217: "Andrea PALESTRA", 218: "Aniello RUGGIERO", 219: "Ciro SENATORE", 220: "Emanuele SENATORE detto Nese", 221: "Mara Francesca SENATORE detta Mara", 222: "Alessandra SIANI", 223: "Marco TAMBURELLO", 224: "Marco VITALE"},
    30: {301: "Vincenzo ACCARINO", 302: "Antonio APICELLA detto Tony Bianco Blu", 303: "Cinzia BISOGNO", 304: "Alfonso CAVALIERE", 305: "Luigi COPPOLA", 306: "Maria DI MARTINO", 307: "Mafalda FERRARA", 308: "Raffaela FERRARA", 309: "Cristiano LODATO", 310: "Marco LOFFREDO", 311: "Anna MAGLIANO", 312: "Francesca MASSA", 313: "Gianfranco MAZZARELLA", 314: "Domenico MONETTA", 315: "Antonella MOSCA", 316: "Adriano PELLEGRINO", 317: "Michele PISANI", 318: "Carlotta PISCOPO", 319: "Ornella SGAMBATI", 320: "Gelsomina SIANI", 321: "Walter SOCCI", 322: "Stefania VIGILANTE", 323: "Gennaro VITALE", 324: "Gennaro ZITO"},
    31: {311: "Cristiano ALIBERTI", 312: "Lucio BISOGNO", 313: "Liunet CAMPOS CASTILLO detta Luna", 314: "Giada CAVALIERE", 315: "Renato CIRIELLI DE MOLA detto Ciriello", 316: "Giuseppe D'AMICO", 317: "Gianpio DE ROSA", 318: "Aldo DE SIMONE detto Canora", 319: "Sara FARIELLO", 320: "Clelia FERRARA", 321: "Luca MANZO", 322: "Sara MATONTI detta Sara", 323: "Matilde MILITE", 324: "Marco PALLADINO", 325: "Sara PECORARO", 326: "Giuseppe RAINONE", 327: "Valerio RONCA", 328: "Antonietta SALSANO", 329: "Gaetano SANTORIELLO", 330: "Gianluca SENATORE", 331: "Carmine SIANI", 332: "Maria SILVESTRI detta Maria", 333: "Giovanni VAGLIA", 334: "Rosario VIRNO"},
    32: {321: "Bruno D'ELIA", 322: "Gianluca BARRELLA", 323: "Paola MOSCHILLO", 324: "Alessandro DI LORENZO", 325: "Francesco PEPE", 326: "Umberto FERRIGNO", 327: "Romina DI GREGORIO", 328: "Dolores CARRATU'", 329: "Candida MILIONE", 330: "Maurizio VIGORITO", 331: "Germano AVELLA", 332: "Teresa MATONTI", 333: "Gerardo BALDI", 334: "Mario Antonio AVAGLIANO", 335: "Massimo LAUDATO", 336: "Ester ADINOLFI", 337: "Maria DE CARO", 338: "Michele Arcangelo COLELLA", 339: "Chiara CASABURI", 340: "Biagio LAMBIASE detto Biagio", 341: "Bernardina RUSSO", 342: "Pasquale SENATORE", 343: "Alessia MASULLO", 344: "Nicola SORRENTINO"},
    33: {331: "Mirko GIORDANI", 332: "Anna AMORE", 333: "Biagio ANGRISANI", 334: "Luca AVAGLIANO", 335: "Lucia BISOGNO", 336: "Fernanda D'ELIA", 337: "Adriana DELLA CORTE", 338: "Valeria DESIDERIO", 339: "Angelo DI MARINO", 340: "Giovanna DI MARINO", 341: "Patrizia FOGLIO", 342: "Giuseppe IRNO", 343: "Anna LAMBIASE", 344: "Vincenzo MILITO detto Enzo", 345: "Nicla PANARESE", 346: "Giuseppe PAOLILLO detto Pino", 347: "Gilda PISAPIA", 348: "Antonio PURGANTE", 349: "Concetta SENATORE detta Conci", 350: "Cosimo SENATORE", 351: "Massimo SIANI", 352: "Antonio SIANI", 353: "Carlo SILVERIO", 354: "Ludovica VENTRE"},
    34: {341: "Antonella ANGRISANI", 342: "Federico BARONE", 343: "Mario CARDAMONE", 344: "Christian CONSIGLIO", 345: "Monica GIORDANO", 346: "Francesco IOVINE", 347: "Donatella LAMBERTI", 348: "Vincenzo LAMBERTI detto Enzo", 349: "Giorgia MADDALO", 350: "Giuseppe MILITE", 351: "Vincenzo PASSA detto Enzo", 352: "Gerardo PISAPIA", 353: "Nicola POLITO", 354: "Gennaro PORTOFINO", 355: "Clara RAGOSTA detta Maria", 356: "Vincenzo RISI", 357: "Clotilde SALSANO detta Titti", 358: "Maddalena SANTORIELLO", 359: "Concetta SENATORE detta Tina", 360: "Daniela SENATORE", 361: "Giovanni SENATORE", 362: "Sabrina SENATORE", 363: "Benito VENTRE", 364: "Luisa VIGNES"},
    35: {351: "Antonio BARBUTI", 352: "Bernardo MANDARA detto Fernando", 353: "Salvatore APICELLA", 354: "Carmela BISOGNO", 355: "Alessandro CASABURI", 356: "Anna CUOMO", 357: "Mariagrazia DE LUCA", 358: "Luigi DE ROSA", 359: "Francesco DELLA ROCCA", 360: "Massimiliano DI MATTEO", 361: "Anna FERONE", 362: "Alessia FERRARA detta Ale", 363: "Valentina FERRARA detta Vale", 364: "Antonella FINELLI", 365: "Monica FRANCESE", 366: "Leandro GUARINO", 367: "Diana LAMBERTI", 368: "Patrizia LAMBIASE", 369: "Manuela LUCIANO", 370: "Soraya PISAPIA", 371: "Assunta SORRENTINO", 372: "Laura TORRE", 373: "Barbara TURCO", 374: "Salvatore VITALE"},
    40: {401: "Antonella ALARI ESPOSITO", 402: "Annamaria BARONE", 403: "Enrico BASTOLLA", 404: "Ivana CARPENTIERI", 405: "Gerarda CARRATU'", 406: "Federico DE FILIPPIS", 407: "Giovanna DELLA PORTA", 408: "Anna DI DOMENICO", 409: "Giovanni DI DONATO", 410: "Stefania FORLANI", 411: "Giuseppe GALDI", 412: "Paolo GRAVAGNUOLO", 413: "Giuseppina IULIANO", 414: "Angela LODATO", 415: "Francesco MANZO detto Franco", 416: "Antonio PALUMBO", 417: "Luisa RISPOLI", 418: "Alfonso SENATORE", 419: "Rossella VECCHIO"},
    41: {411: "Giuseppe BENEVENTO", 412: "Elisabetta PAGANO", 413: "Maurizio DI DOMENICO", 414: "Valeria MANZO", 415: "Matteo ARMENANTE", 416: "Anna CASABURI", 417: "Manuela ARMENANTE", 418: "Fabiana BARONE", 419: "Antonio BIASIO", 420: "Bice BOVE", 421: "Livio CUCCURULLO", 422: "Luigi DE ROSA", 423: "Dario FERRARA", 424: "Gianluca CARLEO", 425: "Antonio IOVINE", 426: "Vincenzo PALAZZO", 427: "Gaetano PISAPIA", 428: "Alessio SALSANO", 429: "Liliana VOZZELLA"},
    42: {421: "Antonella GAROFALO", 422: "Germano BALDI", 423: "Valentina BUONADONNA", 424: "Francesca CINQUE", 425: "Fernando Francesco Amedeo CONSALVO", 426: "Gianluca DI MARINO", 427: "Gianluca DI GIACOMO", 428: "Vincenzo Paolo GIORDANO", 429: "Antonella IANNACO", 430: "Mariateresa MADDALO detta Maresa", 431: "Vincenzo MARINO", 432: "Francesco MASSA", 433: "Marta AMENDOLA", 434: "Antonio ROMANO", 435: "Felicia VANGONE", 436: "Giuseppe VITALE", 437: "Renata ZAPPILE", 438: "Daniela PICOZZI", 439: "Emanuele SENATORE"},
    43: {431: "Francesco BISOGNO", 432: "Elisabetta BRUNO detta Betty", 433: "Arianna CIMINIELLO", 434: "Silvana CODA", 435: "Palmiro DENTE detto Danilo", 436: "Vincenzo DI DOMENICO", 437: "Vincenzo DI GIOVANNI", 438: "Niccolò FARINA", 439: "Annalaura FERRARA", 440: "Carmine FERRARA", 441: "Gaetano GAMBARDELLA", 442: "Francesco GIORDANO", 443: "Wladimiro IANNACE", 444: "Lorena IULIANO", 445: "Felice LANDI", 446: "Paola LANDI", 447: "Carmine MAGLIANO", 448: "Ciro MILITE", 449: "Luca NARBONE", 450: "Anna PADOVANO SORRENTINO", 451: "Ilaria PISAPIA", 452: "Giuseppe ROSSETTI", 453: "Rosaria SANTORIELLO", 454: "Marika SPIEZIA"},
    44: {441: "Luciano D'AMATO", 442: "Barbara MAURO", 443: "Wagner Carlo AVAGLIANO", 444: "Francesco CAFARO", 445: "Stefania CELENTANO", 446: "Arlyn CRUZ", 447: "Silvio DE ANGELIS", 448: "Gerardina DE ROSA", 449: "Eliana DOTI", 450: "Loredana FERRARA", 451: "Lucia GIGANTINO", 452: "Lucia LABRACA", 453: "Ciro LUCIANO", 454: "Raffaele PALMIERI", 455: "Angelica PELLEGRINO", 456: "Fabio SENATORE", 457: "Biagio SPATUZZI"},
    50: {501: "Laura ATTANASIO", 502: "Veneranda BISOGNO", 503: "Alessandro BORGHINO", 504: "Rocco CARRANO", 505: "Fabrizio CASERTA", 506: "Gianfranco D'ALESSIO", 507: "Margherita DE ANGELIS", 508: "Anita DE BLASI", 509: "Vittorio DE ROSA", 510: "Pio DI DOMENICO", 511: "Paola DI FLORIO", 512: "Nicola di SANTO", 513: "Rocco DONVITO", 514: "Anna FATO", 515: "Rosanna FORTE", 516: "Mario LAMBERTI", 517: "Daniele MOLINO", 518: "Nicoletta QUADRINO", 519: "Rosa RICCIARDELLI", 520: "Massimo SIANI", 521: "Carmine VITALE"}
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