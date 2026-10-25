"""Console acceptance checks, including observed failure and recovery transitions."""

import re
import time

CLI_ERROR = re.compile(
    r"%\s*(?:Invalid input|Incomplete command|Ambiguous command|Unknown command|Error)",
    re.IGNORECASE,
)


def validate_plan(plan, labels):
    """Reject malformed or unverifiable phases before starting any lab."""
    errors = []
    phases = {"baseline"}
    groups = [plan.get("checks", [])]
    for step in plan.get("transitions", []):
        name = step.get("name")
        if not name or name in phases or step.get("node") not in labels:
            errors.append("invalid transition name or node")
        phases.add(name)
        commands = step.get("commands", [])
        if not commands or any(
            not isinstance(c, str) or not c.strip() or any(x in c for x in ("\n", "\r", "\x00"))
            for c in commands
        ):
            errors.append("transition needs single-line console commands")
        groups.append(step.get("checks", []))
    for checks in groups:
        if not checks:
            errors.append("each phase needs an observable acceptance check")
        for check in checks:
            if (
                check.get("node") not in labels
                or not check.get("command")
                or not check.get("expectation")
            ):
                errors.append("invalid acceptance command or node")
            try:
                re.compile(check["pattern"])
                if check.get("absent_pattern"):
                    re.compile(check["absent_pattern"])
            except (re.error, KeyError, TypeError):
                errors.append("invalid acceptance pattern")
    return errors


def execute_plan(plan, console, record, *, sleep=time.sleep):
    """Run baseline checks and ordered transitions; retain partial evidence on failure.

    A console must echo each command. No command is accepted solely because a
    prompt or a configured string happened to be present in old console output.
    Existing break/fix initial-state handling remains with the harness.
    """

    def checks(items, phase):
        for check in items:
            output = ""
            passed = False
            attempts = max(1, min(int(check.get("attempts", 5)), 60))
            for attempt in range(attempts):
                output = console(check["node"]).command(check["command"])
                passed = bool(
                    check["command"] in output
                    and not CLI_ERROR.search(output)
                    and re.search(check["pattern"], output, re.MULTILINE | re.IGNORECASE)
                    and (
                        not check.get("absent_pattern")
                        or not re.search(
                            check["absent_pattern"], output, re.MULTILINE | re.IGNORECASE
                        )
                    )
                )
                if passed:
                    break
                if attempt + 1 < attempts:
                    sleep(max(1, min(float(check.get("interval_seconds", 8)), 30)))
            record(
                {
                    "phase": phase,
                    "node": check["node"],
                    "command": check["command"],
                    "expectation": check["expectation"],
                    "passed": passed,
                    "output": output[-3500:],
                }
            )
            if not passed:
                raise AssertionError(
                    "Acceptance check failed in " + phase + ": " + check["command"]
                )

    checks(plan["checks"], "baseline")
    for step in plan.get("transitions", []):
        phase = step["name"]
        for command in step["commands"]:
            output = console(step["node"]).command(command, 5)
            passed = command in output and not CLI_ERROR.search(output)
            record(
                {
                    "phase": phase,
                    "kind": "configuration",
                    "node": step["node"],
                    "command": command,
                    "passed": bool(passed),
                    "output": output[-3500:],
                }
            )
            if not passed:
                raise AssertionError("Transition command failed: " + command)
        checks(step["checks"], phase)
