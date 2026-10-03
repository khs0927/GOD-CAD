"""Untrusted report JSON cannot promote a simulation into native evidence."""

import json

import pytest
from jsonschema import ValidationError as SchemaValidationError
from jsonschema import validate
from pydantic import ValidationError

from god_cad.adapters.native import UnavailableNativeExecutor
from god_cad.models import PlanReport
from god_cad.planner import dry_run


@pytest.mark.parametrize(
    "promotion",
    [
        {"native_write_eligible": True},
        {"status": "verified"},
        {"canonical_allowed": True},
        {"execution_allowed": True},
    ],
)
def test_report_promotion_rejected_by_contract_and_schema(sample, patch_for, promotion):
    report = dry_run(sample[1], patch_for(sample[1])).model_dump(mode="json")
    report.update(promotion)
    # Exercise deserialization rather than trusted Python model construction.
    with pytest.raises(ValidationError):
        PlanReport.model_validate_json(json.dumps(report))
    with pytest.raises(SchemaValidationError):
        validate(report, PlanReport.model_json_schema())


@pytest.mark.parametrize("stale", [False, True])
def test_roundtrip_reports_never_supply_native_permission(sample, patch_for, stale):
    changes = {"expected_revision": "0" * 64} if stale else {}
    patch = patch_for(sample[1], **changes)
    report = PlanReport.model_validate_json(dry_run(sample[1], patch).model_dump_json())
    assert report.status == ("rejected" if stale else "simulation_passed")
    assert report.native_write_eligible is False
    with pytest.raises(NotImplementedError, match="Simulation never authorizes"):
        UnavailableNativeExecutor().execute(patch)
