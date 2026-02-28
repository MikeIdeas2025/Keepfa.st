"""Translation layer — converts analytics output to builder-friendly plain language."""


class TranslationLayer:
    """Translates Intelligence output dicts to plain language strings. No LLM — deterministic."""

    ITALIAN_STOP_WORDS = {
        "del",
        "dei",
        "come",
        "perché",
        "cosa",
        "quali",
        "degli",
        "della",
        "sono",
        "nelle",
        "nella",
    }

    def translate(
        self, analysis_type: str, data: dict, language: str = "auto", user_query: str = ""
    ) -> str:
        if language == "auto":
            language = self.detect_language(user_query) if user_query else "en"

        dispatch = {
            "cohort": self._translate_cohort,
            "funnel": self._translate_funnel,
            "trend": self._translate_trend,
            "segment": self._translate_segment,
            "anomaly": self._translate_anomaly,
            "omtm": self._translate_omtm,
            "health": self._translate_health,
            "journey": self._translate_journey,
            "clv": self._translate_clv,
        }

        handler = dispatch.get(analysis_type)
        if not handler:
            if language == "it":
                return f"Tipo di analisi '{analysis_type}' non riconosciuto."
            return f"Unknown analysis type '{analysis_type}'."

        return handler(data, language)

    def detect_language(self, text: str) -> str:
        words = set(text.lower().split())
        italian_matches = words & self.ITALIAN_STOP_WORDS
        if len(italian_matches) >= 2:
            return "it"
        return "en"

    # --- Cohort ---

    def _translate_cohort(self, data: dict, lang: str) -> str:
        if not data.get("cohorts"):
            return self._zero_data("cohort", lang)

        parts = [
            self._confidence_disclaimer(
                data.get("confidence", "low"), data.get("total_users", 0), lang
            )
        ]

        for cohort in data["cohorts"]:
            name = cohort["name"]
            size = cohort["size"]
            retention = cohort.get("retention", [])

            if len(retention) >= 2:
                m1_pct = retention[1]
                ratio = self._pct_to_ratio(m1_pct)
                if lang == "it":
                    parts.append(
                        f"{name} ({size} utenti): {ratio} è tornato il mese dopo ({m1_pct}%)."
                    )
                else:
                    parts.append(
                        f"{name} ({size} users): {ratio} came back the next month ({m1_pct}%)."
                    )
            else:
                if lang == "it":
                    parts.append(f"{name} ({size} utenti): non ho ancora dati sul mese successivo.")
                else:
                    parts.append(f"{name} ({size} users): not enough data for the next month yet.")

        # Trend summary
        trend = data.get("trend", "insufficient_data")
        if trend == "improving":
            if lang == "it":
                parts.append(
                    "\nBuone notizie: la tendenza sta migliorando. I gruppi recenti tornano di più."
                )
            else:
                parts.append(
                    "\nGood news: the trend is improving. Recent groups are coming back more."
                )
        elif trend == "declining":
            if lang == "it":
                parts.append("\nAttenzione: la tendenza è in calo. I gruppi recenti tornano meno.")
            else:
                parts.append(
                    "\nHeads up: the trend is declining. Recent groups are coming back less."
                )
        elif trend == "stable":
            if lang == "it":
                parts.append("\nLa tendenza è stabile — nessun cambiamento significativo.")
            else:
                parts.append("\nThe trend is stable — no significant change.")

        return "\n".join(p for p in parts if p)

    # --- Funnel ---

    def _translate_funnel(self, data: dict, lang: str) -> str:
        steps = data.get("steps", [])
        if not steps or all(s["count"] == 0 for s in steps):
            return self._zero_data("funnel", lang)

        parts = [
            self._confidence_disclaimer(data.get("confidence", "low"), steps[0]["count"], lang)
        ]

        if lang == "it":
            parts.append("Ecco come si muovono le persone nel tuo flusso:\n")
        else:
            parts.append("Here's how people move through your flow:\n")

        for step in steps:
            parts.append(f"  {step['name']}: {step['count']} users ({step['rate']}%)")

        biggest = data.get("biggest_drop")
        if biggest:
            lost = biggest["users_lost"]
            drop_rate = biggest["drop_rate"]
            from_step = biggest["from"]
            to_step = biggest["to"]
            if lang == "it":
                parts.append(
                    f"\nIl punto critico è tra '{from_step}' e '{to_step}': "
                    f"{lost} persone si fermano qui ({drop_rate}% di chi arriva)."
                )
            else:
                parts.append(
                    f"\nThe critical point is between '{from_step}' and '{to_step}': "
                    f"{lost} people stop here ({drop_rate}% of those who make it)."
                )

        conversion = data.get("overall_conversion", 0)
        if lang == "it":
            parts.append(f"\nConversione totale: {conversion}% arriva alla fine.")
        else:
            parts.append(f"\nOverall conversion: {conversion}% make it to the end.")

        return "\n".join(p for p in parts if p)

    # --- Trend ---

    def _translate_trend(self, data: dict, lang: str) -> str:
        if "error" in data:
            return data["error"]

        points = data.get("data_points", [])
        if not points:
            return self._zero_data("trend", lang)

        parts = [
            self._confidence_disclaimer(
                data.get("confidence", "low"), data.get("total_users", 0), lang
            )
        ]

        metric = data.get("metric", "metric")
        direction = data.get("direction", "stable")
        change = data.get("change_rate", 0)

        if direction == "growing":
            if lang == "it":
                parts.append(
                    f"'{metric}' sta crescendo (+{change}% rispetto al periodo precedente)."
                )
            else:
                parts.append(f"'{metric}' is growing (+{change}% compared to the previous period).")
        elif direction == "declining":
            if lang == "it":
                parts.append(f"'{metric}' è in calo ({change}% rispetto al periodo precedente).")
            else:
                parts.append(
                    f"'{metric}' is declining ({change}% compared to the previous period)."
                )
        else:
            if lang == "it":
                parts.append(f"'{metric}' è stabile ({change}% rispetto al periodo precedente).")
            else:
                parts.append(f"'{metric}' is stable ({change}% compared to the previous period).")

        # Recent data points
        recent = points[-3:] if len(points) >= 3 else points
        if lang == "it":
            parts.append("\nUltimi periodi:")
        else:
            parts.append("\nRecent periods:")
        for dp in recent:
            parts.append(f"  {dp['period']}: {dp['value']}")

        # Anomalies
        anomalies = data.get("anomalies", [])
        if anomalies:
            if lang == "it":
                parts.append("\nHo notato qualcosa di insolito:")
            else:
                parts.append("\nI noticed something unusual:")
            for a in anomalies:
                if lang == "it":
                    sev = a["severity"]
                    sev_it = {"mild": "lieve", "notable": "importante"}.get(sev, "significativo")
                    parts.append(
                        f"  {a['period']}: mi aspettavo ~{a['expected']}, "
                        f"ma il valore reale è {a['actual']} ({sev_it})"
                    )
                else:
                    parts.append(
                        f"  {a['period']}: expected ~{a['expected']}, "
                        f"actual was {a['actual']} ({a['severity']})"
                    )

        return "\n".join(p for p in parts if p)

    # --- Segment ---

    def _translate_segment(self, data: dict, lang: str) -> str:
        seg_a = data.get("segment_a", {})
        seg_b = data.get("segment_b", {})

        if seg_a.get("size", 0) == 0 and seg_b.get("size", 0) == 0:
            return self._zero_data("segment", lang)

        parts = [
            self._confidence_disclaimer(
                data.get("confidence", "low"),
                min(seg_a.get("size", 0), seg_b.get("size", 0)),
                lang,
            )
        ]

        winner = data.get("winner", "")
        diff = data.get("difference", 0)

        if lang == "it":
            parts.append(
                f"'{seg_a['name']}' ({seg_a['size']} utenti): {seg_a['metric_value']}\n"
                f"'{seg_b['name']}' ({seg_b['size']} utenti): {seg_b['metric_value']}"
            )
            parts.append(f"\n'{winner}' è in vantaggio di {diff} punti.")
        else:
            parts.append(
                f"'{seg_a['name']}' ({seg_a['size']} users): {seg_a['metric_value']}\n"
                f"'{seg_b['name']}' ({seg_b['size']} users): {seg_b['metric_value']}"
            )
            parts.append(f"\n'{winner}' is ahead by {diff} points.")

        if not data.get("statistically_significant", False):
            if lang == "it":
                parts.append(
                    "Nota: i numeri sono troppo piccoli per essere certi di questa differenza."
                )
            else:
                parts.append(
                    "Note: the numbers are too small to be confident about this difference."
                )

        return "\n".join(p for p in parts if p)

    # --- Anomaly (standalone) ---

    def _translate_anomaly(self, data: dict, lang: str) -> str:
        anomalies = data.get("anomalies", [])
        if not anomalies:
            if lang == "it":
                return "Non ho trovato nulla di insolito nei tuoi dati. Tutto nella norma."
            return "I didn't find anything unusual in your data. Everything looks normal."

        parts = []
        if lang == "it":
            parts.append("Ho trovato dei cambiamenti insoliti:\n")
        else:
            parts.append("I found some unusual changes:\n")

        for a in anomalies:
            period = a["period"]
            actual = a["actual"]
            expected = a["expected"]
            if lang == "it":
                sev_map = {"mild": "lieve", "notable": "importante", "severe": "significativo"}
                sev = sev_map.get(a["severity"], a["severity"])
                parts.append(
                    f"  {period}: il valore ({actual}) "
                    f"è diverso da quello atteso (~{expected}). "
                    f"Cambiamento {sev}."
                )
            else:
                parts.append(
                    f"  {period}: the value ({actual}) "
                    f"differs from expected (~{expected}). "
                    f"{a['severity'].capitalize()} change."
                )

        return "\n".join(parts)

    # --- OMTM ---

    def _translate_omtm(self, data: dict, lang: str) -> str:
        metric = data.get("suggested_metric", "")
        current = data.get("current_value", 0)
        target = data.get("target_value", 0)
        reasoning = data.get("reasoning", "")

        if lang == "it":
            parts = [
                "Il numero su cui dovresti concentrarti adesso:\n",
                f"  Metrica: {self._metric_plain_name(metric, 'it')}",
                f"  Valore attuale: {current}",
                f"  Obiettivo: {target}",
                f"\nPerché: {reasoning}",
            ]
        else:
            parts = [
                "The one number you should focus on right now:\n",
                f"  Metric: {self._metric_plain_name(metric, 'en')}",
                f"  Current value: {current}",
                f"  Target: {target}",
                f"\nWhy: {reasoning}",
            ]

        return "\n".join(parts)

    # --- Health ---

    def _translate_health(self, data: dict, lang: str) -> str:
        summary = data.get("summary", {})
        customers = data.get("customers", [])

        if summary.get("total", 0) == 0:
            return self._zero_data("cohort", lang)

        parts = [self._confidence_disclaimer(data.get("confidence", "low"), summary["total"], lang)]

        healthy = summary.get("healthy", 0)
        at_risk = summary.get("at_risk", 0)
        critical = summary.get("critical", 0)
        total = summary.get("total", 0)
        mrr_at_risk = summary.get("total_mrr_at_risk", 0)

        if lang == "it":
            parts.append(f"Ho controllato la salute dei tuoi {total} clienti:\n")
            parts.append(f"  In salute: {healthy}")
            parts.append(f"  A rischio: {at_risk}")
            parts.append(f"  Critici: {critical}")
            if mrr_at_risk > 0:
                parts.append(
                    f"\nStai rischiando di perdere ${mrr_at_risk / 100:.0f}/mese "
                    "dai clienti a rischio e critici."
                )
        else:
            parts.append(f"I checked the health of your {total} customers:\n")
            parts.append(f"  Healthy: {healthy}")
            parts.append(f"  At risk: {at_risk}")
            parts.append(f"  Critical: {critical}")
            if mrr_at_risk > 0:
                parts.append(
                    f"\nYou're at risk of losing ${mrr_at_risk / 100:.0f}/month "
                    "from at-risk and critical customers."
                )

        top_factors = data.get("top_risk_factors", [])
        if top_factors:
            if lang == "it":
                parts.append("\nI problemi principali:")
            else:
                parts.append("\nTop issues:")
            for factor in top_factors[:3]:
                parts.append(f"  - {factor}")

        # Show critical customers
        critical_customers = [c for c in customers if c["risk_level"] == "critical"]
        if critical_customers:
            if lang == "it":
                parts.append("\nClienti che hanno bisogno di attenzione immediata:")
            else:
                parts.append("\nCustomers that need immediate attention:")
            for c in critical_customers[:5]:
                email = c["email"] or "unknown"
                if lang == "it":
                    parts.append(f"  - {email} (punteggio: {c['health_score']}/100)")
                else:
                    parts.append(f"  - {email} (score: {c['health_score']}/100)")

        return "\n".join(p for p in parts if p)

    # --- Journey ---

    def _translate_journey(self, data: dict, lang: str) -> str:
        distribution = data.get("phase_distribution", [])
        total = sum(p["count"] for p in distribution)

        if total == 0:
            return self._zero_data("cohort", lang)

        parts = [self._confidence_disclaimer(data.get("confidence", "low"), total, lang)]

        if lang == "it":
            parts.append(f"Ecco dove si trovano i tuoi {total} clienti nel loro percorso:\n")
        else:
            parts.append(f"Here's where your {total} customers are in their journey:\n")

        for phase in distribution:
            if phase["count"] > 0:
                parts.append(f"  {phase['phase']}: {phase['count']} ({phase['pct']}%)")

        bottleneck = data.get("bottleneck")
        if bottleneck:
            if lang == "it":
                parts.append(
                    f"\nIl punto critico: tra '{bottleneck['from']}' e '{bottleneck['to']}' "
                    f"perdi il {bottleneck['drop_pct']}% delle persone."
                )
            else:
                parts.append(
                    f"\nThe critical point: between '{bottleneck['from']}' and "
                    f"'{bottleneck['to']}' you lose {bottleneck['drop_pct']}% of people."
                )

        first_100 = data.get("first_100_days", {})
        if first_100.get("users_in_window", 0) > 0:
            if lang == "it":
                parts.append(
                    f"\nPrimi 100 giorni: {first_100['users_in_window']} utenti, "
                    f"fase media '{first_100['avg_phase']}', "
                    f"{first_100['completion_rate']}% raggiunge la fase Adopt."
                )
            else:
                parts.append(
                    f"\nFirst 100 days: {first_100['users_in_window']} users, "
                    f"average phase '{first_100['avg_phase']}', "
                    f"{first_100['completion_rate']}% reach the Adopt phase."
                )

        return "\n".join(p for p in parts if p)

    # --- CLV ---

    def _translate_clv(self, data: dict, lang: str) -> str:
        customers = data.get("customers", [])
        segments = data.get("segments", {})
        total_clv = data.get("total_portfolio_clv", 0)

        if not customers:
            return self._zero_data("subscription", lang)

        parts = [self._confidence_disclaimer(data.get("confidence", "low"), len(customers), lang)]

        if lang == "it":
            parts.append(
                f"Ecco quanto vale ogni cliente per il tuo business "
                f"(valore totale del portfolio: ${total_clv:.0f}):\n"
            )
        else:
            parts.append(
                f"Here's what each customer is worth to your business "
                f"(total portfolio value: ${total_clv:.0f}):\n"
            )

        # Segment summary
        for seg_name in ["Champions", "Advocates", "Affluents", "Misers"]:
            seg = segments.get(seg_name, {})
            if seg.get("count", 0) > 0:
                if lang == "it":
                    parts.append(
                        f"  {seg_name}: {seg['count']} clienti "
                        f"(valore medio: ${seg['avg_clv']:.0f})"
                    )
                else:
                    parts.append(
                        f"  {seg_name}: {seg['count']} customers (avg value: ${seg['avg_clv']:.0f})"
                    )

        # Top customers
        sorted_customers = sorted(customers, key=lambda c: c["clv"], reverse=True)
        top = sorted_customers[:3]
        if top and any(c["clv"] > 0 for c in top):
            if lang == "it":
                parts.append("\nI tuoi clienti di maggior valore:")
            else:
                parts.append("\nYour most valuable customers:")
            for c in top:
                if c["clv"] > 0:
                    email = c["email"] or "unknown"
                    parts.append(f"  - {email}: ${c['clv']:.0f} (${c['mrr']:.0f}/month)")

        # Loyalty plan
        loyalty_plan = data.get("loyalty_plan", [])
        if loyalty_plan:
            if lang == "it":
                parts.append("\nPiano d'azione:")
            else:
                parts.append("\nAction plan:")
            for step in loyalty_plan:
                parts.append(f"  {step}")

        return "\n".join(p for p in parts if p)

    # --- Helpers ---

    def _pct_to_ratio(self, pct: int) -> str:
        if pct <= 0:
            return "nobody"
        if pct >= 100:
            return "everyone"
        if pct <= 12:
            return "about 1 in 10"
        if pct <= 18:
            return "about 1 in 7"
        if pct <= 22:
            return "about 1 in 5"
        if pct <= 28:
            return "about 1 in 4"
        if pct <= 38:
            return "about 1 in 3"
        if pct <= 45:
            return "about 2 in 5"
        if pct <= 55:
            return "about 1 in 2"
        if pct <= 65:
            return "about 3 in 5"
        if pct <= 78:
            return "about 3 in 4"
        return "most"

    def _confidence_disclaimer(self, confidence: str, n: int, lang: str) -> str:
        if confidence == "high":
            return ""
        if confidence == "low":
            if lang == "it":
                return (
                    f"Attenzione: sto lavorando con pochissimi dati ({n} utenti). "
                    f"Prendilo come un segnale indicativo, non una risposta definitiva.\n"
                )
            return (
                f"Heads up: I'm working with very little data ({n} users). "
                f"Take this as a rough signal, not a firm answer.\n"
            )
        # medium
        if lang == "it":
            return (
                "Ho abbastanza dati per individuare dei pattern, "
                "ma non abbastanza per una certezza statistica.\n"
            )
        return (
            "I have enough data to spot patterns, but not enough for full statistical confidence.\n"
        )

    def _zero_data(self, analysis_type: str, lang: str) -> str:
        templates = {
            "cohort": {
                "en": (
                    "I don't have any event data yet. To analyze how many users come back, "
                    "I need at least a few weeks of usage data. Start tracking key events "
                    "like signups, logins, and feature usage."
                ),
                "it": (
                    "Non ho ancora dati sugli eventi. Per analizzare quanti utenti tornano, "
                    "ho bisogno di almeno qualche settimana di dati di utilizzo. Inizia a "
                    "tracciare eventi chiave come registrazioni, login e utilizzo funzionalità."
                ),
            },
            "funnel": {
                "en": (
                    "I don't have any event data for this flow yet. Make sure you're tracking "
                    "the events that match the steps you defined."
                ),
                "it": (
                    "Non ho ancora dati sugli eventi per questo flusso. Assicurati di tracciare "
                    "gli eventi che corrispondono ai passaggi che hai definito."
                ),
            },
            "trend": {
                "en": (
                    "I don't have enough data points to show a trend yet. "
                    "I need at least a couple of weeks of data."
                ),
                "it": (
                    "Non ho ancora abbastanza dati per mostrare un trend. "
                    "Ho bisogno di almeno un paio di settimane di dati."
                ),
            },
            "segment": {
                "en": (
                    "I don't have any users in these segments yet. "
                    "Make sure your data sources are connected and users have activity."
                ),
                "it": (
                    "Non ho ancora utenti in questi segmenti. Assicurati che le sorgenti "
                    "dati siano collegate e che gli utenti abbiano attività."
                ),
            },
            "subscription": {
                "en": (
                    "No subscriptions found yet. When your first users subscribe, "
                    "I'll be able to tell you about revenue metrics."
                ),
                "it": (
                    "Nessun abbonamento trovato. Quando i primi utenti si abboneranno, "
                    "potrò dirti le metriche di ricavo."
                ),
            },
            "matching": {
                "en": (
                    "I couldn't match any PostHog users to Stripe customers. "
                    "Check that users have the same email in both systems."
                ),
                "it": (
                    "Non sono riuscito ad abbinare utenti PostHog con clienti Stripe. "
                    "Verifica che gli utenti abbiano la stessa email in entrambi i sistemi."
                ),
            },
        }

        t = templates.get(analysis_type, templates.get("cohort", {}))
        return t.get(lang, t.get("en", "No data available."))

    def _metric_plain_name(self, metric: str, lang: str) -> str:
        names = {
            "new_users_per_week": {"en": "New users per week", "it": "Nuovi utenti a settimana"},
            "onboarding_completion_rate": {
                "en": "Onboarding completion rate",
                "it": "Tasso di completamento onboarding",
            },
            "week_1_retention": {
                "en": "Do people come back after the first week?",
                "it": "Le persone tornano dopo la prima settimana?",
            },
            "trial_to_paid_conversion": {
                "en": "Free to paid conversion",
                "it": "Conversione da gratuito a pagamento",
            },
            "referral_rate": {"en": "Referral rate", "it": "Tasso di referral"},
        }
        entry = names.get(metric, {})
        return entry.get(lang, metric.replace("_", " "))
