import pytest
from pydantic import ValidationError
from app.schemas import (
    AccessoryReturnItemInput,
    ConditionCheckInput,
    PatientAckInput,
    CleaningInput,
    OverrideRecommendationInput,
    FollowUpTaskCreate,
    CreateReturnRequest
)

def test_accessory_return_valid():
    """Verify valid accessory return item passes validation."""
    item = AccessoryReturnItemInput(
        accessory_id="ACC-01",
        expected_quantity=2,
        returned_quantity=2,
        condition="PRESENT"
    )
    assert item.accessory_id == "ACC-01"
    assert item.expected_quantity == 2
    assert item.returned_quantity == 2
    assert item.condition == "PRESENT"

def test_accessory_return_negative_quantity_rejected():
    """Verify negative expected or returned quantity raises validation error."""
    with pytest.raises(ValidationError) as exc_info:
        AccessoryReturnItemInput(
            accessory_id="ACC-01",
            expected_quantity=1,
            returned_quantity=-1,
            condition="PRESENT"
        )
    assert "greater than or equal to 0" in str(exc_info.value)

    with pytest.raises(ValidationError) as exc_info2:
        AccessoryReturnItemInput(
            accessory_id="ACC-01",
            expected_quantity=-2,
            returned_quantity=1,
            condition="PRESENT"
        )
    assert "greater than or equal to 0" in str(exc_info2.value)

def test_accessory_return_invalid_condition_enum_rejected():
    """Verify invalid condition literal raises validation error."""
    with pytest.raises(ValidationError) as exc_info:
        AccessoryReturnItemInput(
            accessory_id="ACC-01",
            expected_quantity=1,
            returned_quantity=1,
            condition="LOST"  # Valid are PRESENT, MISSING, DAMAGED, EXCESS, UNKNOWN
        )
    assert "Input should be" in str(exc_info.value)

def test_condition_check_valid():
    """Verify valid condition check input with defaults and explicit values."""
    check = ConditionCheckInput(
        exterior="Good",
        screen="Good",
        buttons="Functional",
        power="Normal",
        battery="Normal",
        ports="Good",
        sensors="Functional",
        physical_cleanliness="Clean"
    )
    assert check.exterior == "Good"
    assert check.screen == "Good"
    assert check.power == "Normal"

def test_condition_check_invalid_enum_rejected():
    """Verify invalid condition enum values are strictly rejected."""
    with pytest.raises(ValidationError) as exc_info:
        ConditionCheckInput(exterior="Completely Destroyed")
    assert "Input should be" in str(exc_info.value)

    with pytest.raises(ValidationError) as exc_info2:
        ConditionCheckInput(screen="Shattered")
    assert "Input should be" in str(exc_info2.value)

    with pytest.raises(ValidationError) as exc_info3:
        ConditionCheckInput(power="Blown fuse")
    assert "Input should be" in str(exc_info3.value)

def test_override_recommendation_reason_length():
    """Verify override reason requires minimum 3 characters."""
    # Valid
    valid = OverrideRecommendationInput(override_reason="Bench tested OK by biomedical engineer")
    assert valid.override_reason == "Bench tested OK by biomedical engineer"

    # Too short (<3 chars)
    with pytest.raises(ValidationError) as exc_info:
        OverrideRecommendationInput(override_reason="ok")
    assert "at least 3 characters" in str(exc_info.value)

    # Empty
    with pytest.raises(ValidationError) as exc_info2:
        OverrideRecommendationInput(override_reason="")
    assert "at least 3 characters" in str(exc_info2.value)

def test_patient_ack_validation():
    """Verify patient acknowledgement status accepts only RECEIVED or MISSING."""
    ack = PatientAckInput(status="RECEIVED", method="Digital Signature")
    assert ack.status == "RECEIVED"

    ack_missing = PatientAckInput(status="MISSING")
    assert ack_missing.status == "MISSING"

    with pytest.raises(ValidationError):
        PatientAckInput(status="PENDING")

def test_cleaning_input_validation():
    """Verify cleaning status accepts allowed enum values."""
    clean = CleaningInput(status="COMPLETED")
    assert clean.status == "COMPLETED"

    clean_fail = CleaningInput(status="FAILED_UNCERTAIN")
    assert clean_fail.status == "FAILED_UNCERTAIN"

    with pytest.raises(ValidationError):
        CleaningInput(status="DIRTY")

def test_create_return_request_missing_required_fields():
    """Verify CreateReturnRequest requires device_id and received_by."""
    with pytest.raises(ValidationError):
        CreateReturnRequest(device_id="DEV-001")  # missing received_by

    req = CreateReturnRequest(device_id="DEV-001", received_by="Nurse Joy")
    assert req.device_id == "DEV-001"
    assert req.received_by == "Nurse Joy"
