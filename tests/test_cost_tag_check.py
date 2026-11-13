"""
Write tests here proving:
  1. Happy path: running the check against fixtures/plan.json correctly flags the resources
     missing `landlord_account_id` (listing_media, mls_feed_sync) and passes the ones that
     have it (landlord_media[0], screening_report_export). The fixture also has a "no-op"
     entry and a "delete" entry with no `after` block at all — neither should appear in the
     output or crash the check.
  2. Idempotency: running the check twice against the same plan file produces the same
     result both times, with no duplicated output.

check_plan() takes a file path, not a dict — for a case that needs its own plan contents
instead of the shared fixture, write one with pytest's `tmp_path` rather than editing
fixtures/plan.json. You don't need to shell out to the real script for every case.
"""
import json
from pathlib import Path

from scripts.cost_tag_check import check_plan

PLAN_PATH = Path(__file__).resolve().parent.parent / "fixtures" / "plan.json"


def _write_plan(tmp_path, resource_changes):
    path = tmp_path / "plan.json"
    path.write_text(json.dumps({"resource_changes": resource_changes}), encoding="utf-8")
    return str(path)


def test_flags_untagged_and_passes_tagged_resources(capsys):
    exit_code = check_plan(str(PLAN_PATH))
    output = capsys.readouterr().out

    assert exit_code != 0

    # Missing landlord_account_id (listing_media only has tenant_id, which doesn't count)
    assert "aws_s3_bucket.listing_media" in output
    assert "aws_lambda_function.mls_feed_sync" in output

    # Have landlord_account_id
    assert "aws_s3_bucket.landlord_media[0]" not in output
    assert "aws_lambda_function.screening_report_export" not in output

    # Skipped: no-op and delete-with-no-after
    assert "archive_media" not in output
    assert "decommissioned_media" not in output


def test_running_twice_gives_identical_result(capsys):
    first_code = check_plan(str(PLAN_PATH))
    first_output = capsys.readouterr().out

    second_code = check_plan(str(PLAN_PATH))
    second_output = capsys.readouterr().out

    assert first_code == second_code
    assert first_output == second_output
    assert first_output.count("aws_s3_bucket.listing_media") == 1
    assert first_output.count("aws_lambda_function.mls_feed_sync") == 1


def test_resource_listed_twice_is_reported_once(tmp_path, capsys):
    untagged = {
        "address": "aws_s3_bucket.listing_media",
        "type": "aws_s3_bucket",
        "change": {"actions": ["create"], "after": {"tags": {"tenant_id": "ten-001"}}},
    }
    plan_path = _write_plan(tmp_path, [untagged, untagged])

    assert check_plan(plan_path) != 0
    assert capsys.readouterr().out.count("aws_s3_bucket.listing_media") == 1


def test_replacement_is_checked(tmp_path, capsys):
    replaced = {
        "address": "aws_s3_bucket.replaced_media",
        "type": "aws_s3_bucket",
        "change": {"actions": ["delete", "create"], "after": {"tags": {}}},
    }
    plan_path = _write_plan(tmp_path, [replaced])

    assert check_plan(plan_path) != 0
    assert "aws_s3_bucket.replaced_media" in capsys.readouterr().out


def test_passes_when_every_resource_is_tagged(tmp_path, capsys):
    tagged = {
        "address": "aws_s3_bucket.landlord_media[0]",
        "type": "aws_s3_bucket",
        "change": {"actions": ["create"], "after": {"tags": {"landlord_account_id": "la-001"}}},
    }
    plan_path = _write_plan(tmp_path, [tagged])

    assert check_plan(plan_path) == 0
    assert "OK" in capsys.readouterr().out
