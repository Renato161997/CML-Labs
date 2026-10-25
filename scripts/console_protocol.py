"""Identify a complete response, ignoring prompts from asynchronous console logs."""

import re


def response_complete(output, command, label):
    clean = re.sub(r"\x1b\[[0-9;?]*[a-zA-Z]", "", output).replace("\r", "")
    host = re.escape(label)
    prefix = rf"(?:{host}(?:\([^\n]*\))?[>#]|root@{host}:[^\n]*#)"
    echo = re.search(rf"(?m)^(?:{prefix}[ \t]*)?{re.escape(command)}[ \t]*$", clean)
    if not echo:
        return False
    remainder = clean[echo.end() :]
    prompt = rf"(?m)^{prefix}\s*$"
    return bool(re.search(prompt, remainder))
