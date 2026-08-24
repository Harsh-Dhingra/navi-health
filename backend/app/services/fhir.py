"""Minimal FHIR R4 resource builders.

NAVI normalizes fragmented, payer- and provider-specific documents into
FHIR-aligned representations (Coverage, ExplanationOfBenefit, Encounter) so
downstream agents and any future EHR/payer integration speak a consistent
schema instead of ad-hoc dicts.
"""

import uuid
from typing import Any


def build_coverage_resource(*, payer_name: str, member_id: str, group_number: str | None, plan_name: str | None) -> dict[str, Any]:
    return {
        "resourceType": "Coverage",
        "id": str(uuid.uuid4()),
        "status": "active",
        "payor": [{"display": payer_name}],
        "subscriberId": member_id,
        "class": [
            {"type": {"text": "group"}, "value": group_number or ""},
            {"type": {"text": "plan"}, "value": plan_name or ""},
        ],
    }


def build_explanation_of_benefit(
    *, claim_number: str | None, provider_name: str | None, billed_amount: float | None, patient_responsibility: float | None
) -> dict[str, Any]:
    return {
        "resourceType": "ExplanationOfBenefit",
        "id": str(uuid.uuid4()),
        "status": "active",
        "identifier": [{"value": claim_number}] if claim_number else [],
        "provider": {"display": provider_name} if provider_name else None,
        "total": [
            {"category": {"text": "billed"}, "amount": {"value": billed_amount, "currency": "USD"}},
            {"category": {"text": "patient_responsibility"}, "amount": {"value": patient_responsibility, "currency": "USD"}},
        ],
    }


def build_encounter_resource(*, provider_name: str | None, visit_type: str | None, reason: str | None) -> dict[str, Any]:
    return {
        "resourceType": "Encounter",
        "id": str(uuid.uuid4()),
        "status": "finished",
        "class": {"code": visit_type or "AMB"},
        "serviceProvider": {"display": provider_name} if provider_name else None,
        "reasonCode": [{"text": reason}] if reason else [],
    }
