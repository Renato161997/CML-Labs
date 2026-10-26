# Validation levels

These checks have different meanings. A green CI badge is not a live CML pass.

See the [observed results matrix](RESULTS.md), [raw import/export evidence](import.json)
and [raw functional evidence](runtime.json).

1. **Static:** YAML parsing with duplicate-key rejection; named configuration
   files; unique node/interface/link IDs; valid physical endpoint references;
   slot/label consistency; no external connector or host-specific image pin.
2. **Import/export:** `import.json` records actual CML API import and export,
   preserving node/link counts, node labels and configuration contents. CML strips
   terminal newlines from configuration files; that normalization is allowed.
   Imported test labs are removed after each check. No nodes are booted by this level.
3. **Functional:** `runtime.json` records actual isolated boot and console
   acceptance commands for the curated subset, including the deliberate OSPF
   fault before repair. The file hash ties each result to the exact checked-in
   topology; a second hash ties it to the executed acceptance plan. Exact CML and image versions are recorded. This is a sampled
   functional suite, not certification of all 233 exercises.

The test environment is deliberately absent from the repository: no controller
address, administrator token, private inventory, recovery exports or real network
configuration belongs in public evidence. Only disposable exercise outputs are
eligible for publication.

Run static checks with `python scripts/labtools.py check`. Live testing is an
explicit maintainer operation against an appropriately licensed CML instance;
CI never connects to a home network or stores its credentials. See the
[runtime harness](../scripts/cml_smoke.py) for its scope and cleanup safeguards.

```sh
python -m pip install -r requirements-runtime.txt
python scripts/cml_smoke.py --url https://your-controller --phase import
python scripts/cml_smoke.py --url https://your-controller --phase functional --lab 017-single-area \
  --ssh-host your-console-server --known-hosts /path/to/verified_console_known_hosts
```

The default functional transport is Cisco's SSH console server on port 22.
It uses the CML application account, which is distinct from the appliance's
Linux/Cockpit account. Verify the console server's host-key fingerprint through
a trusted administration channel before populating the known-hosts file.
The console key can differ from the appliance management SSH key; do not delete
or blindly replace a known key after a mismatch. Unknown/mismatched keys fail
before credentials are sent. The optional `--console websocket` uses a trusted
HTTPS certificate and the CML web-console protocol instead.

Use `--image-override TYPE=IMAGE_ID` (repeat for each type) to select an installed
image privately, without putting appliance-specific pins in the public YAML.
For example, `--image-override iosv=iosv-159-3-m12` selects that IOSv reference
image when available. Runtime evidence records the selection. With automatic
selection the API can return `null`; that must not be presented as a verified
effective image ID. Console prompt and acceptance commands, rather than a
possibly incomplete boot-log tail alone, determine functional success.

All remaining catalog entries with `runtime_status: not-run` have **no functional
validation claim**, even if import/export passes. Platform concepts such as
VXLAN, NAC and controller integrations require a separate image-capability review.

Additional plans can contain ordered `transitions`. Each transition runs console
commands and then its own observable acceptance checks. Evidence must contain all
planned baseline checks, transition commands and transition checks; copying a plan
hash while omitting a failure or recovery phase is rejected. Results distinguish
protocol/data-plane checks from commands used to change the test state.

Slow protocols can set `attempts` (bounded to 60) and `interval_seconds` (bounded
to 30 seconds). Defaults remain five attempts eight seconds apart. In particular,
a fresh NTP reference may spend several minutes measuring clock drift before it
advertises synchronized time; transport reachability is not a substitute for that
state. The workbook and acceptance plan make the longer wait explicit.

Longer CLI operations can set a transition `command_timeout` between 1 and 60
seconds (default: 5). The SSH workbooks use 30 seconds for ephemeral RSA key
generation. This is distinct from protocol convergence retries and cannot remove
an acceptance check.

Offline guest fixtures declare an allowlisted `example_profile`. Run
`python scripts/embed_webhook.py --check` after changing a helper: it verifies
that embedded guest code matches the reviewed source, including the SSH
management probe. Unknown profiles and missing required files fail closed.
The management fixture uses a clearly public exercise password, never a CML
application credential or a production secret.

See [platform scope](../docs/PLATFORMS.md) before substituting IOL for IOSv or
selecting a platform for an API/controller exercise.

The API process state `STARTED` is not treated as a guest boot or functional pass.
Some reference VMs can keep that state after their boot messages. The harness
records the observed `startup_states` and requires the expected interactive
console for each such guest before running acceptance. Console establishment
failure still aborts the test. `console_boot_fallback` identifies the guests
checked this way; no API state is rewritten or promoted to `BOOTED`.

Console requests begin on a fresh input line, so an unsolicited syslog tail
cannot concatenate with the command echo. The parser still requires the exact
whole-line command and a subsequent matching prompt; a command-shaped substring
inside a log message is rejected.
