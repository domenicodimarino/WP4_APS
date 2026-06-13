"""
Interfaccia grafica desktop interattiva per il WP4 basata su CustomTkinter.
Sfondo responsive basato sulla vera scheda elettorale di Cava de' Tirreni.
Il Bulletin Board e lo Scrutinio sono separati in Tab dedicati per massimizzare
lo spazio visivo e la responsivita' del layout.

Avvio: python -m nuovo_wp4.gui
Richiede: pip install customtkinter pillow
"""
from __future__ import annotations

import os
import sys
import random
import threading
import customtkinter as ctk
from tkinter import messagebox
from PIL import Image, ImageTk

from . import config
from . import crypto_primitives as cp
from . import merkle
from .parties.client import VoterClient
from .parties.commissione import Commissione
from .parties.idp import IdentityProvider
from .parties.urna import Urna
from .transport import b64e, request

# Configurazione dell'ambiente grafico
ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

# Risoluzione dinamica del percorso dell'immagine fac-simile
NOME_IMMAGINE = "cava-de-tirreni_scheda.jpg"
PATH_IMMAGINE = os.path.join(os.path.dirname(__file__), NOME_IMMAGINE)

# Texture a matita copiativa: due X distinte (sindaco piu' larga, lista quadrata)
NOME_X_SINDACO = "X_sindaco.png"
NOME_X_LISTA = "X_lista.png"
PATH_X_SINDACO = os.path.join(os.path.dirname(__file__), NOME_X_SINDACO)
PATH_X_LISTA = os.path.join(os.path.dirname(__file__), NOME_X_LISTA)

def guard(method):
    """Decoratore di sicurezza: intercetta le eccezioni di rete e le mostra nei log/popup."""
    def wrapper(self, *a, **k):
        try:
            return method(self, *a, **k)
        except Exception as exc:
            self._log(f"ERRORE in {method.__name__}: {exc}", "err")
            messagebox.showerror("Errore", f"{method.__name__}: {exc}")
    return wrapper

class ElectionGUI(ctk.CTk):
    N_ELETTORI = 12

    # ===== PARAMETRI GRAFICI TARABILI (frazioni di larghezza/altezza del canvas) =====
    # NB: relx/rely di ogni sindaco/lista indicano il CENTRO della casella.
    # Sia la X sia l'area cliccabile (hotspot) vengono centrate su quel punto.

    # Dimensione delle X
    X_SINDACO_W = 0.25    # X sindaco: larghezza (orizzontale, "larga")
    X_SINDACO_H = 0.050   # X sindaco: altezza
    X_LISTA_SIDE = 0.17   # X lista: lato (quadrata)

    # Dimensione dell'area cliccabile (hotspot) centrata su relx/rely
    HOTSPOT_SINDACO_W = 0.12
    HOTSPOT_SINDACO_H = 0.05
    HOTSPOT_LISTA_W = 0.10
    HOTSPOT_LISTA_H = 0.045

    # Posizione dei due dropdown preferenze rispetto al CENTRO della lista.
    # La Y e' DERIVATA da rely (niente piu' campo drop_y per ogni lista): in questo
    # modo i dropdown seguono sempre il simbolo e non si possono piu' disallineare.
    DROP_DX = 0.085       # spostamento orizzontale verso destra (per non coprire il simbolo)
    DROP_OFFSET_Y = 0.04  # quanto sopra il centro della lista parte il primo dropdown
    DROP_DY = 0.03        # distanza verticale tra il primo e il secondo dropdown

    def __init__(self):
        super().__init__()
        self.update()  # Risolve i blocchi di allocazione grafica su sistemi macOS
        self.title("Sistema di Voto Elettronico — Cava de' Tirreni")
        self.minsize(1100, 780)
        # Apertura massimizzata / a tutto schermo per consistenza grafica.
        # macOS non supporta state("zoomed"): ripiego sulla geometria a piena risoluzione.
        if sys.platform == "darwin":
            self.update_idletasks()
            self.geometry(f"{self.winfo_screenwidth()}x{self.winfo_screenheight()}+0+0")
        else:
            try:
                self.state("zoomed")
            except Exception:
                self.update_idletasks()
                self.geometry(f"{self.winfo_screenwidth()}x{self.winfo_screenheight()}+0+0")

        self.idp = self.urna = self.commissione = None
        self.clients = {}
        self.voti_attesi = {"sindaci": {}, "liste": {}, "consiglieri": {}}
        self.scrutinio_fatto = False

        # Variabili di stato crittografico delle preferenze espresse
        self.selected_sindaco = ctk.IntVar(value=0)
        self.selected_lista = ctk.IntVar(value=0)

        self.selected_consiglieri_vars = {}
        self.ui_dropdowns_mappati = {}      # Mappa: id_lista -> [CTkOptionMenu, CTkOptionMenu]
        self.consigliere_nome_to_id = {}    # Mappa: id_lista -> {nome_visualizzato: id_consigliere}

        self.last_canvas_w = 0
        self.last_canvas_h = 0
        self.debug_mode = False
        self._debug_readout = None

        # Costruzione sequenziale protetta del layout a tre schede
        self._build_topbar()
        self._build_log()     # Console log globale sempre visibile sul fondo
        self._build_pages()   # Stack di frame per la navigazione a schede (Tab layout)
        self.mostra_pagina("vote")
        self._set_running(False)

    def _build_topbar(self):
        bar = ctk.CTkFrame(self, corner_radius=0, fg_color=("gray85", "gray15"))
        bar.pack(fill="x", side="top")

        title = ctk.CTkLabel(bar, text="Elezione Comunale — Cava de' Tirreni (WP4 Prototipo)", font=ctk.CTkFont(size=18, weight="bold"))
        title.pack(side="left", padx=20, pady=12)

        self.btn_start = ctk.CTkButton(bar, text="Avvia Sistema", width=120, command=self.avvia_sistema)
        self.btn_start.pack(side="right", padx=10, pady=12)

        self.btn_reset = ctk.CTkButton(bar, text="Reset", width=100, command=self.reset_sistema, fg_color="transparent", border_width=1, text_color=("black", "white"))
        self.btn_reset.pack(side="right", padx=10, pady=12)

        self.status_var = ctk.StringVar(value="Stato: Inattivo")
        ctk.CTkLabel(bar, textvariable=self.status_var, font=ctk.CTkFont(size=11, slant="italic")).pack(side="right", padx=15)

        self.btn_debug = ctk.CTkButton(bar, text="Debug Coord: OFF", width=150, fg_color="gray40", command=self._toggle_debug)
        self.btn_debug.pack(side="right", padx=10, pady=12)

        # Navigazione a 3 Tab (Risolve il problema dello spazio visivo della scheda)
        nav = ctk.CTkFrame(self, fg_color="transparent")
        nav.pack(fill="x", pady=5, padx=20)

        self.btn_tab_vote = ctk.CTkButton(nav, text="1. SCHEDA ELETTORALE REALISTICA", width=260, command=lambda: self.mostra_pagina("vote"))
        self.btn_tab_vote.pack(side="left", padx=4)

        self.btn_tab_bb = ctk.CTkButton(nav, text="2. BULLETIN BOARD (REGISTRO MERKLE)", width=260, fg_color="gray40", command=lambda: self.mostra_pagina("bb"))
        self.btn_tab_bb.pack(side="left", padx=4)

        self.btn_tab_scrut = ctk.CTkButton(nav, text="3. COMMISSIONE DI SCRUTINIO", width=260, fg_color="gray40", command=lambda: self.mostra_pagina("scrut"))
        self.btn_tab_scrut.pack(side="left", padx=4)

    def _build_log(self):
        frame = ctk.CTkFrame(self, fg_color="transparent")
        frame.pack(fill="x", side="bottom", padx=20, pady=10)
        ctk.CTkLabel(frame, text="Console di Audit — Log di Protocollo Crittografico", font=ctk.CTkFont(size=11, weight="bold")).pack(anchor="w")
        self.log = ctk.CTkTextbox(frame, height=95, font=ctk.CTkFont(family="Courier", size=11))
        self.log.pack(fill="x")

    def _build_pages(self):
        self.container = ctk.CTkFrame(self, fg_color="transparent")
        self.container.pack(fill="both", expand=True, padx=20, pady=5)
        self.container.grid_rowconfigure(0, weight=1)
        self.container.grid_columnconfigure(0, weight=1)

        self.page_vote = ctk.CTkFrame(self.container, fg_color="transparent")
        self.page_bb = ctk.CTkFrame(self.container, fg_color="transparent")
        self.page_scrut = ctk.CTkFrame(self.container, fg_color="transparent")

        for p in (self.page_vote, self.page_bb, self.page_scrut):
            p.grid(row=0, column=0, sticky="nsew")

        self._build_page_vote()
        self._build_page_bb()
        self._build_page_scrut()

    def mostra_pagina(self, which):
        if which == "vote":
            self.page_vote.tkraise()
            self.btn_tab_vote.configure(fg_color=["#3a7ebf", "#1f538d"])
            self.btn_tab_bb.configure(fg_color="gray40")
            self.btn_tab_scrut.configure(fg_color="gray40")
        elif which == "bb":
            self.page_bb.tkraise()
            self.btn_tab_bb.configure(fg_color=["#3a7ebf", "#1f538d"])
            self.btn_tab_vote.configure(fg_color="gray40")
            self.btn_tab_scrut.configure(fg_color="gray40")
        else:
            self.page_scrut.tkraise()
            self.btn_tab_scrut.configure(fg_color=["#3a7ebf", "#1f538d"])
            self.btn_tab_vote.configure(fg_color="gray40")
            self.btn_tab_bb.configure(fg_color="gray40")

    def _build_page_vote(self):
        self.page_vote.grid_columnconfigure(0, weight=1)
        self.page_vote.grid_rowconfigure(0, weight=1)

        main_card = ctk.CTkFrame(self.page_vote)
        main_card.grid(row=0, column=0, sticky="nsew", padx=2, pady=2)

        # Pannello autenticazione utente e invio (Fase 1 e Fase 3)
        top_ctrl = ctk.CTkFrame(main_card, height=50, fg_color=("gray90", "gray20"))
        top_ctrl.pack(fill="x", side="top", padx=8, pady=6)

        ctk.CTkLabel(top_ctrl, text="Elettore Attivo (IdP):", font=ctk.CTkFont(weight="bold")).pack(side="left", padx=12, pady=6)
        self.var_elettore = ctk.StringVar()
        self.om_elettore = ctk.CTkOptionMenu(top_ctrl, variable=self.var_elettore, values=[], width=160)
        self.om_elettore.pack(side="left", padx=5, pady=6)

        self.btn_vota = ctk.CTkButton(top_ctrl, text="DEPOSITARE SCHEDA NELL'URNA", font=ctk.CTkFont(weight="bold"), fg_color="#1d7a46", hover_color="#145a32", width=220, command=self.vota)
        self.btn_vota.pack(side="right", padx=12, pady=6)
        self.btn_batch = ctk.CTkButton(top_ctrl, text="Voto Automatico (Massa Elettorale)", fg_color="gray40", width=220, command=self.vota_batch)
        self.btn_batch.pack(side="right", padx=5, pady=6)

        # Canvas Responsive per visualizzare la foto reale
        self.canvas_frame = ctk.CTkFrame(main_card, fg_color="black")
        self.canvas_frame.pack(fill="both", expand=True, padx=8, pady=6)

        self.canvas = ctk.CTkCanvas(self.canvas_frame, bd=0, highlightthickness=0, bg="gray10")
        self.canvas.pack(fill="both", expand=True)

        if os.path.exists(PATH_IMMAGINE):
            self.original_img = Image.open(PATH_IMMAGINE)
            self._log(f"[OK] Mappatura immagine di sfondo completata: {PATH_IMMAGINE}")
        else:
            self.original_img = Image.new("RGB", (1200, 1600), color=(242, 242, 242))
            self._log(f"[ATTENZIONE] Inserire il file '{NOME_IMMAGINE}' in 'nuovo_wp4/' per sbloccare la grafica reale.", "warn")

        # Caricamento delle due X (sindaco largo, lista quadrata) come immagini sorgente.
        # Le PhotoImage scalate sono ricalcolate nel resize (vedi _layout_canvas_items).
        self._x_sindaco_tk = None
        self._x_lista_tk = None
        self.pencil_lista_img = Image.open(PATH_X_LISTA).convert("RGBA") if os.path.exists(PATH_X_LISTA) else None
        if os.path.exists(PATH_X_SINDACO):
            self.pencil_sindaco_img = Image.open(PATH_X_SINDACO).convert("RGBA")
        else:
            # Fallback: se manca la X dedicata al sindaco, riuso quella della lista (scalata piu' larga)
            self.pencil_sindaco_img = self.pencil_lista_img
        if self.pencil_sindaco_img or self.pencil_lista_img:
            self._log("[OK] Trovata texture X a matita personalizzata.")
        else:
            self._log("[INFO] Nessuna X immagine trovata: uso un segno testuale.", "warn")

        self.bg_image_tk = None
        self.canvas_img_id = self.canvas.create_image(0, 0, anchor="nw")
        self.canvas.bind("<Configure>", self._on_canvas_resize)
        self.canvas.bind("<Motion>", self._on_canvas_motion)

        self.ui_sindaci_marks = {}      # id_sindaco -> item X sul canvas
        self.ui_liste_marks = {}        # id_lista   -> item X sul canvas
        self._hotspot_items = {}        # tag -> item hotspot trasparente
        self._canvas_items_built = False
        self._scheda_running = False
        self.interactive_widgets = []

        self._crea_punti_interattivi_scheda()

    def _build_page_bb(self):
        self.page_bb.grid_columnconfigure(0, weight=1)
        self.page_bb.grid_rowconfigure(0, weight=1)

        bb_frame = ctk.CTkFrame(self.page_bb)
        bb_frame.grid(row=0, column=0, sticky="nsew", padx=2, pady=2)

        ctk.CTkLabel(bb_frame, text="Registro Pubblico Append-Only (Bulletin Board dell'Urna)", font=ctk.CTkFont(size=16, weight="bold")).pack(anchor="w", padx=20, pady=(15, 5))

        self.root_var = ctk.StringVar(value="Radice di Merkle Corrente: —")
        ctk.CTkLabel(bb_frame, textvariable=self.root_var, font=ctk.CTkFont(family="Courier", size=11, weight="bold"), justify="left", wraplength=800, text_color="#1f538d").pack(anchor="w", padx=20, pady=2)

        self.bb_textbox = ctk.CTkTextbox(bb_frame, font=ctk.CTkFont(family="Courier", size=11))
        self.bb_textbox.pack(fill="both", expand=True, padx=20, pady=10)

        ctrl_down = ctk.CTkFrame(bb_frame, fg_color="transparent")
        ctrl_down.pack(fill="x", padx=20, pady=(0, 15))

        self.btn_verifica_bb = ctk.CTkButton(ctrl_down, text="Esegui Audit Matematico (Inclusion Proof + STH RSA)", width=320, command=self.verifica_selezionata)
        self.btn_verifica_bb.pack(side="right", padx=5)

        self.ricevuta_var = ctk.StringVar(value="Nessuna ricevuta generata. Esegui un voto per osservare lo scontrino crittografico firmato.")
        ctk.CTkLabel(ctrl_down, textvariable=self.ricevuta_var, font=ctk.CTkFont(family="Courier", size=10), justify="left", wraplength=700, text_color="green").pack(side="left", padx=5)

    def _crea_punti_interattivi_scheda(self):
        """Definisce le zone cliccabili come ITEM NATIVI del canvas.

        I CTkButton/CTkLabel non possono essere trasparenti su un Canvas con immagine
        (disegnano sempre uno sfondo opaco -> i rettangoli neri). Qui usiamo solo
        coordinate relative + tag_bind: la X e gli hotspot trasparenti vengono creati
        e ridimensionati in modo responsive dentro _layout_canvas_items().
        relx/rely indicano il CENTRO della casella.
        """
        # 1. Coordinate dei 5 candidati SINDACO
        self._coord_sindaci = {
            1: {"relx": 0.257, "rely": 0.085},  # LUIGI PETRONE
            2: {"relx": 0.257, "rely": 0.283},  # EUGENIO CANORA
            3: {"relx": 0.257, "rely": 0.490},  # RAFFAELE GIORDANO
            4: {"relx": 0.747, "rely": 0.085},  # GIANCARLO ACCARINO
            5: {"relx": 0.747, "rely": 0.560},  # ARMANDO LAMBERTI
        }
        for s_id in self._coord_sindaci:
            tag = f"hs_sindaco_{s_id}"
            self.canvas.tag_bind(tag, "<Button-1>", lambda e, sid=s_id: self._on_click_sindaco(sid))
            self.canvas.tag_bind(tag, "<Enter>", lambda e: self.canvas.configure(cursor="hand2"))
            self.canvas.tag_bind(tag, "<Leave>", lambda e: self.canvas.configure(cursor=""))

        # 2. Coordinate delle 15 LISTE reali (la Y dei dropdown e' derivata da rely)
        self._coord_liste = {
            # Coalizione Petrone
            10: {"relx": 0.073, "rely": 0.174},  # Nuovi Orizzonti
            11: {"relx": 0.300, "rely": 0.174},  # La Fratellanza
            # Coalizione Canora
            20: {"relx": 0.073, "rely": 0.383},  # Cava Sia
            # Coalizione Giordano
            30: {"relx": 0.073, "rely": 0.59},   # Le Frazioni al Centro
            31: {"relx": 0.3, "rely": 0.59},     # Fratelli d'Italia
            32: {"relx": 0.3, "rely": 0.728},    # Noi Moderati
            33: {"relx": 0.3, "rely": 0.864},    # Prima Cava
            34: {"relx": 0.073, "rely": 0.864},  # Siamo Cavesi
            35: {"relx": 0.073, "rely": 0.728},  # Forza Italia
            # Coalizione Accarino
            40: {"relx": 0.554, "rely": 0.179},  # Uniti per Accarino
            41: {"relx": 0.783, "rely": 0.179},  # Movimento 5 Stelle
            42: {"relx": 0.554, "rely": 0.319},  # Avanti
            43: {"relx": 0.783, "rely": 0.319},  # Partito Democratico
            44: {"relx": 0.554, "rely": 0.460},  # Cava e' Domani
            # Coalizione Lamberti
            50: {"relx": 0.554, "rely": 0.655},  # Cava Ci Appartiene
        }
        # Scarta le liste non presenti nella configurazione
        self._coord_liste = {k: v for k, v in self._coord_liste.items() if k in config.LISTE}

        for l_id, pos in self._coord_liste.items():
            tag = f"hs_lista_{l_id}"
            self.canvas.tag_bind(tag, "<Button-1>", lambda e, lid=l_id: self._on_click_lista(lid))
            self.canvas.tag_bind(tag, "<Enter>", lambda e: self.canvas.configure(cursor="hand2"))
            self.canvas.tag_bind(tag, "<Leave>", lambda e: self.canvas.configure(cursor=""))

            # I dropdown delle preferenze restano widget opachi (nessun problema di trasparenza).
            # Bloccati a monte per evitare bug visivi (Punto 3).
            self.selected_consiglieri_vars[l_id] = [ctk.StringVar(value="Preferenza 1"), ctk.StringVar(value="Preferenza 2")]
            # A video mostriamo SOLO il nome; teniamo una mappa nome->id per recuperare l'id al voto.
            consiglieri_lista = config.CONSIGLIERI.get(l_id, {})
            self.consigliere_nome_to_id[l_id] = {nome: cid for cid, nome in consiglieri_lista.items()}
            candidati_lista = list(consiglieri_lista.values())

            self.ui_dropdowns_mappati[l_id] = []
            for idx in range(2):
                om = ctk.CTkOptionMenu(
                    self.canvas, variable=self.selected_consiglieri_vars[l_id][idx],
                    values=["Nessuna Preferenza"] + candidati_lista, width=140, font=ctk.CTkFont(size=9),
                    state="disabled"  # <-- OSCURATI AL BOOT
                )
                om.place(relx=pos["relx"] + self.DROP_DX, rely=pos["rely"] - self.DROP_OFFSET_Y + (idx * self.DROP_DY), anchor="center")
                self.interactive_widgets.append(om)
                self.ui_dropdowns_mappati[l_id].append(om)

    def _on_canvas_resize(self, event):
        w, h = event.width, event.height
        if w == self.last_canvas_w and h == self.last_canvas_h:
            return
        self.last_canvas_w, self.last_canvas_h = w, h

        resized_img = self.original_img.resize((w, h), Image.Resampling.LANCZOS)
        self.bg_image_tk = ImageTk.PhotoImage(resized_img)
        self.canvas.itemconfig(self.canvas_img_id, image=self.bg_image_tk)

        self._layout_canvas_items(w, h)

    def _layout_canvas_items(self, w, h):
        """(Ri)dimensiona X e hotspot in modo responsive.

        MODELLO CENTER-BASED: relx/rely di ogni elemento e' il CENTRO della casella.
        Sia la X sia l'hotspot vengono disegnati con anchor="center" su quel punto,
        quindi il centro della X coincide sempre col centro dell'area cliccabile.
        Gli hotspot sono immagini PNG trasparenti: invisibili ma cliccabili su tutta
        l'area (un rettangolo con fill="" sarebbe cliccabile solo sul bordo).
        """
        # --- X del SINDACO: larga in orizzontale (larghezza e altezza indipendenti) ---
        if self.pencil_sindaco_img:
            ws = max(20, int(w * self.X_SINDACO_W))
            hs = max(14, int(h * self.X_SINDACO_H))
            self._x_sindaco_tk = ImageTk.PhotoImage(self.pencil_sindaco_img.resize((ws, hs), Image.Resampling.LANCZOS))
        # --- X della LISTA: quadrata ---
        if self.pencil_lista_img:
            ql = max(14, int(h * self.X_LISTA_SIDE))
            self._x_lista_tk = ImageTk.PhotoImage(self.pencil_lista_img.resize((ql, ql), Image.Resampling.LANCZOS))

        # --- Hotspot trasparenti, condivisi da tutti gli item della stessa categoria ---
        hs_sw, hs_sh = max(40, int(w * self.HOTSPOT_SINDACO_W)), max(20, int(h * self.HOTSPOT_SINDACO_H))
        hs_lw, hs_lh = max(30, int(w * self.HOTSPOT_LISTA_W)), max(18, int(h * self.HOTSPOT_LISTA_H))
        self._hs_sindaco_tk = ImageTk.PhotoImage(Image.new("RGBA", (hs_sw, hs_sh), (0, 0, 0, 0)))
        self._hs_lista_tk = ImageTk.PhotoImage(Image.new("RGBA", (hs_lw, hs_lh), (0, 0, 0, 0)))

        font_x = ("Helvetica", max(18, int(h * 0.04)), "bold")

        # --- SINDACI (X e hotspot centrati su relx/rely) ---
        for s_id, pos in self._coord_sindaci.items():
            cx, cy = pos["relx"] * w, pos["rely"] * h
            tag = f"hs_sindaco_{s_id}"
            if not self._canvas_items_built:
                if self._x_sindaco_tk:
                    xi = self.canvas.create_image(cx, cy, anchor="center", image=self._x_sindaco_tk, state="hidden")
                else:
                    xi = self.canvas.create_text(cx, cy, anchor="center", text="X", fill="#10131a", font=font_x, state="hidden")
                self.ui_sindaci_marks[s_id] = xi
                self._hotspot_items[tag] = self.canvas.create_image(cx, cy, anchor="center", image=self._hs_sindaco_tk, tags=(tag,))
            else:
                self.canvas.coords(self.ui_sindaci_marks[s_id], cx, cy)
                if self._x_sindaco_tk:
                    self.canvas.itemconfig(self.ui_sindaci_marks[s_id], image=self._x_sindaco_tk)
                else:
                    self.canvas.itemconfig(self.ui_sindaci_marks[s_id], font=font_x)
                self.canvas.coords(self._hotspot_items[tag], cx, cy)
                self.canvas.itemconfig(self._hotspot_items[tag], image=self._hs_sindaco_tk)

        # --- LISTE (X e hotspot centrati su relx/rely) ---
        for l_id, pos in self._coord_liste.items():
            cx, cy = pos["relx"] * w, pos["rely"] * h
            tag = f"hs_lista_{l_id}"
            if not self._canvas_items_built:
                if self._x_lista_tk:
                    xi = self.canvas.create_image(cx, cy, anchor="center", image=self._x_lista_tk, state="hidden")
                else:
                    xi = self.canvas.create_text(cx, cy, anchor="center", text="X", fill="#10131a", font=font_x, state="hidden")
                self.ui_liste_marks[l_id] = xi
                self._hotspot_items[tag] = self.canvas.create_image(cx, cy, anchor="center", image=self._hs_lista_tk, tags=(tag,))
            else:
                self.canvas.coords(self.ui_liste_marks[l_id], cx, cy)
                if self._x_lista_tk:
                    self.canvas.itemconfig(self.ui_liste_marks[l_id], image=self._x_lista_tk)
                else:
                    self.canvas.itemconfig(self.ui_liste_marks[l_id], font=font_x)
                self.canvas.coords(self._hotspot_items[tag], cx, cy)
                self.canvas.itemconfig(self._hotspot_items[tag], image=self._hs_lista_tk)

        # Gli hotspot devono stare sopra sfondo e X (sono trasparenti: ricevono comunque i click)
        for item in self._hotspot_items.values():
            self.canvas.tag_raise(item)

        self._canvas_items_built = True

        if self.debug_mode:
            self._draw_debug(w, h)

    # ------------------------------------------------------------------ DEBUG COORDINATE
    def _toggle_debug(self):
        self.debug_mode = not self.debug_mode
        self.btn_debug.configure(text=f"Debug Coord: {'ON' if self.debug_mode else 'OFF'}")
        if self.debug_mode:
            self._draw_debug(self.last_canvas_w, self.last_canvas_h)
        else:
            self.canvas.delete("debug")
            self._debug_readout = None

    def _on_canvas_motion(self, event):
        """Mostra in tempo reale le coordinate relative sotto il cursore (solo in debug)."""
        if not self.debug_mode or self._debug_readout is None:
            return
        w, h = self.last_canvas_w, self.last_canvas_h
        if w <= 1 or h <= 1:
            return
        rx, ry = event.x / w, event.y / h
        self.canvas.itemconfigure(self._debug_readout, text=f"cursore →  relx={rx:.3f}   rely={ry:.3f}")
        self.canvas.coords(self._debug_readout, min(event.x + 15, w - 220), event.y + 12)
        self.canvas.tag_raise(self._debug_readout)

    def _draw_debug(self, w, h):
        """Disegna griglia, riquadri (centrati su relx/rely) con crosshair sul centro
        e i marcatori dei dropdown, più un readout che segue il mouse. Tutto taggato
        'debug' per essere rimosso con una sola delete."""
        self.canvas.delete("debug")
        if w <= 1 or h <= 1:
            return

        # Griglia ogni 0.05 (linee marcate ogni 0.10 con etichetta)
        for i in range(0, 21):
            r = i / 20
            col = "#5566cc" if i % 2 == 0 else "#33408a"
            self.canvas.create_line(r * w, 0, r * w, h, fill=col, dash=(1, 5), tags="debug")
            self.canvas.create_line(0, r * h, w, r * h, fill=col, dash=(1, 5), tags="debug")
            if i % 2 == 0:
                self.canvas.create_text(r * w + 2, 2, anchor="nw", text=f"{r:.2f}", fill="#8899ff", font=("Helvetica", 8), tags="debug")
                self.canvas.create_text(2, r * h + 2, anchor="nw", text=f"{r:.2f}", fill="#8899ff", font=("Helvetica", 8), tags="debug")

        hs_sw, hs_sh = max(40, int(w * self.HOTSPOT_SINDACO_W)), max(20, int(h * self.HOTSPOT_SINDACO_H))
        hs_lw, hs_lh = max(30, int(w * self.HOTSPOT_LISTA_W)), max(18, int(h * self.HOTSPOT_LISTA_H))

        def _crosshair(cx, cy, col):
            self.canvas.create_line(cx - 9, cy, cx + 9, cy, fill=col, width=2, tags="debug")
            self.canvas.create_line(cx, cy - 9, cx, cy + 9, fill=col, width=2, tags="debug")

        # Hotspot SINDACI (rosso) — riquadro centrato su relx/rely
        for s_id, pos in self._coord_sindaci.items():
            cx, cy = pos["relx"] * w, pos["rely"] * h
            self.canvas.create_rectangle(cx - hs_sw / 2, cy - hs_sh / 2, cx + hs_sw / 2, cy + hs_sh / 2,
                                         outline="#ff3b30", width=2, tags="debug")
            _crosshair(cx, cy, "#ff3b30")
            self.canvas.create_text(cx, cy - hs_sh / 2 - 4, anchor="s", text=f"S{s_id}  x={pos['relx']:.3f} y={pos['rely']:.3f}",
                                    fill="#ff3b30", font=("Helvetica", 10, "bold"), tags="debug")

        # Hotspot LISTE (verde) + dropdown centrati (arancio)
        for l_id, pos in self._coord_liste.items():
            cx, cy = pos["relx"] * w, pos["rely"] * h
            self.canvas.create_rectangle(cx - hs_lw / 2, cy - hs_lh / 2, cx + hs_lw / 2, cy + hs_lh / 2,
                                         outline="#34c759", width=2, tags="debug")
            _crosshair(cx, cy, "#34c759")
            self.canvas.create_text(cx, cy - hs_lh / 2 - 4, anchor="s", text=f"L{l_id}  x={pos['relx']:.3f} y={pos['rely']:.3f}",
                                    fill="#1f9e3f", font=("Helvetica", 9, "bold"), tags="debug")
            for idx in range(2):
                dx = (pos["relx"] + self.DROP_DX) * w
                dy = (pos["rely"] - self.DROP_OFFSET_Y + idx * self.DROP_DY) * h
                _crosshair(dx, dy, "#ff9500")
                if idx == 0:
                    self.canvas.create_text(dx, dy - 12, anchor="s", text="pref. 1 / 2",
                                            fill="#ff9500", font=("Helvetica", 9, "bold"), tags="debug")

        # Readout live che segue il mouse
        self._debug_readout = self.canvas.create_text(10, 10, anchor="nw", text="cursore →  muovi il mouse sulla scheda",
                                                      fill="#ffcc00", font=("Helvetica", 13, "bold"), tags="debug")

    def _on_click_sindaco(self, sid: int):
        if not self._scheda_running:
            return
        self._select_sindaco(sid)

    def _select_sindaco(self, sid: int):
        self.selected_sindaco.set(sid)
        for k, item in self.ui_sindaci_marks.items():
            self.canvas.itemconfigure(item, state="normal" if k == sid else "hidden")
        self._log(f"[GUI] Selezionato Candidato Sindaco: {config.SINDACI[sid]}")

    def _on_click_lista(self, lid: int):
        if not self._scheda_running:
            return
        self._select_lista(lid)

    def _select_lista(self, lid: int):
        """Attivazione condizionale: abilita i dropdown SOLO della lista spuntata (Punto 3)."""
        self.selected_lista.set(lid)
        for k, item in self.ui_liste_marks.items():
            self.canvas.itemconfigure(item, state="normal" if k == lid else "hidden")

        # Gestione dell'oscuramento dinamico delle preferenze nominali
        for id_lista, lista_dropdowns in self.ui_dropdowns_mappati.items():
            if id_lista == lid:
                for om in lista_dropdowns:
                    om.configure(state="normal")  # Sblocca
            else:
                for om in lista_dropdowns:
                    om.configure(state="disabled")  # Disattiva e spegne
                    self.selected_consiglieri_vars[id_lista][0].set("Preferenza 1")
                    self.selected_consiglieri_vars[id_lista][1].set("Preferenza 2")

        self._log(f"[GUI] Selezionata Lista: {config.LISTE[lid]}. Preferenze nominali sbloccate.")

    def _build_page_scrut(self):
        """TAB 3: Pannello della Commissione Elettorale per lo spoglio offline dei risultati."""
        top = ctk.CTkFrame(self.page_scrut)
        top.pack(fill="x")

        ctk.CTkLabel(top, text="Fase 4 — Scrutinio Pubblico", font=ctk.CTkFont(size=18, weight="bold")).pack(anchor="w", padx=20, pady=(20, 5))

        self.btn_scrutina = ctk.CTkButton(top, text="Chiudi Urne ed Esegui Scrutinio", font=ctk.CTkFont(weight="bold"), command=self.scrutina)
        self.btn_scrutina.pack(anchor="w", padx=20, pady=10)

        self.stats_var = ctk.StringVar(value="")
        ctk.CTkLabel(top, textvariable=self.stats_var).pack(anchor="w", padx=20)

        self.sth_var = ctk.StringVar(value="")
        ctk.CTkLabel(top, textvariable=self.sth_var, font=ctk.CTkFont(family="Courier", size=11), text_color="gray").pack(anchor="w", padx=20)

        self.universale_var = ctk.StringVar(value="")
        self.universale_lbl = ctk.CTkLabel(top, textvariable=self.universale_var, font=ctk.CTkFont(size=14, weight="bold"))
        self.universale_lbl.pack(anchor="w", padx=20, pady=(5, 10))

        res = ctk.CTkFrame(self.page_scrut, fg_color="transparent")
        res.pack(fill="both", expand=True, pady=(5, 0))
        res.grid_columnconfigure((0, 1, 2), weight=1)
        res.grid_rowconfigure(0, weight=1)

        self.tb_sindaci = self._result_box(res, "Sindaco", 0)
        self.tb_liste = self._result_box(res, "Lista", 1)
        self.tb_cons = self._result_box(res, "Consiglieri", 2)

    def _result_box(self, parent, titolo, col):
        f = ctk.CTkFrame(parent)
        f.grid(row=0, column=col, sticky="nsew", padx=5)
        ctk.CTkLabel(f, text=titolo, font=ctk.CTkFont(size=16, weight="bold")).pack(anchor="w", padx=10, pady=(10, 5))
        tb = ctk.CTkTextbox(f, font=ctk.CTkFont(family="Courier", size=12))
        tb.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        return tb

    def _set_running(self, running: bool):
        self._scheda_running = running
        state = "normal" if running else "disabled"
        self.btn_vota.configure(state=state)
        self.btn_batch.configure(state=state)
        self.om_elettore.configure(state=state)

        for w in self.interactive_widgets:
            try:
                w.configure(state=state)
            except Exception:
                pass

        self.btn_start.configure(state="disabled" if running else "normal")
        if not running:
            self.canvas.configure(cursor="")

    @guard
    def avvia_sistema(self):
        n = self.N_ELETTORI
        anagrafe = {f"elettore_{i}" for i in range(n)}
        self.idp = IdentityProvider(anagrafe)
        self.urna = Urna(self.idp.sign_pk)
        self.commissione = Commissione()
        self.idp.start()
        self.urna.start()
        self.clients = {}
        self.voti_attesi = {"sindaci": {}, "liste": {}, "consiglieri": {}}
        self.scrutinio_fatto = False

        elettori = sorted(anagrafe, key=lambda s: int(s.split("_")[1]))
        self.om_elettore.configure(values=elettori)
        self.var_elettore.set(elettori[0])

        self.bb_textbox.delete("1.0", "end")
        self.tb_sindaci.delete("1.0", "end")
        self.tb_liste.delete("1.0", "end")
        self.tb_cons.delete("1.0", "end")

        self.stats_var.set("")
        self.sth_var.set("")
        self.universale_var.set("")
        self.ricevuta_var.set("Nessun voto depositato nel ciclo corrente.")
        self.root_var.set("Radice corrente Merkle Tree: —")

        self._reset_grafico_scheda()
        self._set_running(True)
        self.status_var.set(f"Stato: Attivo · N={n} · Shamir (t={config.SHAMIR_T}, n={config.SHAMIR_N})")
        self._log(f"[OK] Infrastruttura distribuita configurata. IdP, Urna, Commissione e Registri pronti.", "ok")

    @guard
    def reset_sistema(self):
        try:
            if self.idp: self.idp.stop()
            if self.urna: self.urna.stop()
        except Exception:
            pass
        self.idp = self.urna = self.commissione = None
        self._set_running(False)
        self.status_var.set("Stato: Inattivo")
        self._log("[WARN] Tutti i nodi sono stati arrestati. Memoria volatile ripulita.", "warn")

    def _esegui_voto(self, cred, sindaco, lista, consiglieri):
        c = VoterClient(cred, self.commissione.pk_comm, self.urna.sign_pk)
        c.fase1_richiedi_token()
        c.fase2_cifra_scheda(sindaco, lista, consiglieri)
        c.fase3_sottometti()
        self.clients[cred] = c
        self.voti_attesi["sindaci"][sindaco] = self.voti_attesi["sindaci"].get(sindaco, 0) + 1
        self.voti_attesi["liste"][lista] = self.voti_attesi["liste"].get(lista, 0) + 1
        for x in consiglieri:
            self.voti_attesi["consiglieri"][x] = self.voti_attesi["consiglieri"].get(x, 0) + 1
        return c

    @guard
    def vota(self):
        if self.scrutinio_fatto: return
        cred = self.var_elettore.get()
        if not cred: return

        sindaco = self.selected_sindaco.get()
        lista = self.selected_lista.get()

        if sindaco == 0 or lista == 0:
            messagebox.showwarning("Scheda Bianca o Incompleta", "Devi inserire almeno un Sindaco e una Lista facendo click sulla scheda.")
            return

        consiglieri_scelti = []
        mappa_nomi = self.consigliere_nome_to_id.get(lista, {})
        for var in self.selected_consiglieri_vars[lista]:
            val = var.get()
            if val and val not in ("Preferenza 1", "Preferenza 2", "Nessuna Preferenza"):
                cid = mappa_nomi.get(val)
                if cid is not None:
                    consiglieri_scelti.append(cid)

        consiglieri_scelti = list(set(consiglieri_scelti))

        c = self._esegui_voto(cred, sindaco, lista, consiglieri_scelti)
        ok = c.verifica_individuale()

        disgiunto = "Sì" if lista not in config.COALIZIONI[sindaco] else "No"
        self._log(f"[{cred}] Voto Registrato sul Registro Merkle · Voto Disgiunto: {disgiunto}")

        self.ricevuta_var.set(f"Scontrino R (RSA Signed):\n{b64e(c.receipt)[:70]}...\nVerifica Matematica: SUCCESSO")
        self._refresh_bb()
        self._reset_grafico_scheda()
        self._next_elettore()

    def _reset_grafico_scheda(self):
        self.selected_sindaco.set(0)
        self.selected_lista.set(0)
        for item in self.ui_sindaci_marks.values():
            self.canvas.itemconfigure(item, state="hidden")
        for item in self.ui_liste_marks.values():
            self.canvas.itemconfigure(item, state="hidden")
        for id_lista, lista_dropdowns in self.ui_dropdowns_mappati.items():
            lista_dropdowns[0].configure(state="disabled")
            lista_dropdowns[1].configure(state="disabled")
            self.selected_consiglieri_vars[id_lista][0].set("Preferenza 1")
            self.selected_consiglieri_vars[id_lista][1].set("Preferenza 2")

    @guard
    def vota_batch(self):
        if self.scrutinio_fatto: return
        elettori = sorted({f"elettore_{i}" for i in range(self.N_ELETTORI)}, key=lambda s: int(s.split("_")[1]))
        rimanenti = [e for e in elettori if e not in self.clients]

        for cred in rimanenti:
            s = random.choice(list(config.SINDACI))
            l = random.choice(list(config.LISTE))
            candidati_disponibili = list(config.CONSIGLIERI.get(l, {}).keys())
            k_pref = random.randint(0, min(config.MAX_PREFERENZE_CONSIGLIERI, len(candidati_disponibili)))
            cons = random.sample(candidati_disponibili, k=k_pref)

            try:
                self._esegui_voto(cred, s, l, cons)
                self._log(f"[{cred}] Sottomissione automatica riuscita.")
            except RuntimeError as e:
                self._log(f"[{cred}] Rifiutato: {e}", "err")
            self.update_idletasks()

        self._refresh_bb()
        self._next_elettore()
        self.mostra_pagina("bb")

    def _next_elettore(self):
        elettori = sorted({f"elettore_{i}" for i in range(self.N_ELETTORI)}, key=lambda s: int(s.split("_")[1]))
        rimanenti = [e for e in elettori if e not in self.clients]
        if rimanenti:
            self.om_elettore.configure(values=rimanenti)
            self.var_elettore.set(rimanenti[0])
        else:
            self.om_elettore.configure(values=[])
            self.var_elettore.set("")

    def _refresh_bb(self):
        self.bb_textbox.delete("1.0", "end")
        for i, leaf in enumerate(self.urna.bb.leaves):
            self.bb_textbox.insert("end", f"Foglia Transazionale #{i:>2} : {leaf}\n")
        if self.urna.bb.size() > 0:
            self.root_var.set(f"Radice di Merkle Corrente (STH On-Chain Anchor):\n{self.urna.bb.current_root()}")

    @guard
    def verifica_selezionata(self):
        if self.urna.bb.size() == 0: return
        leaf = self.urna.bb.leaves[-1]
        resp, _, _ = request(config.URNA_HOST, config.URNA_PORT, {"op": "inclusion_proof", "leaf": leaf})
        sth_resp, _, _ = request(config.URNA_HOST, config.URNA_PORT, {"op": "get_sth"})

        ok = (resp.get("ok") and
              merkle.verify_proof(leaf, [tuple(x) for x in resp["proof"]], resp["root"]) and
              sth_resp.get("ok") and merkle.verify_sth(sth_resp["sth"], self.urna.sign_pk) and
              sth_resp["sth"]["root"] == resp["root"])

        self._log(f"[AUDIT] Audit crittografico foglia {leaf[:16]}...: {'SUCCESSO' if ok else 'FALLITO'}")
        if ok:
            messagebox.showinfo("Audit Matematico Riuscito", "Inclusion Proof di Merkle e firma RSA dell'STH convalidate con successo!")
        else:
            messagebox.showerror("Fallimento Audit", "Incongruenza logica riscontrata nel cammino di autenticazione!")

    @guard
    def scrutina(self):
        if self.urna.bb.size() == 0:
            messagebox.showwarning("Urna vuota", "Nessun voto depositato da scrutinare.")
            return
        if self.scrutinio_fatto: return

        freeze, _, _ = request(config.URNA_HOST, config.URNA_PORT, {"op": "freeze"})
        risultati, plain_votes, stats = self.commissione.tally(freeze["ciphertexts"], self.commissione.shares)
        sth = freeze["sth"]
        self.scrutinio_fatto = True

        self.stats_var.set(f"Schede totali: {stats['totali']}  |  Valide: {stats['valide']}  |  Nulle (Integrita' HMAC): {stats['nulle_integrita']}  |  Nulle (Semantica): {stats['nulle_semantica']}")
        self.sth_var.set(f"STH Finale: n={sth['n']}, root={sth['root'][:50]}...")

        self._fill(self.tb_sindaci, risultati["sindaci"], config.SINDACI)
        self._fill(self.tb_liste, risultati["liste"], config.LISTE)
        self._fill(self.tb_cons, risultati["consiglieri"], config.CONSIGLIERI)

        ric = {"sindaci": {}, "liste": {}, "consiglieri": {}}
        for pv in plain_votes:
            if not pv["valida"]: continue
            v = pv["voto"]
            ric["sindaci"][v["sindaco"]] = ric["sindaci"].get(v["sindaco"], 0) + 1
            ric["liste"][v["lista"]] = ric["liste"].get(v["lista"], 0) + 1
            for x in v["consiglieri"]:
                ric["consiglieri"][x] = ric["consiglieri"].get(x, 0) + 1

        coerente = (ric == risultati == self.voti_attesi)
        self.universale_var.set(f"Verifica Universale (Tally Recalculation): {'COERENTE (SUCCESSO)' if coerente else 'INCOERENTE (FALLITA)'}")
        self.universale_lbl.configure(text_color="green" if coerente else "red")

        self._log(f"[SCRUTINIO] Computazione terminata. Verifica universale: {'OK' if coerente else 'FALLITA'}")
        self._set_running(False)
        self.btn_scrutina.configure(state="disabled")
        self.mostra_pagina("scrut")

    def _fill(self, tb, agg, names):
        tb.delete("1.0", "end")
        for k, v in sorted(agg.items(), key=lambda x: -x[1]):
            name_str = str(k)
            if any(isinstance(val, dict) for val in names.values()):
                for sub_dict in names.values():
                    if k in sub_dict:
                        name_str = sub_dict[k]
                        break
            else:
                name_str = names.get(k, str(k))
            tb.insert("end", f"{name_str:<35} | Voti: {v}\n")

    def _log(self, msg, tag="info"):
        self.log.insert("end", msg + "\n")
        self.log.see("end")

def main():
    app = ElectionGUI()
    app.mainloop()

if __name__ == "__main__":
    main()