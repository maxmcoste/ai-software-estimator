# Modello di Stima Software "Core & Satellites" (Post-GenAI Era)

## 1. Strategia di Stima: Il Cambio di Paradigma
Il modello tradizionale basato su una percentuale dello sviluppo (es. PM = 20% del coding) è reso obsoleto dalla GenAI. Se l'IA abbatte i tempi di sviluppo del 50%, non significa che la complessità di gestione o i requisiti di sicurezza si dimezzino; al contrario, spesso aumentano.

**Principi Guida:**
* **Scomposizione del Valore:** Il costo del "fare" (Core) viene isolato dal costo del "garantire" (Satelliti).
* **Decoupling:** Ogni servizio satellite ha la propria metrica di stima indipendente dal volume di codice prodotto.
* **Human-in-the-Loop:** Il Core include sempre una quota di revisione umana, mentre i satelliti rappresentano il valore intellettuale e legale insostituibile.

---

## 2. Architettura del Modello: Core e Satelliti

### A. Il Core (The Engine)
Rappresenta la costruzione della logica funzionale assistita da AI.
* **Componenti:** Sviluppo Frontend/Backend, Unit Testing generato, Prompt Engineering, Code Review assistita.
* **Metrica:** **Functional Complexity Units (FCU)** + Moltiplicatori di contesto.

### B. I Servizi Satellite (The Orbit)
Servizi indipendenti che garantiscono il successo, la sicurezza e la scalabilità del Core.
1.  **Project Management & Orchestration (PM&O):** Governance e gestione stakeholder.
2.  **Solution Architecture & Infra:** Design sistemico, IaC e gestione Cloud (FinOps).
3.  **Cybersecurity & Compliance:** Protezione dei dati e validazione legale.
4.  **Digital Experience (DX):** UX/UI Strategy e design dei flussi.
5.  **Quality Assurance (QA):** Validazione di integrità e test di regressione.

---

## 3. Modello di Stima Dettagliato

### CORE: Functional Complexity Units (FCU)
La stima del Core non si basa sulle ore, ma sulla densità funzionale.

* **Base FCU:** Somma di Entità Dati (CRUD), Integrazioni API e Complessità della Business Logic.
* **Moltiplicatore di Scalabilità:**
    * *Low* (<1k utenti/mese): 1.0x
    * *Medium* (1k-50k utenti/mese): 1.3x
    * *High* (>50k utenti/mese o Critical): 1.8x
* **Il fattore "SPIKE":** Add-on fisso per ogni incognita tecnologica o integrazione Legacy (R&D).

**Formula:** $Stima\_Core = (Base\_FCU \times Moltiplicatore\_Scalabilità) + Costo\_Spike$

---

### SATELLITE 1: Project Management & Orchestration (PM&O)
Scollegato dal costo del codice, legato alla durata e alla complessità del team.

* **Metrica:** **Calendar-Based Service Unit (CBSU)**.
* **Base FTE (Minimo Fisiologico):** * 0.2 FTE/mese per progetti Small.
    * 0.5 FTE/mese per progetti Medium.
    * 1.0 FTE/mese per progetti Large/Enterprise.
* **Fattore Team:** x1.2 se Multi-vendor; x1.15 se co-working con team cliente.

**Formula:** $Costo_{PM} = (Base\_FTE \times Mesi\_Progetto) \times Fattore\_Team$

---

### SATELLITE 2: Solution Architecture & Infrastructure
Include il design logico e la gestione degli ambienti (Cloud/DevOps).

* **Design Blueprint:** Flat fee basata sul numero di sistemi esterni da integrare.
* **Environment Complexity (ECU):** Setup degli ambienti (Dev, Test, Prod) basato su SLA richiesti.
* **FinOps & Governance:** Canone mensile per il monitoraggio dei costi cloud e l'ottemperanza alle linee guida architetturali.

**Formula:** $Costo_{SA} = Blueprint\_Setup + (\sum ECU) + Monthly\_Governance$

---

### SATELLITE 3: Cybersecurity & Compliance
Basato sulla "superficie di attacco" e sulla sensibilità dei dati gestiti.

* **Tier di Sensibilità:** * *Basic:* Dati pubblici.
    * *Standard:* PII/GDPR.
    * *Critical:* Dati finanziari/sanitari.
* **Security Gate:** Costo fisso per ogni rilascio "Major" (Vulnerability Assessment, SAST/DAST).
* **Compliance Add-on:** Costo una-tantum per pratiche legali (DPIA, auditing ISO).

**Formula:** $Costo_{Cyber} = Base\_Shield + (N\_Security\_Gate \times Prezzo\_Gate)$

---

### SATELLITE 4: Digital Experience (DX)
Basato sulla complessità dei percorsi utente, non sul numero di pagine.

* **User Journey Complexity (UJC):** * *Simple:* Flussi lineari (Login).
    * *Transactional:* Flussi a stati (Checkout/Wizard).
    * *Expert:* Dashboard dense di dati.
* **Accessibility Factor:** Moltiplicatore per conformità WCAG 2.1 (obbligatoria 2025).

**Formula:** $Costo_{DX} = Experience\_Strategy + (\sum UJC \times Accessibility\_Factor)$

---

### SATELLITE 5: Quality Assurance (QA)
Il "giudice" umano che valida l'output della GenAI.

* **Verification Points (VP):** Punti di controllo su logica di business e contratti API.
* **Criticality Tier:** Moltiplicatore basato sull'impatto del fallimento (Tier 1 a Tier 3).
* **Performance/Load Test:** Servizio opzionale calcolato a "campagna di test".

**Formula:** $Costo_{QA} = Automation\_Setup + (\sum VP \times Tier\_Multiplier)$

---

## 4. Riepilogo Economico (Esempio Progetto)

In un preventivo basato su questo modello, la ripartizione del valore appare così:

| Voce | Incidenza Media | Driver di Valore |
| :--- | :--- | :--- |
| **Core (AI Assisted)** | 30-40% | Esecuzione rapida della logica. |
| **Satelliti Governance (PM/Arch)** | 25-30% | Garanzia di consegna e tenuta sistemica. |
| **Satelliti Qualità (QA/Cyber/DX)** | 30-40% | Riduzione del rischio e adozione utente. |