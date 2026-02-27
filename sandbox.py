"""Sandbox — run all 3 skills with fixture data, no API keys needed."""

from keepfast.intelligence.clv import CLVAnalyzer
from keepfast.intelligence.health import CustomerHealthAnalyzer
from keepfast.intelligence.journey import JourneyOrchestrator
from keepfast.pipeline import DataPipeline
from keepfast.translation.plain_language import TranslationLayer
from tests.stubs import FakePostHogConnector, FakeStripeConnector


def main():
    # Build pipeline with fake connectors (fixture JSON data)
    pipeline = DataPipeline(FakePostHogConnector(), FakeStripeConnector())
    data = pipeline.fetch_and_normalize()
    translator = TranslationLayer()

    print(f"Loaded: {len(data.users)} users, {len(data.events)} events, "
          f"{len(data.subscriptions)} subscriptions\n")
    print("=" * 60)

    # 1. Health Check
    print("\n--- CUSTOMER HEALTH DIAGNOSTICIAN ---\n")
    health = CustomerHealthAnalyzer().diagnose(data.users, data.events, data.subscriptions)
    print(translator.translate("health", health, "en"))

    print("\n" + "=" * 60)

    # 2. Journey Map
    print("\n--- RETENTION JOURNEY ORCHESTRATOR ---\n")
    journey = JourneyOrchestrator().map_journey(data.users, data.events, data.subscriptions)
    print(translator.translate("journey", journey, "en"))

    print("\n" + "=" * 60)

    # 3. Customer Value
    print("\n--- LUCRATIVE LOYAL STRATEGIST ---\n")
    clv = CLVAnalyzer().analyze(data.users, data.events, data.subscriptions)
    print(translator.translate("clv", clv, "en"))

    print("\n" + "=" * 60)

    # Bonus: same in Italian
    print("\n--- VERSIONE ITALIANA (Health Check) ---\n")
    print(translator.translate("health", health, "it"))


if __name__ == "__main__":
    main()
