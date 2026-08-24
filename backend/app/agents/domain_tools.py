"""Domain tools available to agents via LLM tool calling.

These are deterministic mocks so the graph is runnable without live payer
integrations. Each function documents the real integration point it stands
in for (eligibility/benefits APIs, provider directories, fee schedules).
"""

from langchain_core.tools import tool

_MOCK_PROVIDERS = [
    {"name": "Dr. Elena Ross", "specialty": "Radiology", "network": "in-network", "distance_miles": 2.1, "next_available": "2026-08-27"},
    {"name": "Riverside Imaging Center", "specialty": "Radiology", "network": "in-network", "distance_miles": 4.6, "next_available": "2026-08-26"},
    {"name": "Downtown MRI & CT", "specialty": "Radiology", "network": "out-of-network", "distance_miles": 1.3, "next_available": "2026-08-25"},
]


@tool
def search_in_network_providers(specialty: str, zip_code: str) -> list[dict]:
    """Search for in-network providers by specialty near a ZIP code.

    In production this calls the payer's provider directory API (or an
    NPI registry cross-referenced against the member's plan network).
    """
    return [p for p in _MOCK_PROVIDERS if p["specialty"].lower() == specialty.lower()]


@tool
def estimate_procedure_cost(procedure_code: str, in_network: bool, deductible_remaining: float) -> dict:
    """Estimate out-of-pocket cost for a procedure given plan benefits.

    In production this calls the payer's real-time benefits/cost estimator
    (X12 270/271 eligibility transaction plus the member's accumulator data).
    """
    base_costs = {"MRI": 1200.0, "CT": 900.0, "XRAY": 250.0}
    base = next((v for k, v in base_costs.items() if k.lower() in procedure_code.lower()), 800.0)
    coinsurance_rate = 0.2 if in_network else 0.5
    patient_owes = min(base, deductible_remaining) + max(0, base - deductible_remaining) * coinsurance_rate
    return {
        "procedure_code": procedure_code,
        "estimated_total_cost": base,
        "estimated_patient_responsibility": round(patient_owes, 2),
        "in_network": in_network,
    }


@tool
def check_prior_authorization_requirement(procedure_code: str, payer_name: str) -> dict:
    """Check whether a procedure requires prior authorization under a given payer.

    In production this queries the payer's utilization management rules
    engine or published prior-auth code list.
    """
    requires_auth_codes = {"MRI", "CT", "SURGERY"}
    requires_auth = any(code in procedure_code.upper() for code in requires_auth_codes)
    return {
        "procedure_code": procedure_code,
        "payer_name": payer_name,
        "requires_prior_authorization": requires_auth,
        "estimated_turnaround_days": 3 if requires_auth else 0,
    }
