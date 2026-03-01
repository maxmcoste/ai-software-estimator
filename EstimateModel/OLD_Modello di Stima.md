# Modello di Stima Software "Core & Satellites" (V2 - Post-GenAI Era)

## 1. Strategia di Stima
Il modello scollega la produzione tecnica (Core) dalla governance e consulenza (Satelliti). La Business Analysis viene trattata sia come costo operativo del Core (Refinement) sia come valore aggiunto consulenziale (Satellite).

---

## 2. Il CORE (The Engine)
Include lo sviluppo e la preparazione tecnica del requisito.

* **Functional Complexity Units (FCU):** Misura della logica di business.
* **BA Refinement (Core Component):** +15% sul valore FCU. Copre la traduzione dei requisiti in prompt e specifiche per l'IA. È un'attività assistita da GenAI per la generazione di User Stories e Acceptance Criteria.
* **Formula Core:** $Stima\_Core = ((Base\_FCU + BA\_Refinement) \times Scalabilità) + Spike$

---

## 3. I SATELLITI (The Orbit)

### SATELLITE 1: Project Management & Orchestration (PM&O)
* **Metrica:** CBSU (Calendar-Based).
* **Stima:** FTE (0.2 - 1.0) x Mesi Progetto.

### SATELLITE 2: Dedicated Business Analysis (NEW)
Servizio richiesto per la gestione attiva degli stakeholder e la definizione dei processi.
* **Metrica:** **Consulting Units (CU)**.
* **Stima:** FTE dedicato (es. 0.5 o 1.0) x Durata.
* **Quando usarlo:** Se il cliente non ha requisiti pronti o richiede un presidio costante nei workshop.

### SATELLITE 3: Solution Architecture & Infra
* **Metrica:** ECU (Environment Complexity Units).
* **Include:** Design sistemico, IaC, FinOps e monitoraggio.

### SATELLITE 4: Cybersecurity & Compliance
* **Metrica:** Surface & Sensitivity (S2).
* **Include:** Audit, Security Gates per ogni release, conformità GDPR.

### SATELLITE 5: Digital Experience (DX)
* **Metrica:** User Journey Complexity (UJC).

### SATELLITE 6: Quality Assurance (QA)
* **Metrica:** Verification Points (VP).

---

## 4. Matrice di Responsabilità e AI-Impact

| Elemento | Impatto GenAI | Natura del Costo |
| :--- | :--- | :--- |
| **Core Coding** | Alto (Riduzione tempi) | Transazionale / FCU |
| **BA Refinement** | Medio (Accelerazione doc) | % del Core |
| **Dedicated BA** | Basso (Relazione umana) | FTE x Tempo |
| **Architecture** | Medio (Generazione IaC) | Per complessità di rete |
| **Cybersecurity** | Basso (Validazione umana) | Per livello di rischio |