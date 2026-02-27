# CLAUDE.md — Keepfa.st

## Cos'è questo progetto

Keepfa.st è un AI retention analyst distribuito come MCP server (Model Context Protocol). Si collega a PostHog + Stripe, normalizza i dati, e espone 5 tool che permettono ai builder di fare domande sulla retention del loro SaaS in linguaggio naturale — direttamente dentro Cursor o Claude.

**In una frase:** Il PM on-demand per chi sa buildare ma non sa misurare.

**Tagline:** Tu buildi. L'AI legge. Tu decidi. L'AI misura.

---

## Per chi è

### ICP Primario: Vibecoder
Builder nato dalla wave Cursor/Bolt/Lovable/Replit Agent. 12 mesi fa non aveva mai scritto codice, oggi ha un SaaS live. Sa promptare un prodotto in esistenza ma non ha idea di cosa sia una cohort o perché il churn al 15% mensile lo sta uccidendo. Per lui "analytics" significa guardare il numero di utenti su Stripe e sperare che salga.

### ICP Secondario: Founder dev-first
Sa scrivere codice, shippa veloce, ha un prodotto live con utenti paganti. Quando apre Mixpanel non sa cosa guardare. Confonde vanity metrics con segnali reali. Non ha studiato Lean Analytics e non ha intenzione di farlo. Vuole risposte, non dashboard.

### Denominatore comune
Sanno buildare, non sanno leggere. Questo prodotto NON è per PM esperti che vogliono un tool migliore. È per chi non ha mai avuto un PM e ne ha bisogno senza saperlo.

---

## Principi di prodotto

### ODA Loop (Observe → Decide → Act)
Ogni interazione segue questo ciclo:
- **OBSERVE:** L'AI raccoglie, normalizza e presenta i dati in linguaggio semplice
- **DECIDE:** L'AI propone insight e azioni. L'umano valida e sceglie
- **ACT:** L'umano conferma, l'AI esegue la misurazione e traccia l'impatto

### Human-in-the-Loop (HITL)
L'AI NON agisce MAI autonomamente. Ogni decisione richiede conferma umana. Questo è sia un principio etico che un selling point. L'AI non tocca il prodotto dell'utente senza approvazione esplicita.

### Translation Layer (differenziatore CRITICO)
L'AI NON parla MAI in gergo analytics. Traduce la retention science in linguaggio da builder.
- ❌ "La tua cohort retention M1 è al 34%"
- ✅ "Dei tuoi utenti del mese scorso, solo 1 su 3 è tornato — e il motivo principale è questo."
- ❌ "Il tuo OMTM dovrebbe shiftare sulla Day 7 retention"
- ✅ "La cosa che conta di più adesso è: le persone tornano dopo la prima settimana?"

---

## Architettura

### Stack tecnologico
- **Linguaggio:** Python
- **Framework MCP:** FastMCP
- **Sorgenti dati (MVP):** PostHog API + Stripe API
- **Sorgenti future:** Supabase, Vercel Analytics
- **Nessuna web dashboard nella v1** — il builder vive in Cursor, incontralo lì

### Componenti

```
keepfast/
├── CLAUDE.md                  # Questo file
├── README.md                  # Guida setup per vibecoder (< 5 min installazione)
├── pyproject.toml             # Configurazione progetto
├── src/
│   ├── server.py              # Entry point FastMCP server
│   ├── auth/
│   │   ├── __init__.py
│   │   └── manager.py         # Gestione API key per PostHog + Stripe
│   ├── connectors/
│   │   ├── __init__.py
│   │   ├── posthog.py         # Connector PostHog API (eventi, persone, insight)
│   │   └── stripe.py          # Connector Stripe API (subscription, clienti, fatture)
│   ├── normalizer/
│   │   ├── __init__.py
│   │   ├── schema.py          # Schema dati unificato (utenti, eventi, metriche)
│   │   ├── mapper.py          # Mapping user_id cross-piattaforma (Stripe ↔ PostHog)
│   │   └── cleaner.py         # Gestione dati sporchi (no naming convention, eventi caotici)
│   ├── intelligence/
│   │   ├── __init__.py
│   │   ├── cohort.py          # Calcolo retention per cohort
│   │   ├── funnel.py          # Analisi funnel + rilevamento drop-off
│   │   ├── trends.py          # Trend metriche + rilevamento anomalie
│   │   ├── segments.py        # Confronto segmenti
│   │   └── omtm.py            # Selezione OMTM (One Metric That Matters) per stage
│   ├── translation/
│   │   ├── __init__.py
│   │   └── plain_language.py  # Converte output analytics → linguaggio da builder
│   └── tools/
│       ├── __init__.py
│       ├── get_cohort_retention.py
│       ├── get_funnel_analysis.py
│       ├── get_metric_trend.py
│       ├── compare_segments.py
│       └── get_anomalies.py
└── tests/
    ├── test_connectors.py
    ├── test_normalizer.py
    ├── test_intelligence.py
    ├── test_translation.py
    └── fixtures/               # Dati di esempio PostHog + Stripe per testing
        ├── posthog_events.json
        └── stripe_subscriptions.json
```

### MCP Tool (5 totali per MVP)

```python
@mcp.tool()
def get_cohort_retention(cohort: str, period: str) -> str:
    """
    Analizza la retention per una cohort specifica.
    Ritorna spiegazione in linguaggio semplice di quanti utenti sono tornati
    e perché alcuni non lo hanno fatto.
    """

@mcp.tool()
def get_funnel_analysis(funnel_name: str, date_range: str) -> str:
    """
    Identifica dove gli utenti abbandonano in un funnel specifico.
    Ritorna il bottleneck principale e il fix suggerito.
    """

@mcp.tool()
def get_metric_trend(metric: str, granularity: str) -> str:
    """
    Mostra il trend di qualsiasi metrica con segnalazione anomalie.
    Ritorna se le cose stanno migliorando o peggiorando e perché.
    """

@mcp.tool()
def compare_segments(segment_a: str, segment_b: str, metric: str) -> str:
    """
    Confronta due segmenti di utenti su una metrica specifica.
    Ritorna quale segmento performa meglio e cosa guida la differenza.
    """

@mcp.tool()
def get_anomalies(metric: str, threshold: float) -> str:
    """
    Rileva pattern insoliti in qualsiasi metrica.
    Ritorna cosa è cambiato, quando, e la causa probabile.
    """
```

### Flusso dati

```
PostHog API ──→ ┐
                 ├──→ Normalizer ──→ Intelligence ──→ Translation ──→ Risposta MCP Tool
Stripe API  ──→ ┘         │                │                │
                           │                │                │
                      HITL: "Ho trovato    HITL: "Ti        HITL: "Vuoi
                      14 eventi.           suggerisco X.    che te lo
                      Questi 3 sono        Sei d'accordo?"  spieghi più
                      dell'onboarding.                      semplice?"
                      Confermi?"
```

---

## Edge case da gestire

### Qualità dati (CRITICO per il target vibecoder)
- **Nessuna naming convention:** I vibecoder non hanno un tracking plan. Gli eventi possono chiamarsi qualsiasi cosa. Il normalizer deve dare senso a dati caotici.
- **Mismatch user_id:** Stripe customer ID ≠ PostHog distinct_id. Il mapper deve usare l'email come chiave di fallback.
- **Zero eventi:** SaaS appena lanciato, PostHog ha 0 eventi. Non crashare — rispondi "Non ho ancora abbastanza dati. Ecco cosa iniziare a tracciare."
- **Zero subscription:** Stripe collegato ma nessun utente pagante. Suggerisci cosa monitorare per quando arriveranno.
- **Dati sparsi:** < 30 utenti rende l'analisi statistica inaffidabile. Usa euristiche, non statistica. Sii trasparente sul livello di confidenza.

### Limiti API
- PostHog: 240 richieste/min. Cache aggressiva.
- Stripe: 100 richieste/sec (generoso). Cache comunque per query ripetute.

### Edge case traduzione
- Se l'utente non capisce la versione in linguaggio semplice, offri di semplificare ulteriormente
- Se l'utente chiede in italiano, rispondi in italiano. Se in inglese, rispondi in inglese. Auto-detect.
- Non usare MAI: "cohort", "OMTM", "retention curve", "churn rate" senza spiegare immediatamente in parole semplici

---

## Cosa NON buildare (scope MVP)

- ❌ Niente grafici o visualizzazioni — solo testo. Il builder ha bisogno di una frase, non di una curva.
- ❌ Niente web dashboard — il builder vive in Cursor. Incontralo lì.
- ❌ Niente connector Intercom/support — due sorgenti bastano per il primo ciclo ODA.
- ❌ Niente modello ML custom — usa euristiche semplici (nessun login da X giorni → a rischio). Il ML viene dopo con dati reali.
- ❌ Niente sistema di alert/push automatico — nella v1, l'utente chiede. Aggiungi push quando sai cosa vale la pena segnalare.
- ❌ Niente multi-tenant/team — solo founder singolo.
- ❌ Niente billing/pagamento — gratis durante la beta, monetizza dopo validazione.

**Test di semplificazione:** "Se tolgo questo, il builder riceve comunque la risposta a 'perché il mio prodotto non cresce?'" Se sì, toglilo.

---

## Metriche di successo

### Per l'utente
- **Time-to-insight:** Da 3 ore/settimana di data archaeology a < 2 minuti per query
- **Action rate:** > 50% degli insight suggeriti portano a un'azione concreta entro 7 giorni
- **Comprensione:** Un non-PM capisce l'output senza spiegazioni aggiuntive

### Per il prodotto
- **Tempo di setup:** Il vibecoder installa e fa la prima query utile in < 5 minuti
- **Beta NPS:** > 40 tra i beta tester
- **Validazione:** 7+ su 10 beta tester dicono "questo mi ha detto qualcosa che non sapevo"
- **WTP:** 5+ su 10 confermano willingness-to-pay > €0. Almeno 3 sopra €30/mese.

---

## Roadmap builder

### Fase 0: Foundation (Settimana 1-2)
- Giorno 1-2: Scaffold FastMCP + auth manager per API key PostHog + Stripe
- Giorno 3-4: Data fetcher — pull subscription da Stripe, eventi da PostHog. Caching.
- Giorno 5-7: Normalizer — schema unificato, mapping user_id cross-piattaforma, gestione dati sporchi
- Giorno 8-10: Primo tool (get_cohort_retention) con translation layer

### Fase 1: Core Tool (Settimana 3-4)
- Giorno 11-12: get_funnel_analysis
- Giorno 13-14: get_metric_trend con segnalazione anomalie
- Giorno 15-16: compare_segments + get_anomalies
- Giorno 17-18: README, guida setup, video Loom di 3 minuti. Installabile in 5 minuti.

### Fase 2: Beta + Validazione (Settimana 5-8)
- Settimana 5: Recluta 10-15 beta tester dalla rete X + Product Heroes + Birra&Build
- Settimana 6: Onboarding 1:1 con ogni tester. Osserva setup + prima query. Raccogli friction.
- Settimana 7: Itera sul feedback. Fix translation layer. Migliora edge case.
- Settimana 8: Test willingness-to-pay con metodologia Mom Test.

### Fase 3: Monetizzazione (Mese 3-6)
- Mese 3: Lancio servizio productized "AI Retention Analyst" via Birra&Build AaaS (€500-2000/mese)
- Mese 4: Release open source del core MCP. Blog post + thread X. Authority play.
- Mese 5: Versione hosted light per chi non usa Cursor. €29-99/mese self-serve.
- Mese 6: Decision point — scala self-serve o raddoppia su servizio productized in base a dati reali.

---

## Assunzioni critiche da validare (in ordine)

| # | Assunzione | Come validarla | Kill criteria |
|---|-----------|----------------|---------------|
| 1 | I vibecoder hanno PostHog + Stripe installati | Survey a 20 vibecoder su X | < 30% usa PostHog → cambia connector prioritario |
| 2 | L'output in linguaggio semplice è più utile di un dashboard | A/B qualitativo: mostra stesso dato in gergo vs plain a 10 builder | La versione plain non genera più azioni → il translation layer non è il moat |
| 3 | I builder agiscono sugli insight (non li ignorano) | Traccia action rate in beta: quanti insight portano a un cambio nel prodotto entro 7 giorni | Action rate < 20% → gli insight non sono abbastanza azionabili |
| 4 | Esiste willingness-to-pay | Mom Test dopo 2 settimane di uso | < 3/10 indicano WTP > €0 → il modello SaaS non regge, pivota su servizio |

**Principio: valida l'assunzione più rischiosa per prima.** Se i vibecoder non usano PostHog, tutto il resto crolla. Parti da lì.

---

## Posizionamento competitivo

Keepfa.st NON compete con Amplitude/Mixpanel/PostHog. Quelli sono tool di raccolta dati. Keepfa.st è il layer di interpretazione che li rende utili per chi non sa di analytics.

I veri competitor:
- **Il nulla** — la maggior parte dei vibecoder non tracka niente. Opportunità di creare una categoria.
- **PostHog free tier** — si iscrivono, configurano 2 eventi, si perdono nei dashboard, lo abbandonano dopo una settimana.
- **ChatGPT + export CSV** — manuale, senza contesto, senza memoria, senza loop.
- **Twitter/community** — consigli generici, non basati sui TUOI dati.

**Il moat di Keepfa.st:** il translation layer. Chiunque può buildare connettori PostHog + Stripe. Nessuno sta costruendo il layer "spiegamelo come se fossi un builder, non un PM."

---

## Contesto per le sessioni Claude Code

Quando lavori su questo progetto nel terminale:
- Segui sempre il pattern ODA + HITL nel design dei tool
- Ogni output dei tool deve passare dal translation layer — non restituire MAI gergo analytics grezzo
- Testa prima con dati sporchi/minimi — è quello che avranno i vibecoder reali
- Mantieni le funzioni piccole e a singola responsabilità
- Se il nome di una funzione ha bisogno di "e" dentro, sta facendo troppo
- Il README deve essere comprensibile da qualcuno che non ha mai sentito parlare di "cohort retention"
- Supporto italiano e inglese nel translation layer — auto-detect dalla lingua dell'input utente
- Quando hai dubbi, semplifica. Il test MVP: "questo aiuta il builder a sapere cosa fixare oggi?"

---

## Owner del progetto

Michele Laurelli — Fractional Product & Growth Strategist
- 6+ anni come PM con esattamente questo problema di retention
- Community Manager in Product Heroes (700+ PM italiani)
- Co-founder Birra&Build (podcast + Agency-as-a-Service)
- Building in public su X @MicLau93
- Base: Roma, Italia
