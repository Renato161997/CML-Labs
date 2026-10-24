# Contributing

Report a reproducible import, boot or exercise problem using the issue form.
Include the lab path, CML version, node image versions, expected result and the
smallest relevant error. Remove real credentials, serial numbers, public/private
infrastructure details and proprietary configurations before posting.

## Development checks

```sh
python -m pip install -r requirements-dev.txt
ruff format scripts tests examples
ruff check scripts tests examples
python scripts/labtools.py generate
python scripts/labtools.py check
python scripts/embed_webhook.py --check
python -m unittest discover -s tests -v
```

Use Python 3.11 or newer. Dependencies are intentionally small; the example
webhook uses only the Python standard library. CML is not needed for these local
checks. Passing them must never be described as a live CML test.

## Topology changes

- Keep paths stable where possible. Use explicit unique node/interface/link IDs.
- Keep interface labels consistent with physical slots in the node definition.
- Use CML named configuration files, not legacy strings or integer endpoints.
- Keep exercises isolated. External connectors and host-specific image pins fail
  the repository validator; discuss an explicit supported alternative first.
- Add a workbook with addressing, prerequisites, observable acceptance criteria,
  a reset procedure and any deliberate faults. Distinguish working baselines
  from break/fix starting states.
- Add/edit `catalog/curated.json` only when the workbook actually exists.
- Remove or replace stale import/export and runtime evidence after changing a topology. A hash
  mismatch deliberately fails CI. Record the actual CML/image versions tested.
- Do not upload vendor images, activation keys, proprietary courseware or dumps.
- After editing `examples/webhook/`, run `python scripts/embed_webhook.py` to
  refresh the code carried by the two offline Ubuntu topologies. Then refresh
  the catalog and repeat their functional checks; old evidence becomes stale.

The current default preserves the 233 existing exercise paths. Scaffold entries
remain scaffolds until their task instructions, actual platform capability and
functional checks have been reviewed. Import success is a separate level.

## Licensing decision

This repository does not currently contain an explicit open-source license.
Public visibility and forks do not by themselves grant broad redistribution
rights. The maintainer must choose a license before a reuse policy or inbound
contribution license is advertised. Cisco/vendor binaries and trademarks remain
outside any future license for the original topology/workbook material.
