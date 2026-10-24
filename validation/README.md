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
