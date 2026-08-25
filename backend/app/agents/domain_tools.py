"""Domain tools available to agents via LLM tool calling.

Provider search hits the real CMS NPI Registry (see
app/integrations/npi_registry.py). Cost estimation and prior-auth checks go
through the pluggable EligibilityProvider (see app/integrations/eligibility.py)
— mock by default, a real clearinghouse once credentials are configured.
Every tool result carries a `data_source` field so downstream agents (and
ultimately the safety agent / frontend) can tell a member when a figure is
simulated rather than a real payer determination.
"""

from langchain_core.tools import tool

from app.integrations.eligibility import get_eligibility_provider
from app.integrations.npi_registry import search_providers


@tool
def search_in_network_providers(specialty: str, state: str) -> list[dict]:
    """Search for real, federally-registered providers by specialty and US state
    (two-letter code, e.g. 'NY'). Network status is not part of this data —
    call check_provider_network_status separately for a given provider's NPI."""
    try:
        return search_providers(taxonomy_description=specialty, state=state)
    except Exception as exc:  # NPI registry outage, bad state code, etc.
        return [{"error": f"Provider search unavailable: {exc}", "data_source": "error"}]


@tool
def check_provider_network_status(provider_npi: str, payer_name: str) -> dict:
    """Check whether a specific provider (by NPI) is in-network for a payer."""
    return get_eligibility_provider().check_network_status(provider_npi=provider_npi, payer_name=payer_name)


@tool
def estimate_procedure_cost(procedure_code: str, in_network: bool, deductible_remaining: float) -> dict:
    """Estimate out-of-pocket cost for a procedure given plan benefits."""
    return get_eligibility_provider().estimate_cost(
        procedure_code=procedure_code, in_network=in_network, deductible_remaining=deductible_remaining
    )


@tool
def check_prior_authorization_requirement(procedure_code: str, payer_name: str) -> dict:
    """Check whether a procedure requires prior authorization under a given payer."""
    return get_eligibility_provider().check_prior_authorization(procedure_code=procedure_code, payer_name=payer_name)
