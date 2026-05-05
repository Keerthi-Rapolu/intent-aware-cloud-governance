"""
Experiment baselines — swap-in replacements for the full PBCP pipeline.

Each module exposes:
    evaluate(intent: dict) -> SimulationResult
    evaluate_batch(intents: list[dict]) -> list[SimulationResult]

Baselines:
    static_provisioning  — no intervention (lower bound)
    rule_based_policies  — fixed rules, no EV/simulation
    no_phase3_frozen     — full PBCP but catalog priors only, no learning
"""