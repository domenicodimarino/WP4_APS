"""
Interfaccia grafica desktop del prototipo WP4 basata su CustomTkinter.
Garantisce un design moderno, intuitivo e responsivo modellato sulla
vera scheda elettorale del Comune di Cava de' Tirreni.

Avvio: python -m nuovo_wp4.gui
Richiede: pip install customtkinter
"""
from __future__ import annotations

import random
import threading
import customtkinter as ctk
from tkinter import messagebox

from . import config
from . import crypto_primitives as cp
from . import merkle
from .parties.client import VoterClient
from .parties.commissione import Commissione
from .parties.idp import IdentityProvider
from .parties.urna import Urna
from .transport import b64e, request

# Configurazione del tema grafico conforme ai requisiti di usabilità aziendale/universitaria
ctk.set_appearance_mode("System")  # Adatta il tema al Light/Dark mode del Mac
ctk.set_default_color_theme("blue")

def guard(method):
    """Decoratore: cattura le eccezioni dei callback di rete e le mostra a schermo."""
    def wrapper(self, *a, **k):
        try:
            return method(self, *a, **k)
        except Exception as exc:
            self._log(f"ERRORE in {method.__name__}: {exc}", "err")
            messagebox.showerror("Errore", f"{method.__name__}: {exc}")
    return wrapper

class ElectionGUI(ctk.CTk):
    N_ELETTORI = 1000  # Scalabile a piacimento (es. 1000). Impostato a 12 per rendere fluido l'OptionMenu su Mac.

    def __init__(self):
        super().__init__()
        self.update()  # Previene i blocchi di allocazione della finestra su macOS
        self.title("Voto Elettronico — Cava de' Tirreni (WP4)")
        self.geometry("1200x800")
        
        self.idp = self.urna = self.commissione = None
        self.clients = {}
        self.voti_attesi = {"sindaci": {}, "liste": {}, "consiglieri": {}}
        self.scrutinio_fatto = False

        self._build_topbar()
        self._build_pages()
        self._build_log()
        self.mostra_pagina("vote")
        self._set_running(False)

    def _build_topbar(self):
        bar = ctk.CTkFrame(self, corner_radius=0, fg_color=("gray85", "gray15"))
        bar.pack(fill="x", side="top")
        
        title = ctk.CTkLabel(bar, text="Elezione Comunale — Cava de' Tirreni", font=ctk.CTkFont(size=20, weight="bold"))
        title.pack(side="left", padx=20, pady=15)
        
        self.btn_start = ctk.CTkButton(bar, text="Avvia sistema", command=self.avvia_sistema)
        self.btn_start.pack(side="right", padx=10, pady=15)
        
        self.btn_reset = ctk.CTkButton(bar, text="Reset", command=self.reset_sistema, fg_color="transparent", border_width=1, text_color=("black", "white"))
        self.btn_reset.pack(side="right", padx=10, pady=15)
        
        self.status_var = ctk.StringVar(value="Sistema non avviato")
        ctk.CTkLabel(bar, textvariable=self.status_var, font=ctk.CTkFont(size=12, slant="italic")).pack(side="right", padx=20)

        # Tab Navigation
        nav = ctk.CTkFrame(self, fg_color="transparent")
        nav.pack(fill="x", pady=10, padx=20)
        
        self.btn_tab_vote = ctk.CTkButton(nav, text="Urna Digitale (Fasi 1-3)", command=lambda: self.mostra_pagina("vote"), width=200)
        self.btn_tab_vote.pack(side="left", padx=5)
        
        self.btn_tab_scrut = ctk.CTkButton(nav, text="Commissione di Scrutinio (Fase 4)", command=lambda: self.mostra_pagina("scrut"), width=200, fg_color="gray40")
        self.btn_tab_scrut.pack(side="left", padx=5)

    def _build_pages(self):
        self.container = ctk.CTkFrame(self, fg_color="transparent")
        self.container.pack(fill="both", expand=True, padx=20, pady=5)
        self.container.grid_rowconfigure(0, weight=1)
        self.container.grid_columnconfigure(0, weight=1)
        
        self.page_vote = ctk.CTkFrame(self.container, fg_color="transparent")
        self.page_scrut = ctk.CTkFrame(self.container, fg_color="transparent")
        
        for p in (self.page_vote, self.page_scrut):
            p.grid(row=0, column=0, sticky="nsew")
            
        self._build_page_vote()
        self._build_page_scrut()

    def mostra_pagina(self, which):
        if which == "vote":
            self.page_vote.tkraise()
            self.btn_tab_vote.configure(fg_color=["#3a7ebf", "#1f538d"])
            self.btn_tab_scrut.configure(fg_color="gray40")
        else:
            self.page_scrut.tkraise()
            self.btn_tab_scrut.configure(fg_color=["#3a7ebf", "#1f538d"])
            self.btn_tab_vote.configure(fg_color="gray40")

    def _build_page_vote(self):
        # Griglia divisa in due colonne primarie: 0 (Scheda Elettorale) e 1 (Bulletin Board Merkle)
        self.page_vote.grid_columnconfigure(0, weight=3)
        self.page_vote.grid_columnconfigure(1, weight=2)
        self.page_vote.grid_rowconfigure(0, weight=1)

        # PANNELLO SINISTRO: Scheda Elettorale di Cava de' Tirreni (Scrollable)
        scheda_scroll = ctk.CTkScrollableFrame(self.page_vote, label_text="SCHEDA ELETTORALE — COMUNE DI CAVA DE' TIRRENI")
        scheda_scroll.grid(row=0, column=0, sticky="nsew", padx=(0, 10), pady=10)
        scheda_scroll.grid_columnconfigure(0, weight=1)

        # Stato delle selezioni correnti (Variabili di voto)
        self.selected_sindaco = ctk.IntVar(value=0)
        self.selected_lista = ctk.IntVar(value=0)
        self.selected_consiglieri_vars = {} # Mappa: id_lista -> [StringVar, StringVar]

        # Strutture per la manipolazione dinamica dello stato grafico
        self.ui_sindaci_labels = {}
        self.ui_liste_labels = {}
        self.ui_sindaci_buttons = []
        self.ui_liste_buttons = []
        self.ui_dropdowns_consiglieri = []

        # Box di selezione identità (Fase 1: IdP)
        id_frame = ctk.CTkFrame(scheda_scroll, fg_color=("gray90", "gray20"))
        id_frame.pack(fill="x", padx=10, pady=10)
        
        ctk.CTkLabel(id_frame, text="Autenticazione Elettore:", font=ctk.CTkFont(weight="bold")).pack(side="left", padx=10, pady=10)
        self.var_elettore = ctk.StringVar()
        self.om_elettore = ctk.CTkOptionMenu(id_frame, variable=self.var_elettore, values=[], width=180)
        self.om_elettore.pack(side="left", padx=10, pady=10)
        
        self.btn_vota = ctk.CTkButton(id_frame, text="Invia Scheda Cifrata", font=ctk.CTkFont(weight="bold"), command=self.vota)
        self.btn_vota.pack(side="right", padx=10, pady=10)
        self.btn_batch = ctk.CTkButton(id_frame, text="Voto Automatico", fg_color="gray40", command=self.vota_batch)
        self.btn_batch.pack(side="right", padx=10, pady=10)

        # Corpo della Scheda Elettorale diviso in 2 colonne principali (Fac-simile reale)
        body_frame = ctk.CTkFrame(scheda_scroll, fg_color="transparent")
        body_frame.pack(fill="both", expand=True, padx=5, pady=5)
        body_frame.grid_columnconfigure((0, 1), weight=1)

        col_mapping = {1: 0, 2: 0, 3: 0, 4: 1, 5: 1}
        row_counter = {0: 0, 1: 0}

        for s_id, s_nome in config.SINDACI.items():
            target_col = col_mapping[s_id]
            target_row = row_counter[target_col]
            row_counter[target_col] += 1

            # Blocco rettangolare del Candidato Sindaco
            s_frame = ctk.CTkFrame(body_frame, border_width=2, border_color=("gray70", "gray30"))
            s_frame.grid(row=target_row, column=target_col, padx=8, pady=8, sticky="nsew")
            
            # Header del Sindaco (Risolve il TclError disaccoppiando il geometry manager del bottone)
            s_header_frame = ctk.CTkFrame(s_frame, fg_color="transparent")
            s_header_frame.pack(fill="x", padx=5, pady=5)
            
            btn_s = ctk.CTkButton(
                s_header_frame, 
                text=f"Candidato Sindaco: {s_nome}", 
                font=ctk.CTkFont(size=12, weight="bold"),
                anchor="w",
                fg_color=("gray85", "gray25"),
                text_color=("black", "white"),
                command=lambda sid=s_id: self._select_sindaco(sid)
            )
            btn_s.pack(side="left", fill="x", expand=True, padx=(2, 5), pady=2)
            self.ui_sindaci_buttons.append(btn_s)
            
            x_s_label = ctk.CTkLabel(s_header_frame, text="", font=ctk.CTkFont(size=14, weight="bold"), text_color="red")
            x_s_label.pack(side="right", padx=5)
            self.ui_sindaci_labels[s_id] = x_s_label

            # Generazione delle liste collegate alla coalizione del Sindaco
            liste_collegate = config.COALIZIONI.get(s_id, [])
            for l_id in liste_collegate:
                l_nome = config.LISTE[l_id]
                
                l_frame = ctk.CTkFrame(s_frame, fg_color=("gray95", "gray20"), border_width=1, border_color="gray50")
                l_frame.pack(fill="x", padx=10, pady=4)

                # Segnaposto visivo per la X della lista (messo a sinistra per simulare la croce sul simbolo)
                x_l_label = ctk.CTkLabel(l_frame, text="", font=ctk.CTkFont(size=14, weight="bold"), text_color="red")
                x_l_label.pack(side="left", padx=5)
                self.ui_liste_labels[l_id] = x_l_label

                btn_l = ctk.CTkButton(
                    l_frame,
                    text=f"{l_nome}",
                    anchor="w",
                    fg_color="transparent",
                    text_color=("black", "white"),
                    command=lambda lid=l_id: self._select_lista(lid)
                )
                btn_l.pack(side="left", fill="x", expand=True, padx=5, pady=5)
                self.ui_liste_buttons.append(btn_l)

                # Dropdown per esprimere le preferenze nominali dei consiglieri
                drop_frame = ctk.CTkFrame(l_frame, fg_color="transparent")
                drop_frame.pack(side="right", padx=5)
                
                self.selected_consiglieri_vars[l_id] = [
                    ctk.StringVar(value="Preferenza 1"), 
                    ctk.StringVar(value="Preferenza 2")
                ]
                candidati_lista = [f"{k} — {v}" for k, v in config.CONSIGLIERI.get(l_id, {}).items()]
                
                for idx in range(2):
                    om = ctk.CTkOptionMenu(
                        drop_frame, 
                        variable=self.selected_consiglieri_vars[l_id][idx], 
                        values=["Nessuna Preferenza"] + candidati_lista,
                        width=135,
                        font=ctk.CTkFont(size=10)
                    )
                    om.pack(side="top", pady=1)
                    self.ui_dropdowns_consiglieri.append(om)

        # PANNELLO DESTRO: Bulletin Board (Registro ad integrità algoritmica)
        right = ctk.CTkFrame(self.page_vote)
        right.grid(row=0, column=1, sticky="nsew", padx=(10, 0), pady=10)
        
        ctk.CTkLabel(right, text="Bulletin Board (Registro Merkle)", font=ctk.CTkFont(size=18, weight="bold")).pack(anchor="w", padx=20, pady=(20, 5))
        
        self.root_var = ctk.StringVar(value="Radice corrente: —")
        ctk.CTkLabel(right, textvariable=self.root_var, font=ctk.CTkFont(family="Courier", weight="bold"), justify="left", wraplength=400).pack(anchor="w", padx=20)
        
        self.bb_textbox = ctk.CTkTextbox(right, font=ctk.CTkFont(family="Courier", size=11))
        self.bb_textbox.pack(fill="both", expand=True, padx=20, pady=10)
        
        self.btn_verifica_bb = ctk.CTkButton(right, text="Verifica Matematica Ultimo Voto", command=self.verifica_selezionata)
        self.btn_verifica_bb.pack(anchor="e", padx=20, pady=(0, 10))

        # Visualizzatore dinamico delle ricevute crittografiche firmate dall'Urna
        self.ricevuta_var = ctk.StringVar(value="")
        ctk.CTkLabel(right, textvariable=self.ricevuta_var, font=ctk.CTkFont(family="Courier", size=10), justify="left", wraplength=400, text_color="green").pack(anchor="w", padx=20, pady=10)

    def _select_sindaco(self, sid: int):
        self.selected_sindaco.set(sid)
        for k, lbl in self.ui_sindaci_labels.items():
            lbl.configure(text="[ X ]" if k == sid else "")
        self._log(f"[GUI] Selezionato Candidato Sindaco: {config.SINDACI[sid]}")

    def _select_lista(self, lid: int):
        self.selected_lista.set(lid)
        for k, lbl in self.ui_liste_labels.items():
            lbl.configure(text="[ X ]" if k == lid else "")
        self._log(f"[GUI] Selezionata Lista Circoscrizionale: {config.LISTE[lid]}")

    def _build_page_scrut(self):
        top = ctk.CTkFrame(self.page_scrut)
        top.pack(fill="x")
        
        ctk.CTkLabel(top, text="Fase 4 — Scrutinio", font=ctk.CTkFont(size=18, weight="bold")).pack(anchor="w", padx=20, pady=(20, 5))
        ctk.CTkLabel(top, text="Simula la chiusura urne, ricomposizione SK_Comm tramite Shamir's Secret Sharing (t,n),\nShuffling, verifica Encrypt-then-MAC, e decifratura.", justify="left").pack(anchor="w", padx=20)
        
        self.btn_scrutina = ctk.CTkButton(top, text="Chiudi Urne ed Esegui Scrutinio", font=ctk.CTkFont(weight="bold"), command=self.scrutina)
        self.btn_scrutina.pack(anchor="w", padx=20, pady=15)
        
        self.stats_var = ctk.StringVar(value="")
        ctk.CTkLabel(top, textvariable=self.stats_var).pack(anchor="w", padx=20)
        
        self.sth_var = ctk.StringVar(value="")
        ctk.CTkLabel(top, textvariable=self.sth_var, font=ctk.CTkFont(family="Courier", size=11), text_color="gray").pack(anchor="w", padx=20)
        
        self.universale_var = ctk.StringVar(value="")
        self.universale_lbl = ctk.CTkLabel(top, textvariable=self.universale_var, font=ctk.CTkFont(size=14, weight="bold"))
        self.universale_lbl.pack(anchor="w", padx=20, pady=(10, 20))

        # Risultati strutturati su 3 colonne
        res = ctk.CTkFrame(self.page_scrut, fg_color="transparent")
        res.pack(fill="both", expand=True, pady=(10, 0))
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

    def _build_log(self):
        frame = ctk.CTkFrame(self, fg_color="transparent")
        frame.pack(fill="x", padx=20, pady=10)
        ctk.CTkLabel(frame, text="Log di Rete e Protocollo", font=ctk.CTkFont(weight="bold")).pack(anchor="w")
        self.log = ctk.CTkTextbox(frame, height=100, font=ctk.CTkFont(family="Courier", size=11))
        self.log.pack(fill="x")

    def _log(self, msg, tag="info"):
        self.log.insert("end", msg + "\n")
        self.log.see("end")

    def _set_running(self, running: bool):
        state = "normal" if running else "disabled"
        self.btn_vota.configure(state=state)
        self.btn_batch.configure(state=state)
        self.btn_scrutina.configure(state=state)
        self.om_elettore.configure(state=state)
        
        # Abilita/Disabilita dinamicamente i nuovi elementi interattivi della scheda per coerenza di stato
        for btn in self.ui_sindaci_buttons: btn.configure(state=state)
        for btn in self.ui_liste_buttons: btn.configure(state=state)
        for om in self.ui_dropdowns_consiglieri: om.configure(state=state)
        
        self.btn_start.configure(state="disabled" if running else "normal")

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
        self.ricevuta_var.set("")
        self.root_var.set("Radice corrente: —")
        
        # Ripristino dello stato visivo originario
        self.selected_sindaco.set(0)
        self.selected_lista.set(0)
        for lbl in self.ui_sindaci_labels.values(): lbl.configure(text="")
        for lbl in self.ui_liste_labels.values(): lbl.configure(text="")
        for l_id in self.selected_consiglieri_vars:
            self.selected_consiglieri_vars[l_id][0].set("Preferenza 1")
            self.selected_consiglieri_vars[l_id][1].set("Preferenza 2")
        
        self._set_running(True)
        self.status_var.set(f"Sistema Attivo · {n} Elettori · Shamir (t={config.SHAMIR_T}, n={config.SHAMIR_N})")
        self._log(f"[OK] Sistema avviato: IdP, Urna, Commissione. Anagrafe {n} elettori.", "ok")

    @guard
    def reset_sistema(self):
        try:
            if self.idp: self.idp.stop()
            if self.urna: self.urna.stop()
        except Exception:
            pass
        self.idp = self.urna = self.commissione = None
        self._set_running(False)
        self.status_var.set("Sistema non avviato")
        self._log("[WARN] Sistema resettato.")

    def _parse_id(self, value):
        return int(value.split(" — ")[0])

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
            messagebox.showwarning("Scheda Incompleta", "Selezionare un Sindaco e una Lista cliccando sui relativi riquadri della scheda.")
            return

        # Estrazione e parsing delle preferenze nominali dei consiglieri della lista votata
        consiglieri_scelti = []
        for var in self.selected_consiglieri_vars[lista]:
            val = var.get()
            if val and val not in ("Preferenza 1", "Preferenza 2", "Nessuna Preferenza"):
                c_id = self._parse_id(val)
                consiglieri_scelti.append(c_id)

        # Trattamento delle preferenze ripetute (Voto corretto per unicità)
        consiglieri_scelti = list(set(consiglieri_scelti))

        c = self._esegui_voto(cred, sindaco, lista, consiglieri_scelti)
        ok = c.verifica_individuale()
        
        disgiunto = "Sì" if lista not in config.COALIZIONI[sindaco] else "No"
        self._log(f"[{cred}] Voto Sottomesso · Ricevuta Verificata: {'OK' if ok else 'FALLITA'} · Disgiunto: {disgiunto}")
        
        self.ricevuta_var.set(f"Ricevuta R (Firmata RSA dall'Urna):\n{b64e(c.receipt)[:65]}...\nVerifica BB Individuale: {'SUCCESSO' if ok else 'ERR'}")
        self._refresh_bb()

        # Reset grafico della scheda per garantire il diritto di segretezza visiva al voto successivo
        self.selected_sindaco.set(0)
        self.selected_lista.set(0)
        for lbl in self.ui_sindaci_labels.values(): lbl.configure(text="")
        for lbl in self.ui_liste_labels.values(): lbl.configure(text="")
        for l_id in self.selected_consiglieri_vars:
            self.selected_consiglieri_vars[l_id][0].set("Preferenza 1")
            self.selected_consiglieri_vars[l_id][1].set("Preferenza 2")
        
        self._next_elettore()

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
                self._log(f"[{cred}] Voto automatico completato (Disgiunto: {'Sì' if l not in config.COALIZIONI[s] else 'No'}).")
            except RuntimeError as e:
                self._log(f"[{cred}] Rifiutato: {e}", "err")
            self.update_idletasks()
            
        self._refresh_bb()
        self._next_elettore()

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
            self.bb_textbox.insert("end", f"Foglia #{i:>2} : {leaf[:50]}...\n")
        if self.urna.bb.size() > 0:
            self.root_var.set(f"Radice corrente Merkle Tree:\n{self.urna.bb.current_root()}")

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
              
        self._log(f"[AUDIT MATH] Foglia {leaf[:16]}...: {'VALIDA (Inclusion Proof & STH RSA OK)' if ok else 'FALLITA'}")
        if ok:
            messagebox.showinfo("Successo", "Verifica Matematica Riuscita!\nIl percorso di Merkle e la firma RSA dell'STH sono validi.")
        else:
            messagebox.showerror("Errore", "Audit fallito!")

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

        self.stats_var.set(f"Schede totali: {stats['totali']}  |  Valide: {stats['valide']}  |  Nulle (Integrità HMAC): {stats['nulle_integrita']}  |  Nulle (Semantica): {stats['nulle_semantica']}")
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
                
            tb.insert("end", f"{name_str:<25} | Voti: {v}\n")

def main():
    app = ElectionGUI()
    app.mainloop()

if __name__ == "__main__":
    main()