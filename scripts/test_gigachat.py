"""Quick GigaChat connectivity check. Run: python scripts/test_gigachat.py"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

from users.ai import chat_completion_json, enhance_exam_analysis, gigachat_configured  # noqa: E402
from users.gigachat_client import _analysis_enabled, resolve_gigachat_credentials  # noqa: E402


def main() -> int:
    print("=== GigaChat check ===")
    print("configured:", gigachat_configured())
    print("analysis_enabled:", _analysis_enabled())
    cred = resolve_gigachat_credentials()
    print("credential_length:", len(cred) if cred else 0)

    if not gigachat_configured():
        print("FAIL: no credentials in .env")
        return 1

    result = chat_completion_json(
        system_prompt="Return only valid JSON, no markdown.",
        user_prompt='Return JSON: {"ok": true, "message": "test"}',
        temperature=0.1,
    )
    if not result:
        print("FAIL: API returned empty or invalid response (see logs above)")
        return 2

    print("OK: API response:", json.dumps(result, ensure_ascii=False))

    analysis = enhance_exam_analysis(
        {
            "exam_type": "ege",
            "subject": "math",
            "students_count": 30,
            "avg_score": 62,
            "draft_executive_summary": ["Черновик вывода"],
        }
    )
    if not isinstance(analysis, dict):
        print("FAIL: enhance_exam_analysis returned None")
        return 3
    if not analysis.get("executive_summary"):
        print("WARN: analysis OK but executive_summary empty; keys:", list(analysis.keys()))
    else:
        print("OK: report analysis module works, summary lines:", len(analysis["executive_summary"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
