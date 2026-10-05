import pytest
from fastapi import HTTPException
from app.models import DeviceReturn
from app.routers.return_router import check_return_modifiable

def test_check_return_modifiable_allowed_states():
    """Verify active return states (RETURN_PENDING, IN_REVIEW, QUARANTINED) pass modifiability check."""
    active_statuses = ["RETURN_PENDING", "IN_REVIEW", "QUARANTINED", "INSPECTED"]
    for st in active_statuses:
        ret = DeviceReturn(return_id=f"RET-TEST-{st}", device_id="DEV-01", status=st)
        # Should not raise exception
        check_return_modifiable(ret)

def test_check_return_modifiable_finalized_states_rejected():
    """Verify terminal return states (COMPLETED, READY_FOR_REISSUE, ARCHIVED) raise 400 state violation."""
    terminal_statuses = ["COMPLETED", "READY_FOR_REISSUE", "ARCHIVED"]
    for st in terminal_statuses:
        ret = DeviceReturn(return_id=f"RET-TEST-{st}", device_id="DEV-01", status=st)
        with pytest.raises(HTTPException) as exc_info:
            check_return_modifiable(ret)
        assert exc_info.value.status_code == 400
        assert "State Machine Violation" in exc_info.value.detail
        assert st in exc_info.value.detail
