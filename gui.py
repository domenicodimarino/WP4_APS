"""
Interfaccia grafica desktop del prototipo WP4 basata su CustomTkinter.
Garantisce un design moderno, intuitivo e responsivo.

Avvio: python -m wp4.gui
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

# Configurazione del tema
ctk.set_appearance_mode("System")  # Usa il tema di sistema (Light/Dark)
ctk.set_default_color_theme("blue")

def guard(method):
    """Decoratore: cattura le eccezioni dei callback e le mostra."""
    def wrapper(self, *a, **k):
        try:
            return method(self, *a, **k)
        except Exception as exc:
            self._log(f"ERRORE in {method.__name__}: {exc}", "err")
            messagebox.showerror("Errore", f"{method.__name__}: {exc}")
    return wrapper

class ElectionGUI(ctk.CTk):
    N_ELETTORI = 1000

    def __init__(self):
        super().__init__()
        self.update()
        self.title("Voto Elettronico — Cava de' Tirreni (WP4)")
        self.geometry("1100x800")
        
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
        self.page_vote.grid_columnconfigure(1, weight=1)
        self.page_vote.grid_rowconfigure(0, weight=1)

        # PANNELLO SINISTRO: Scheda Elettorale
        card = ctk.CTkFrame(self.page_vote)
        card.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        
        ctk.CTkLabel(card, text="Scheda Elettorale", font=ctk.CTkFont(size=18, weight="bold")).pack(anchor="w", padx=20, pady=(20, 10))

        # Elettore
        ctk.CTkLabel(card, text="1. Identità Elettore (IdP)").pack(anchor="w", padx=20)
        self.var_elettore = ctk.StringVar(value="")
        self.om_elettore = ctk.CTkOptionMenu(card, variable=self.var_elettore, values=[], width=250)
        self.om_elettore.pack(anchor="w", padx=20, pady=(0, 15))

        # Sindaco
        ctk.CTkLabel(card, text="2. Candidato Sindaco").pack(anchor="w", padx=20)
        self.var_sindaco = ctk.StringVar()
        self.sindaco_opts = [f"{k} — {v}" for k, v in config.SINDACI.items()]
        self.om_sindaco = ctk.CTkOptionMenu(card, variable=self.var_sindaco, values=self.sindaco_opts, width=250)
        self.om_sindaco.pack(anchor="w", padx=20, pady=(0, 15))

        # Lista
        ctk.CTkLabel(card, text="3. Lista Collegata").pack(anchor="w", padx=20)
        self.var_lista = ctk.StringVar()
        self.lista_opts = [f"{k} — {v}" for k, v in config.LISTE.items()]

        self.om_lista = ctk.CTkOptionMenu(
            card, 
            variable=self.var_lista, 
            values=self.lista_opts, 
            width=250,
            command=self._aggiorna_consiglieri_filtrati
        )

        self.om_lista.pack(anchor="w", padx=20, pady=(0, 15))

        # Consiglieri (Nuovo sistema con ScrollableFrame e Checkbox)
        ctk.CTkLabel(card, text=f"4. Consiglieri (max {config.MAX_PREFERENZE_CONSIGLIERI})").pack(anchor="w", padx=20)
        self.consiglieri_frame = ctk.CTkScrollableFrame(card, height=150, width=230)
        self.consiglieri_frame.pack(anchor="w", padx=20, pady=(0, 20))
        
        self.consiglieri_checkboxes = []
        
        # Cicliamo prima sulle liste per creare i raggruppamenti visivi
        for id_lista, nome_lista in config.LISTE.items():
            # Intestazione della Lista (es. --- Cava Civica ---)
            lbl_gruppo = ctk.CTkLabel(
                self.consiglieri_frame, 
                text=f"--- {nome_lista} ---", 
                font=ctk.CTkFont(size=11, weight="bold"),
                text_color="gray"
            )
            lbl_gruppo.pack(anchor="w", pady=(6, 2), padx=5)
            
            # Checkbox per ogni consigliere appartenente a QUELLA specifica lista
            candidati_lista = config.CONSIGLIERI.get(id_lista, {})
            for k, v in candidati_lista.items():
                cb = ctk.CTkCheckBox(self.consiglieri_frame, text=f"{k} — {v}")
                cb.pack(anchor="w", pady=2, padx=15)
                self.consiglieri_checkboxes.append((k, cb)) # Mantiene l'ID originale (es. 101)

        # Bottoni Azione
        self.btn_vota = ctk.CTkButton(card, text="Cifra e Sottometti Voto", font=ctk.CTkFont(weight="bold"), command=self.vota)
        self.btn_vota.pack(fill="x", padx=20, pady=5)
        
        self.btn_batch = ctk.CTkButton(card, text="Voto Automatico (Rimanenti)", fg_color="gray40", command=self.vota_batch)
        self.btn_batch.pack(fill="x", padx=20, pady=5)

        self.ricevuta_var = ctk.StringVar(value="")
        ctk.CTkLabel(card, textvariable=self.ricevuta_var, font=ctk.CTkFont(family="Courier", size=10), justify="left", wraplength=250).pack(anchor="w", padx=20, pady=10)

        # PANNELLO DESTRO: Bulletin Board
        right = ctk.CTkFrame(self.page_vote)
        right.grid(row=0, column=1, sticky="nsew")
        
        ctk.CTkLabel(right, text="Bulletin Board (Registro Merkle)", font=ctk.CTkFont(size=18, weight="bold")).pack(anchor="w", padx=20, pady=(20, 5))
        
        self.root_var = ctk.StringVar(value="Radice corrente: —")
        ctk.CTkLabel(right, textvariable=self.root_var, font=ctk.CTkFont(family="Courier", weight="bold")).pack(anchor="w", padx=20)
        
        self.bb_textbox = ctk.CTkTextbox(right, font=ctk.CTkFont(family="Courier", size=12))
        self.bb_textbox.pack(fill="both", expand=True, padx=20, pady=10)
        
        self.btn_verifica_bb = ctk.CTkButton(right, text="Verifica individuale dell'ultimo voto immesso", command=self.verifica_selezionata)
        self.btn_verifica_bb.pack(anchor="e", padx=20, pady=(0, 20))

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

        # Risultati
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
        self.om_sindaco.configure(state=state)
        self.om_lista.configure(state=state)
        for _, cb in self.consiglieri_checkboxes:
            cb.configure(state=state)
        
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
        self.var_sindaco.set(self.sindaco_opts[0])
        self.var_lista.set(self.lista_opts[0])

        self.bb_textbox.delete("1.0", "end")
        self.tb_sindaci.delete("1.0", "end")
        self.tb_liste.delete("1.0", "end")
        self.tb_cons.delete("1.0", "end")
        
        self.stats_var.set("")
        self.sth_var.set("")
        self.universale_var.set("")
        self.ricevuta_var.set("")
        self.root_var.set("Radice corrente: —")
        
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
        if self.scrutinio_fatto:
            messagebox.showwarning("Urne chiuse", "Lo scrutinio è già avvenuto.")
            return
        cred = self.var_elettore.get()
        if not cred:
            messagebox.showinfo("Nessun elettore", "Tutti gli elettori hanno già votato.")
            return
        
        sindaco = self._parse_id(self.var_sindaco.get())
        lista = self._parse_id(self.var_lista.get())
        
        # Gestione preferenze tramite Checkbox
        consiglieri_selezionati = [k for k, cb in self.consiglieri_checkboxes if cb.get() == 1]
        
        if len(consiglieri_selezionati) > config.MAX_PREFERENZE_CONSIGLIERI:
            messagebox.showerror("Errore", f"Puoi selezionare al massimo {config.MAX_PREFERENZE_CONSIGLIERI} consiglieri.")
            return
            
        try:
            c = self._esegui_voto(cred, sindaco, lista, consiglieri_selezionati)
        except RuntimeError as e:
            self._log(f"[{cred}] voto rifiutato: {e}", "err")
            messagebox.showerror("Voto rifiutato", str(e))
            return
            
        ok = c.verifica_individuale()
        self._log(f"[{cred}] Voto Registrato · H(C)={c.leaf[:16]}… · Verifica individuale {'OK' if ok else 'FALLITA'}")
        self.ricevuta_var.set(f"Ricevuta R:\n{b64e(c.receipt)[:60]}...\nVerifica BB Individuale: {'OK' if ok else 'FALLITA'}")
        
        self._refresh_bb()
        
        # Deseleziona le checkbox per il prossimo elettore
        for _, cb in self.consiglieri_checkboxes:
            cb.deselect()
            
        self._next_elettore()

    @guard
    def vota_batch(self):
        if self.scrutinio_fatto:
            return
        elettori = sorted({f"elettore_{i}" for i in range(self.N_ELETTORI)}, key=lambda s: int(s.split("_")[1]))
        rimanenti = [e for e in elettori if e not in self.clients]
        
        for cred in rimanenti:
            s = random.choice(list(config.SINDACI))
            l = random.choice(list(config.LISTE))
            
            # CORREZIONE: Estrae i candidati disponibili SOLO per la lista estratta
            candidati_disponibili = list(config.CONSIGLIERI.get(l, {}).keys())
            
            # Seleziona un numero di preferenze valido
            k_pref = random.randint(0, min(config.MAX_PREFERENZE_CONSIGLIERI, len(candidati_disponibili)))
            cons = random.sample(candidati_disponibili, k=k_pref)
            
            try:
                self._esegui_voto(cred, s, l, cons)
                self._log(f"[{cred}] Voto automatico completato.")
            except RuntimeError as e:
                self._log(f"[{cred}] {e}", "err")
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
            self.root_var.set(f"Radice corrente: {self.urna.bb.current_root()[:50]}...")

    @guard
    def verifica_selezionata(self):
        if self.urna.bb.size() == 0:
            return
        leaf = self.urna.bb.leaves[-1]  # Verifica l'ultimo inserito per semplicità
        resp, _, _ = request(config.URNA_HOST, config.URNA_PORT, {"op": "inclusion_proof", "leaf": leaf})
        sth_resp, _, _ = request(config.URNA_HOST, config.URNA_PORT, {"op": "get_sth"})
        
        ok = (resp.get("ok") and
              merkle.verify_proof(leaf, [tuple(x) for x in resp["proof"]], resp["root"]) and
              sth_resp.get("ok") and merkle.verify_sth(sth_resp["sth"], self.urna.sign_pk) and
              sth_resp["sth"]["root"] == resp["root"])
              
        self._log(f"[VERIFICA INDIVIDUALE] Foglia {leaf[:16]}... : {'OK' if ok else 'FALLITA'}")
        if ok:
            messagebox.showinfo("Successo", "Il percorso di Merkle e la firma RSA dell'STH sono validi!")
        else:
            messagebox.showerror("Errore", "Verifica matematica fallita!")

    @guard
    def scrutina(self):
        if self.urna.bb.size() == 0:
            messagebox.showwarning("Urna vuota", "Nessun voto da scrutinare.")
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
        self.universale_var.set(f"Verifica Universale (ricalcolo indipendente): {'COERENTE (SUCCESSO)' if coerente else 'INCOERENTE (FALLITA)'}")
        self.universale_lbl.configure(text_color="green" if coerente else "red")
        
        self._log(f"[SCRUTINIO COMPLETO] Schede processate. Verifica universale: {'OK' if coerente else 'ERR'}")
        
        self.btn_vota.configure(state="disabled")
        self.btn_batch.configure(state="disabled")
        self.mostra_pagina("scrut")

    def _fill(self, tb, agg, names):
        tb.delete("1.0", "end")
        for k, v in sorted(agg.items(), key=lambda x: -x[1]):
            # Gestione dinamica: funziona sia con dizionari piatti che annidati
            name_str = str(k)
            if any(isinstance(val, dict) for val in names.values()):
                # Se è annidato (come i CONSIGLIERI), cerca nei sotto-dizionari
                for sub_dict in names.values():
                    if k in sub_dict:
                        name_str = sub_dict[k]
                        break
            else:
                # Se è piatto (come SINDACI o LISTE)
                name_str = names.get(k, str(k))
                
            tb.insert("end", f"{name_str:<25} | Voti: {v}\n")

    def _aggiorna_consiglieri_filtrati(self, scelta_lista):
        # Estraiamo l'ID numerico della lista selezionata (es. "10 — Lista Civica" -> 10)
        id_lista = self._parse_id(scelta_lista)
        
        # Distruggiamo le vecchie checkbox nello scrollable frame
        for widget in self.consiglieri_frame.winfo_children():
            widget.destroy()
        self.consiglieri_checkboxes.clear()
        
        # Preleviamo solo i consiglieri associati a QUELLA lista dal config
        consiglieri_della_lista = config.CONSIGLIERI.get(id_lista, {})
        
        # Ridisegnamo solo i candidati pertinenti
        for k, v in consiglieri_della_lista.items():
            cb = ctk.CTkCheckBox(self.consiglieri_frame, text=f"{k} — {v}")
            cb.pack(anchor="w", pady=2, padx=5)
            self.consiglieri_checkboxes.append((k, cb))

def main():
    app = ElectionGUI()
    app.mainloop()

if __name__ == "__main__":
    main()