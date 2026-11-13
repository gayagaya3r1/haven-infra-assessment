# B2 part 2: cost tag check (AI transcript)

- **Tool:** Claude Code (VS Code extension), model Claude Opus 5.5
- **Date:** 2026-11-13
- **Scope:** B2 part 2 only (`scripts/cost_tag_check.py` and `tests/test_cost_tag_check.py`).
  B2 part 1 (access control) is not covered in this file.

**How this was recorded:** my prompts are copied word for word, typos included. The AI's
messages are copied word for word. The commands the AI ran and the files it read are summarized
in *[brackets]*, with local folder paths shortened to repo paths.

---

## Prompt 1

> i want ti write a python code for this taks help me out

Pasted with the prompt: the full `README.md` (not repeated here, see the repo root) and the stub
from `scripts/cost_tag_check.py`:

```python
import json
import sys


def check_plan(plan_path: str) -> int:
    """
    Returns an exit code: 0 if every resource being created or updated has
    `landlord_account_id`, non-zero otherwise.
    """
    raise NotImplementedError("Implement this.")


if __name__ == "__main__":
    sys.exit(check_plan(sys.argv[1]))
```

## AI response 1

**AI:** I'll look at the plan fixture, the tests, and the design notes so the code matches what's
expected.

*[Listed `app/`, `fixtures/`, `scripts/`, `tests/`. Printed `DESIGN_NOTES.md`, the rest of
`README.md` and `requirements.txt`.]*

*[Printed `scripts/cost_tag_check.py` (including its docstring with the task rules) and every
file in `tests/`.]*

*[Ran a short Python script that printed each entry in `fixtures/plan.json` with its actions and
tags:]*

```
aws_s3_bucket.landlord_media[0] | aws_s3_bucket | ['create'] | after.tags: {'landlord_account_id': 'la-001'}
aws_s3_bucket.listing_media | aws_s3_bucket | ['create'] | after.tags: {'tenant_id': 'ten-001'}
aws_lambda_function.mls_feed_sync | aws_lambda_function | ['create'] | after.tags: {}
aws_lambda_function.screening_report_export | aws_lambda_function | ['update'] | after.tags: {'landlord_account_id': 'la-002', 'tenant_id': 'ten-002'}
aws_s3_bucket.archive_media | aws_s3_bucket | ['no-op'] | after.tags: {}
aws_s3_bucket.decommissioned_media | aws_s3_bucket | ['delete'] | after.tags: None
```

*[Printed the raw `fixtures/plan.json` and checked versions. Python 3.14.7 was found, but the
pytest check failed:]*

```
No module named pytest
```

**AI:** The fixture has 6 entries: 2 tagged correctly, 2 missing the landlord tag, 1 no-op and 1
delete with `after: null`. I'll implement the check and fill in the matching test file.

*[Edited `scripts/cost_tag_check.py`: replaced the `NotImplementedError` stub with the
implementation that is now in the file (`REQUIRED_TAG = "landlord_account_id"`, a set of checked
actions `{"create", "update"}`, a `find_untagged()` helper that collects missing addresses in a
set and returns them sorted, and a usage message when no argument is given).]*

*[Wrote `tests/test_cost_tag_check.py` with 5 tests.]*

**AI:** pytest isn't installed, so I'll run the script directly and set up a throwaway virtual
environment in the scratchpad to run the tests.

*[Ran `python scripts/cost_tag_check.py fixtures/plan.json` twice:]*

```
FAIL: 2 resource(s) missing the 'landlord_account_id' tag:
  - aws_lambda_function.mls_feed_sync
  - aws_s3_bucket.listing_media
exit code: 1
--- second run ---
FAIL: 2 resource(s) missing the 'landlord_account_id' tag:
  - aws_lambda_function.mls_feed_sync
  - aws_s3_bucket.listing_media
exit code: 1
```

*[Created a temporary virtual environment outside the repo, installed `pytest>=8.0`, and ran
`pytest tests/test_cost_tag_check.py -v`:]*

```
tests/test_cost_tag_check.py::test_flags_untagged_and_passes_tagged_resources PASSED [ 20%]
tests/test_cost_tag_check.py::test_running_twice_gives_identical_result PASSED [ 40%]
tests/test_cost_tag_check.py::test_resource_listed_twice_is_reported_once PASSED [ 60%]
tests/test_cost_tag_check.py::test_replacement_is_checked PASSED         [ 80%]
tests/test_cost_tag_check.py::test_passes_when_every_resource_is_tagged PASSED [100%]

============================== 5 passed in 0.35s ==============================
```

**AI:**

I implemented the check in [cost_tag_check.py](scripts/cost_tag_check.py) and filled in the tests
in [test_cost_tag_check.py](tests/test_cost_tag_check.py). All 5 tests pass, and running the
script twice prints the same thing both times:

```
FAIL: 2 resource(s) missing the 'landlord_account_id' tag:
  - aws_lambda_function.mls_feed_sync
  - aws_s3_bucket.listing_media
exit code: 1
```

### How the code works

1. It reads the plan JSON file.
2. It only checks resources being **created or updated**. It skips `no-op`, `read`, and
   `delete` entries with no `after` block.
3. A **replacement** (`["delete", "create"]`) is checked too, because it creates a new resource.
4. Each resource must have a **`landlord_account_id`** tag with a non-empty value, because the
   landlord account is the billing unit. `tenant_id` doesn't count, which is why
   `listing_media` fails.
5. Failing resource addresses go into a **set**, so a resource listed twice is printed only once.
6. The list is **sorted**, so the output comes out the same on every run.
7. It returns **1** if anything is missing and **0** if everything is tagged.

### What the tests check

- The right 2 resources are flagged, and the correctly tagged ones pass.
- The `no-op` and `delete` entries don't show up in the output and don't crash the check.
- Running it twice gives the same output and the same exit code.
- A resource listed twice is reported once.
- A replacement with missing tags is caught.

### For DESIGN_NOTES.md

DESIGN_NOTES.md also asks you to explain the idempotency key. This paragraph is written for the
reviewer and is ready to paste:

> The idempotency key is the resource `address` (for example `aws_s3_bucket.listing_media`).
> The address is unique for each resource in a plan, so the script adds failing addresses to a
> set; a duplicate entry is reported only once. The output is sorted and depends only on the
> plan file. The script stores nothing between runs, so running it twice on the same file
> always gives the same output and the same exit code.

### Notes

- pytest isn't installed on your machine. I ran the tests in a temporary environment. To run
  them yourself: `pip install -r requirements.txt`, then
  `python -m pytest tests/test_cost_tag_check.py`.
- The other half of B2 is still a stub: `can_access_screening_report` in
  `app/access_control.py`, and its tests in `tests/test_access_control.py`.

---

## Prompt 2

> what did we test in that pytest and what are we trying to achieve her, in crisp

## AI response 2

**Goal:** every AWS resource being created or changed must say which landlord account it
belongs to, using the `landlord_account_id` tag. The landlord account is who gets billed, so an
untagged resource is cost that can't be charged to anyone. The script catches this in the
Terraform plan, before anything is deployed, and fails the check.

**What the 5 tests check:**

| Test | What it proves |
|---|---|
| Flags untagged, passes tagged | `listing_media` and `mls_feed_sync` fail. `landlord_media[0]` and `screening_report_export` pass. The `no-op` and `delete` entries are skipped without crashing. |
| Running twice gives the same result | Same output and same pass/fail every time (idempotent). |
| Resource listed twice is reported once | No duplicate lines in the output. |
| Replacement is checked | A resource being deleted and recreated is still checked, because a new resource gets created. |
| Passes when everything is tagged | A plan where every resource is tagged returns 0 (pass). |

**In one line:** the tests prove the check fails on the right resources, skips the ones it
should, and gives the same answer every time it runs.
