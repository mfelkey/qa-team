"""
agents/orchestrator/orchestrator.py

Protean Pursuits — QA Team Orchestrator

Scope: Portfolio-wide — covers code, data pipelines, marketing content,
       legal documents, and accessibility across all teams.

Sign-off authority: The QA Team Orchestrator issues GO / CONDITIONAL GO /
NO GO decisions. Nothing ships without QA sign-off.

Run modes:
  TEST_CASE    — develop test cases for a feature or component
  AUDIT        — audit an existing product, pipeline, or document
  FULL_QA      — all applicable agents, complete QA package
  SIGN_OFF     — final pre-launch QA gate

Risk levels:
  PASS         — meets quality standards, no blocking issues
  CONDITIONAL  — minor issues, can ship with remediation plan
  FAIL         — blocking issues, must not ship until resolved
  CRITICAL     — severe issues requiring immediate escalation
"""

import os
import json
import uuid
from datetime import datetime
from dotenv import load_dotenv
from crewai import Agent, LLM

load_dotenv("config/.env")

QA_PASS      = "PASS"
QA_CONDITIONAL = "CONDITIONAL"
QA_FAIL      = "FAIL"
QA_CRITICAL  = "CRITICAL"

QA_INSTRUCTION = """
QA OUTPUT STANDARDS — MANDATORY:

1. VERDICT BLOCK: Every QA output must open with:
---
QA VERDICT: [PASS | CONDITIONAL | FAIL | CRITICAL]
BLOCKING ISSUES: [count] — list below
NON-BLOCKING ISSUES: [count] — list below
SIGN-OFF STATUS: [APPROVED TO SHIP | CONDITIONAL — see remediation plan | DO NOT SHIP]
---

2. ISSUE FORMAT: Every issue must include:
   - ID (e.g. QA-001)
   - Severity: CRITICAL / HIGH / MEDIUM / LOW
   - Category: functional / performance / security / accessibility / data / compliance
   - Description: precise, reproducible description
   - Expected vs actual (for functional issues)
   - Remediation: specific fix required
   - Blocking: YES / NO (blocks ship if YES)

3. NO VAGUE FINDINGS: "Performance could be better" is not a finding.
   "API response time exceeds 2s SLA under 50 concurrent users (measured:
   2.8s p95)" is a finding.

4. RETEST REQUIREMENT: Every FAIL or CRITICAL verdict must specify
   what must be retested and what evidence is required for sign-off.
"""



def send_pushover(subject: str, message: str, priority: int = 1) -> bool:
    """Send Pushover push notification."""
    import urllib.request, urllib.parse, json
    user_key  = os.getenv("PUSHOVER_USER_KEY", "")
    api_token = os.getenv("PUSHOVER_API_TOKEN", "")
    if not user_key or not api_token:
        print("⚠️  Pushover credentials not set")
        return False
    try:
        data = urllib.parse.urlencode({
            "token": api_token, "user": user_key,
            "title": subject[:250], "message": message[:1024],
            "priority": priority,
        }).encode("utf-8")
        req = urllib.request.Request(
            "https://api.pushover.net/1/messages.json",
            data=data, method="POST"
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            result = json.loads(resp.read())
            if result.get("status") == 1:
                print(f"📱 Pushover sent: {subject[:60]}")
                return True
            print(f"⚠️  Pushover error: {result}")
            return False
    except Exception as e:
        print(f"⚠️  Pushover failed: {e}")
        return False


def send_sms(message: str) -> bool:
    return send_pushover("Notification", message, priority=1)


def send_email(subject: str, body: str) -> bool:
    return send_pushover(subject, body, priority=0)


def notify_human(subject: str, message: str) -> None:
    send_sms(f"[QA-TEAM] {subject}\n{message}")
    send_email(f"[QA-TEAM] {subject}", message)


def escalate_qa_failure(context: dict, verdict: str,
                         artifact_path: str, summary: str) -> None:
    if verdict in (QA_FAIL, QA_CRITICAL):
        notify_human(
            subject=f"[{verdict}] QA — {context['qa_name']}",
            message=(
                f"QA ID: {context['qa_id']}\n"
                f"Matter: {context['qa_name']}\n"
                f"Verdict: {verdict}\n"
                f"Summary: {summary}\n"
                f"Report: {artifact_path}\n\n"
                f"DO NOT SHIP until blocking issues are resolved."
            )
        )
        print(f"\n🚨 [{verdict}] QA failure escalated — {context['qa_id']}")


def request_human_review(artifact_path: str, summary: str,
                          verdict: str, timeout_hours: int = 48) -> bool:
    import time as _t
    approval_dir = "logs/approvals"
    os.makedirs(approval_dir, exist_ok=True)
    review_id = f"QA-{uuid.uuid4().hex[:8].upper()}"
    response_file = f"{approval_dir}/{review_id}.response.json"

    with open(f"{approval_dir}/{review_id}.json", "w") as f:
        json.dump({"review_id": review_id, "verdict": verdict,
                   "artifact_path": artifact_path, "summary": summary,
                   "requested_at": datetime.utcnow().isoformat()}, f, indent=2)

    notify_human(
        subject=f"[QA REVIEW — {verdict}] {review_id}",
        message=(
            f"Verdict: {verdict}\nSummary: {summary}\n"
            f"Report: {artifact_path}\n\n"
            f"{'DO NOT SHIP — blocking issues present.' if verdict in (QA_FAIL, QA_CRITICAL) else ''}\n"
            f"Approve: {{'decision': 'APPROVED'}}\n"
            f"Reject: {{'decision': 'REJECTED', 'reason': '...'}}"
        )
    )
    print(f"\n⏸️  [QA REVIEW — {verdict}] {review_id}")

    elapsed = 0
    while elapsed < timeout_hours * 3600:
        if os.path.exists(response_file):
            with open(response_file) as f:
                resp = json.load(f)
            decision = resp.get("decision", "").upper()
            if decision == "APPROVED":
                print(f"✅ QA review approved — {review_id}")
                return True
            elif decision == "REJECTED":
                print(f"❌ QA review rejected — {review_id}")
                return False
        _t.sleep(30)
        elapsed += 30
    print(f"⏰ QA review timed out — {review_id}")
    return False


def create_qa_context(qa_name: str, qa_type: str,
                       target_team: str = None,
                       project_id: str = None) -> dict:
    return {
        "framework": "protean-pursuits-qa",
        "qa_id": f"QA-{uuid.uuid4().hex[:8].upper()}",
        "qa_name": qa_name,
        "qa_type": qa_type,
        "target_team": target_team,
        "project_id": project_id,
        "created_at": datetime.utcnow().isoformat(),
        "status": "INITIATED",
        "verdict": None,
        "artifacts": [],
        "events": []
    }


def save_context(context: dict) -> str:
    os.makedirs("logs", exist_ok=True)
    path = f"logs/{context['qa_id']}.json"
    with open(path, "w") as f:
        json.dump(context, f, indent=2)
    return path


def log_event(context: dict, event_type: str, detail: str = "") -> None:
    context["events"].append({"event_type": event_type, "detail": detail,
                               "timestamp": datetime.utcnow().isoformat()})
    save_context(context)


def save_artifact(context: dict, name: str, artifact_type: str,
                  content: str, output_dir: str, verdict: str = QA_CONDITIONAL) -> str:
    os.makedirs(output_dir, exist_ok=True)
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    path = f"{output_dir}/{context['qa_id']}_{artifact_type}_{ts}.md"
    with open(path, "w") as f:
        f.write(content)
    context["verdict"] = verdict
    context["artifacts"].append({"name": name, "type": artifact_type,
                                  "path": path, "verdict": verdict,
                                  "status": "PENDING_REVIEW",
                                  "created_at": datetime.utcnow().isoformat()})
    log_event(context, f"{artifact_type}_COMPLETE", path)
    print(f"\n💾 [{artifact_type} — {verdict}] Saved: {path}")
    return path


def build_qa_orchestrator() -> Agent:
    llm = LLM(model=os.getenv("TIER1_MODEL", "ollama/qwen3:32b"),
               base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
               timeout=1800)
    return Agent(
        role="QA Team Orchestrator",
        goal=(
            "Coordinate portfolio-wide quality assurance — across code, data, "
            "design, marketing content, and legal documents — issuing GO / "
            "CONDITIONAL GO / NO GO verdicts that nothing ships without."
        ),
        backstory=(
            "You are the VP of Quality Assurance at Protean Pursuits LLC — a QA "
            "leader with 18 years of experience building quality frameworks for "
            "technology companies across software, data, and regulated industries. "
            "You operate portfolio-wide: you QA software from the Dev Team, data "
            "pipelines from the DS Team, campaigns from the Marketing Team, brand "
            "assets from the Design Team, and compliance documents from the Legal "
            "Team. Quality is not a department — it is a gate that everything passes "
            "through before it reaches users, regulators, or counterparties. "
            "You lead eight specialist agents: Functional/Integration Testing, "
            "Performance & Load Testing, Security & Penetration Testing, "
            "Accessibility Auditing, Data Quality & Pipeline QA, Marketing & "
            "Content Compliance QA, Legal Document Completeness QA, and Test Case "
            "Development. You assign the right agents to each QA request, review "
            "their findings, and issue the final sign-off verdict. "
            "Your verdicts are: PASS (ship it), CONDITIONAL (ship with remediation "
            "plan), FAIL (do not ship), CRITICAL (immediate escalation). You never "
            "issue a PASS to avoid difficult conversations. You never issue a FAIL "
            "without a clear, actionable remediation path."
        ),
        llm=llm, verbose=True, allow_delegation=True
    )


# ── Run function ──────────────────────────────────────────────────────────────

def run_qa_orchestrator(brief: str, context: dict) -> str:
    """
    Instantiate the QA Team Orchestrator, run it against the brief, return output.

    Called by flows/qa_intake_flow.py via:
        run_qa_orchestrator = _import_orchestrator()
        result = run_qa_orchestrator(brief=brief_text, context=project_context)
    """
    from crewai import Crew, Task

    agent = build_qa_orchestrator()
    context_block = (
        context.get("raw", "")
        or (json.dumps(context, indent=2) if context else "No context provided.")
    )

    task = Task(
        description=(
            f"Project brief:\n{brief}\n\n"
            f"Project context:\n{context_block}\n\n"
            "Coordinate portfolio-wide quality assurance for this project. "
            "Assign the appropriate specialist agents (functional, performance, "
            "security, accessibility, data quality, content compliance). "
            "Every output must open with a QA VERDICT block: "
            "PASS / CONDITIONAL / FAIL / CRITICAL, blocking issue count, "
            "non-blocking issue count, and SIGN-OFF STATUS. "
            "Every issue must have an ID, severity, category, description, "
            "expected vs actual, remediation, and blocking flag. "
            "FAIL and CRITICAL verdicts trigger immediate human escalation. "
            "Nothing ships without QA sign-off. "
            "End with CROSS-TEAM FLAGS and OPEN QUESTIONS."
        ),
        expected_output=(
            "Complete QA report with VERDICT block, full issue list with IDs, "
            "severity, and remediation steps. Sign-off decision clearly stated. "
            "No placeholders. Ends with CROSS-TEAM FLAGS and OPEN QUESTIONS."
        ),
        agent=agent,
    )

    crew = Crew(agents=[agent], tasks=[task], verbose=True)
    result = crew.kickoff()
    return str(result)
