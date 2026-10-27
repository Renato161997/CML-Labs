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
    preparation = plan.get("prepare", [])
    if not isinstance(preparation, list) or len(preparation) > 1:
        errors.append("prepare must be a list containing at most one registered operation")
    else:
        for step in preparation:
            from iosxe_prepare import OPERATION, implementation_digest

            if (
                not isinstance(step, dict)
                or set(step) != {"operation", "router", "client", "implementation_sha256"}
                or step.get("operation") != OPERATION
                or not isinstance(step.get("router"), str)
                or not isinstance(step.get("client"), str)
                or step.get("router") not in labels
                or step.get("client") not in labels
                or step.get("router") == step.get("client")
                or step.get("implementation_sha256") != implementation_digest()
            ):
                errors.append("invalid or stale registered preparation operation")
    phases = {"baseline"}
    groups = [plan.get("checks", [])]
    for step in plan.get("transitions", []):
        name = step.get("name")
        if not name or name in phases or step.get("node") not in labels:
            errors.append("invalid transition name or node")
        phases.add(name)
        timeout = step.get("command_timeout", 5)
        if not isinstance(timeout, (int, float)) or not 1 <= timeout <= 60:
            errors.append("transition command timeout must be between 1 and 60 seconds")
        commands = step.get("commands", [])
        if not commands or any(
            not isinstance(c, str) or not c.strip() or any(x in c for x in ("\n", "\r", "\x00"))
            for c in commands
        ):
            errors.append("transition needs single-line console commands")
        if "command_pattern" in step:
            try:
                if not isinstance(step["command_pattern"], str) or not step["command_pattern"]:
                    raise ValueError("empty transition result pattern")
                re.compile(step["command_pattern"])
            except (re.error, TypeError, ValueError):
                errors.append("invalid transition result pattern")
        groups.append(step.get("checks", []))
    for checks in groups:
        if not checks:
            errors.append("each phase needs an observable acceptance check")
        for check in checks:
            timeout = check.get("command_timeout", 18)
            if (
                isinstance(timeout, bool)
                or not isinstance(timeout, (int, float))
                or not 1 <= timeout <= 90
            ):
                errors.append("acceptance command timeout must be between 1 and 90 seconds")
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
                output = console(check["node"]).command(
                    check["command"], check.get("command_timeout", 18)
                )
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

    for step in plan.get("prepare", []):
        from iosxe_prepare import OPERATION, implementation_digest, prepare_iosxe

        if (
            step["operation"] != OPERATION
            or step["implementation_sha256"] != implementation_digest()
        ):
            raise ValueError("Preparation implementation does not match the acceptance plan")
        prepare_iosxe(console(step["router"]), console(step["client"]), record, sleep=sleep)
        record(
            {
                "phase": "prepare",
                "kind": "preparation",
                "node": step["router"],
                "command": step["operation"],
                "implementation_sha256": step["implementation_sha256"],
                "passed": True,
            }
        )
    checks(plan["checks"], "baseline")
    for step in plan.get("transitions", []):
        phase = step["name"]
        for command in step["commands"]:
            output = console(step["node"]).command(command, step.get("command_timeout", 5))
            passed = command in output and not CLI_ERROR.search(output)
            if "command_pattern" in step:
                passed = passed and bool(re.search(step["command_pattern"], output, re.MULTILINE))
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
