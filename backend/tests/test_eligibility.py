import pytest

from app.integrations.eligibility import (
    AvailityEligibilityProvider,
    MockEligibilityProvider,
    get_eligibility_provider,
)


def test_mock_provider_flags_data_as_simulated():
    provider = MockEligibilityProvider()
    assert provider.check_network_status(provider_npi="1234567890", payer_name="Aetna")["data_source"] == "simulated"
    assert provider.estimate_cost(procedure_code="MRI", in_network=True, deductible_remaining=200)["data_source"] == "simulated"
    assert provider.check_prior_authorization(procedure_code="MRI", payer_name="Aetna")["data_source"] == "simulated"


def test_mock_cost_estimate_respects_deductible():
    provider = MockEligibilityProvider()
    result = provider.estimate_cost(procedure_code="MRI-KNEE", in_network=True, deductible_remaining=0)
    # fully past deductible: patient owes only the 20% in-network coinsurance
    assert result["estimated_patient_responsibility"] == pytest.approx(1200.0 * 0.2)


def test_mri_requires_prior_auth_but_xray_does_not():
    provider = MockEligibilityProvider()
    assert provider.check_prior_authorization(procedure_code="MRI-KNEE", payer_name="Aetna")["requires_prior_authorization"]
    assert not provider.check_prior_authorization(procedure_code="XRAY-HAND", payer_name="Aetna")["requires_prior_authorization"]


def test_get_eligibility_provider_defaults_to_mock():
    assert isinstance(get_eligibility_provider(), MockEligibilityProvider)


def test_availity_provider_requires_api_key():
    with pytest.raises(RuntimeError, match="AVAILITY_API_KEY"):
        AvailityEligibilityProvider()
