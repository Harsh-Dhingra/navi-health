"""Payer eligibility, cost estimation, and prior-authorization lookups.

Real-time benefit/eligibility data (network status, accumulator-aware cost
estimates, prior-auth requirements) comes from a payer or a clearinghouse
(Availity, Change Healthcare/Optum, etc.) via a contracted, credentialed
integration — there is no public self-serve API for this, unlike the NPI
registry. `MockEligibilityProvider` is the default so the product is usable
in demos/pilots without a signed contract, but every result it returns is
tagged `data_source: "simulated"` so callers (the safety agent, the
frontend) can surface an honest disclaimer instead of presenting fabricated
coverage or cost figures as real to an actual member making a real
healthcare decision.

Swap to a real provider once you have clearinghouse credentials by setting
ELIGIBILITY_PROVIDER=availity and the associated API key/base URL — no
change to the agent graph or tools is required, since both providers speak
the same `EligibilityProvider` interface.
"""

from abc import ABC, abstractmethod

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import get_settings


class EligibilityProvider(ABC):
    @abstractmethod
    def check_network_status(self, *, provider_npi: str, payer_name: str) -> dict: ...

    @abstractmethod
    def estimate_cost(self, *, procedure_code: str, in_network: bool, deductible_remaining: float) -> dict: ...

    @abstractmethod
    def check_prior_authorization(self, *, procedure_code: str, payer_name: str) -> dict: ...


class MockEligibilityProvider(EligibilityProvider):
    """Deterministic simulated responses. Every result is explicitly tagged
    so it is never mistaken for a real coverage or cost determination."""

    def check_network_status(self, *, provider_npi: str, payer_name: str) -> dict:
        in_network = int(provider_npi[-1]) % 2 == 0 if provider_npi.isdigit() else True
        return {"provider_npi": provider_npi, "payer_name": payer_name, "in_network": in_network, "data_source": "simulated"}

    def estimate_cost(self, *, procedure_code: str, in_network: bool, deductible_remaining: float) -> dict:
        base_costs = {"MRI": 1200.0, "CT": 900.0, "XRAY": 250.0}
        base = next((v for k, v in base_costs.items() if k.lower() in procedure_code.lower()), 800.0)
        coinsurance_rate = 0.2 if in_network else 0.5
        patient_owes = min(base, deductible_remaining) + max(0, base - deductible_remaining) * coinsurance_rate
        return {
            "procedure_code": procedure_code,
            "estimated_total_cost": base,
            "estimated_patient_responsibility": round(patient_owes, 2),
            "in_network": in_network,
            "data_source": "simulated",
        }

    def check_prior_authorization(self, *, procedure_code: str, payer_name: str) -> dict:
        requires_auth_codes = {"MRI", "CT", "SURGERY"}
        requires_auth = any(code in procedure_code.upper() for code in requires_auth_codes)
        return {
            "procedure_code": procedure_code,
            "payer_name": payer_name,
            "requires_prior_authorization": requires_auth,
            "estimated_turnaround_days": 3 if requires_auth else 0,
            "data_source": "simulated",
        }


class AvailityEligibilityProvider(EligibilityProvider):
    """Scaffold for a real Availity (or equivalent clearinghouse) integration.

    Requires AVAILITY_API_KEY / AVAILITY_API_BASE_URL, obtained by enrolling
    as a trading partner — not a self-serve signup. Endpoint paths below are
    illustrative; confirm against your clearinghouse's current API contract
    before relying on this in production.
    """

    def __init__(self):
        settings = get_settings()
        if not settings.availity_api_key:
            raise RuntimeError(
                "ELIGIBILITY_PROVIDER=availity requires AVAILITY_API_KEY. "
                "Enroll as an Availity trading partner to obtain credentials, "
                "or set ELIGIBILITY_PROVIDER=mock for demo/pilot use."
            )
        self._base_url = settings.availity_api_base_url
        self._client = httpx.Client(
            base_url=self._base_url,
            headers={"Authorization": f"Bearer {settings.availity_api_key}"},
            timeout=15.0,
        )

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=0.5, min=0.5, max=4))
    def check_network_status(self, *, provider_npi: str, payer_name: str) -> dict:
        response = self._client.get("/v1/provider-network-status", params={"npi": provider_npi, "payer": payer_name})
        response.raise_for_status()
        return {**response.json(), "data_source": "availity"}

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=0.5, min=0.5, max=4))
    def estimate_cost(self, *, procedure_code: str, in_network: bool, deductible_remaining: float) -> dict:
        response = self._client.post(
            "/v1/cost-estimate",
            json={"procedure_code": procedure_code, "in_network": in_network, "deductible_remaining": deductible_remaining},
        )
        response.raise_for_status()
        return {**response.json(), "data_source": "availity"}

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=0.5, min=0.5, max=4))
    def check_prior_authorization(self, *, procedure_code: str, payer_name: str) -> dict:
        response = self._client.get(
            "/v1/prior-authorization-requirements", params={"procedure_code": procedure_code, "payer": payer_name}
        )
        response.raise_for_status()
        return {**response.json(), "data_source": "availity"}


def get_eligibility_provider() -> EligibilityProvider:
    settings = get_settings()
    if settings.eligibility_provider == "availity":
        return AvailityEligibilityProvider()
    return MockEligibilityProvider()
