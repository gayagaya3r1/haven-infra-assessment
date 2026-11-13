"""
B2, part 2 — implement the cost-tagging check.

Read fixtures/plan.json for the shape of a `terraform show -json` plan: a `resource_changes`
list, where each entry has a `type`, an `address`, and `change.after.tags`.

Implement check_plan() so it:
  - Looks at every resource being created or updated (skip anything whose change.actions
    isn't "create" or "update" — a "no-op"/"read" change, or a "delete" with no `after`
    block at all).
  - Fails (returns a non-zero exit code) if the resource is missing the tag that identifies
    the real billing unit, per README.md's domain model — not whatever tag the resource
    happens to already carry.
  - Is idempotent: running this twice against the same plan file produces the same result,
    with no duplicate output and no flipped pass/fail. This is about a single run being
    stable and repeatable — it does not require remembering anything between runs.
  - Prints which specific resource address(es) are missing the tag.

Run manually: python scripts/cost_tag_check.py fixtures/plan.json
"""
import json
import sys

# LandlordAccount is the billing unit (README domain model), so this is the only tag that
# counts. A tenant_id or any other tag does NOT satisfy the check.
REQUIRED_TAG = "landlord_account_id"

# A replacement shows up as ["delete", "create"] or ["create", "delete"]; it still creates a
# new resource, so it is checked too.
CHECKED_ACTIONS = {"create", "update"}


def _is_created_or_updated(change: dict) -> bool:
    """True if this change creates/updates a resource and has an `after` block to inspect."""
    actions = change.get("actions") or []
    return bool(CHECKED_ACTIONS.intersection(actions)) and change.get("after") is not None


def _has_billing_tag(after: dict) -> bool:
    """True if the resource carries a non-empty landlord_account_id tag."""
    tags = after.get("tags") or {}
    value = tags.get(REQUIRED_TAG)
    return isinstance(value, str) and value.strip() != ""


def find_untagged(plan: dict) -> list[str]:
    """
    Return the addresses of created/updated resources missing the billing tag.

    Idempotency key: the resource `address` (e.g. aws_s3_bucket.landlord_media[0]). Addresses
    go into a set, so a resource listed twice is reported once, and the result is sorted so
    the output is the same on every run.
    """
    missing = set()
    for resource in plan.get("resource_changes") or []:
        change = resource.get("change") or {}
        if not _is_created_or_updated(change):
            continue  # no-op, read, or delete with no `after` block
        if not _has_billing_tag(change["after"]):
            missing.add(resource["address"])
    return sorted(missing)


def check_plan(plan_path: str) -> int:
    """
    Returns an exit code: 0 if every resource being created or updated has
    `landlord_account_id`, non-zero otherwise.
    """
    with open(plan_path, encoding="utf-8") as f:
        plan = json.load(f)

    missing = find_untagged(plan)

    if missing:
        print(f"FAIL: {len(missing)} resource(s) missing the '{REQUIRED_TAG}' tag:")
        for address in missing:
            print(f"  - {address}")
        return 1

    print(f"OK: every created or updated resource has the '{REQUIRED_TAG}' tag.")
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python scripts/cost_tag_check.py <plan.json>", file=sys.stderr)
        sys.exit(2)
    sys.exit(check_plan(sys.argv[1]))
