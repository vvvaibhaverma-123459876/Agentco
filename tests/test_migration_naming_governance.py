"""AUD-006: migration naming/ordering governance.

Adversarial tests for scripts/verify_migration_naming.py -- proves the checker
actually catches a duplicate sequence number and a non-conforming filename in a
synthetic directory (not just that it happens to pass against the real,
already-clean migrations directory), and proves the grandfather list is scoped
to exact filenames rather than blanket-exempting a whole number or pattern.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import verify_migration_naming as vmn  # noqa: E402


def write(directory: Path, name: str, content: str = "-- test\n") -> None:
    (directory / name).write_text(content)


def test_real_migrations_directory_is_currently_clean():
    findings = vmn.verify(ROOT / "backend" / "src" / "db" / "migrations")
    assert findings == []


def test_cli_check_mode_exits_zero_on_real_directory():
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "verify_migration_naming.py"), "--check"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert '"success": true' in result.stdout


def test_new_duplicate_sequence_number_is_caught(tmp_path):
    write(tmp_path, "200_alpha.sql")
    write(tmp_path, "200_beta.sql")
    findings = vmn.verify(tmp_path)
    assert any(f.startswith("DUPLICATE_SEQUENCE_NUMBER:200:") for f in findings)


def test_nonconforming_filename_is_caught(tmp_path):
    write(tmp_path, "201_ok.sql")
    write(tmp_path, "202b_sneaky_letter_suffix.sql")
    findings = vmn.verify(tmp_path)
    assert any(f == "NONCONFORMING_FILENAME:202b_sneaky_letter_suffix.sql" for f in findings)


def test_uppercase_filename_is_caught(tmp_path):
    write(tmp_path, "203_Bad_Case.sql")
    findings = vmn.verify(tmp_path)
    assert any(f.startswith("NONCONFORMING_FILENAME:203_Bad_Case.sql") for f in findings)


def test_grandfathered_pair_reproduced_exactly_is_clean(tmp_path):
    # A control: if the tmp directory contains EXACTLY the real 051 pair (same two
    # filenames, same number, nothing else), it must be silent -- proving the
    # grandfather list works, not just that duplicates always fail.
    write(tmp_path, "051_fix_fk_constraints.sql")
    write(tmp_path, "051_team_activations.sql")
    findings = vmn.verify(tmp_path)
    assert findings == []


def test_third_file_added_to_a_grandfathered_number_is_still_caught(tmp_path):
    # The grandfather exemption is scoped to the EXACT pair, not the number --
    # adding a third file that reuses 051 must not be silently exempted.
    write(tmp_path, "051_fix_fk_constraints.sql")
    write(tmp_path, "051_team_activations.sql")
    write(tmp_path, "051_sneaky_third_migration.sql")
    findings = vmn.verify(tmp_path)
    assert any(f.startswith("DUPLICATE_SEQUENCE_NUMBER:051:") for f in findings)


def test_renaming_a_grandfathered_file_is_caught_not_silently_accepted(tmp_path):
    # If a grandfathered file were renamed, the new name must NOT quietly inherit
    # the exemption just because the number matches -- and the disappearance of
    # the original documented filename must itself be flagged.
    write(tmp_path, "051_fix_fk_constraints.sql")
    write(tmp_path, "051_team_activations_renamed.sql")
    findings = vmn.verify(tmp_path)
    assert any(f.startswith("DUPLICATE_SEQUENCE_NUMBER:051:") for f in findings)
    assert any(f.startswith("GRANDFATHERED_FILE_MISSING:051:") for f in findings)


def test_grandfathered_nonconforming_filename_reproduced_exactly_is_clean(tmp_path):
    write(tmp_path, "052b_institutions.sql")
    write(tmp_path, "052_specialist_http_endpoint.sql")
    write(tmp_path, "053_work_assignment_schema.sql")
    findings = vmn.verify(tmp_path)
    assert findings == []


def test_a_second_letter_suffixed_file_is_not_exempted_by_resembling_052b(tmp_path):
    # 052b is a named, one-off exception -- not a sanctioned pattern. A brand-new
    # letter-suffixed filename must still fail even though it "looks like" 052b.
    write(tmp_path, "204b_new_letter_suffix_attempt.sql")
    findings = vmn.verify(tmp_path)
    assert any(f == "NONCONFORMING_FILENAME:204b_new_letter_suffix_attempt.sql" for f in findings)


def test_clean_sequential_migrations_produce_no_findings(tmp_path):
    write(tmp_path, "300_first.sql")
    write(tmp_path, "301_second.sql")
    write(tmp_path, "302_third_thing.sql")
    findings = vmn.verify(tmp_path)
    assert findings == []
