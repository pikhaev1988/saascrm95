"""Remote Stage 9 runner for Beget production DB."""
import os
import sys

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "analiz_gia.settings")
django.setup()

from django.core.management import call_command


def main():
    limit = None
    skip_upload = False
    for arg in sys.argv[1:]:
        if arg.startswith("--limit="):
            limit = int(arg.split("=", 1)[1])
        elif arg == "--skip-upload":
            skip_upload = True

    print("=== manage.py check ===")
    call_command("check")

    print("=== makemigrations --check ===")
    try:
        call_command("makemigrations", "--check", "--dry-run")
        print("makemigrations: OK")
    except SystemExit as exc:
        print("makemigrations exit:", getattr(exc, "code", None))

    print("=== apps.vpr tests ===")
    call_command("test", "apps.vpr", verbosity=1)

    print("=== STAGE 9 production acceptance ===")
    from apps.vpr.audit.run_stage9_production_acceptance import (
        run_stage9_production_acceptance,
    )

    result = run_stage9_production_acceptance(
        limit=limit,
        out_dir="apps/vpr/audit",
        skip_upload=skip_upload,
    )
    print(
        "FINAL={f} TOTAL={t} PASS={p} FAIL={fail} BLOCKED={b}".format(
            f=result.get("FINAL_PRODUCTION_ACCEPTANCE"),
            t=result.get("TOTAL_EXISTING"),
            p=result.get("PASS"),
            fail=result.get("FAIL"),
            b=result.get("BLOCKED"),
        )
    )
    print("New upload:", (result.get("New_upload") or {}).get("status"))
    print("Rebuild:", (result.get("Rebuild") or {}).get("status"))
    print("Isolation:", (result.get("Isolation") or {}).get("status"))


if __name__ == "__main__":
    main()
