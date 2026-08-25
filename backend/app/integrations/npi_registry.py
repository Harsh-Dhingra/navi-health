"""Real integration with the CMS NPPES NPI Registry.

Unlike payer eligibility/cost/prior-auth (which need a contracted
clearinghouse relationship), the NPI Registry is a genuinely public,
credential-free federal API — every U.S. healthcare provider's National
Provider Identifier record is queryable at no cost. This gives NAVI real
verified provider identity/specialty/address data even before any payer
integration is signed. It does NOT tell you network status, which is
payer-specific and requires the adapter in `app/integrations/eligibility.py`.

https://npiregistry.cms.hhs.gov/api-docs/
"""

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

NPI_REGISTRY_URL = "https://npiregistry.cms.hhs.gov/api/"


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=0.5, min=0.5, max=4))
def search_providers(*, taxonomy_description: str, state: str, limit: int = 10) -> list[dict]:
    """Search NPPES by specialty (taxonomy) and state. Returns real,
    federally-registered provider records — name, NPI, specialty, address."""
    params = {
        "version": "2.1",
        "taxonomy_description": taxonomy_description,
        "state": state,
        "limit": limit,
        "enumeration_type": "NPI-1",  # individual providers, not organizations
    }
    with httpx.Client(timeout=10.0) as client:
        response = client.get(NPI_REGISTRY_URL, params=params)
        response.raise_for_status()
        payload = response.json()

    results = []
    for record in payload.get("results", []):
        basic = record.get("basic", {})
        address = next(
            (a for a in record.get("addresses", []) if a.get("address_purpose") == "LOCATION"),
            record.get("addresses", [{}])[0] if record.get("addresses") else {},
        )
        results.append(
            {
                "npi": record.get("number"),
                "name": f"{basic.get('first_name', '')} {basic.get('last_name', '')}".strip() or basic.get("organization_name"),
                "specialty": next(
                    (t.get("desc") for t in record.get("taxonomies", []) if t.get("primary")), taxonomy_description
                ),
                "city": address.get("city"),
                "state": address.get("state"),
                "phone": address.get("telephone_number"),
                "data_source": "npi_registry",  # real, federally verified — not simulated
            }
        )
    return results
