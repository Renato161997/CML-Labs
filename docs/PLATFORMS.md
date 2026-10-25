# Choosing a reference platform

Node definitions, installed images and tested features are separate prerequisites.
The workbook identifies the required node types; the dated results identify the
exact image IDs used in the observed run. Vendor images are never distributed here.

| Platform | Interface naming | Nominal RAM per node | Scope in this collection |
| --- | --- | ---: | --- |
| IOSv | GigabitEthernet0/0 | 512 MiB | Existing routing baselines |
| IOSvL2 | GigabitEthernet0/0, then GigabitEthernet1/0 | 768 MiB | Switching baselines |
| IOL-XE | Ethernet0/0, then Ethernet1/0 | 1024 MiB | Additional routing exercises |
| IOL-L2 XE | Ethernet0/0, then Ethernet1/0 | 1024 MiB | Available for compatible switching exercises |
| Ubuntu | ens2 | 2048 MiB | Existing offline application exercises |

RAM figures are planning defaults, not measured peak consumption. IOL uses a
container-based implementation rather than a full IOSv VM. It does **not** support
NETCONF, RESTCONF or EEM applets: those exercises require a suitable full IOS XE
platform such as CSR 1000v and a separate tested workflow.
[Cisco IOL documentation](https://developer.cisco.com/docs/modeling-labs/iol/).

Virtual Ethernet carrier does not reliably follow a remote interface shutdown.
Use explicit two-ended failures or reachability tracking when the exercise needs
them; do not assume a local `up/up` state proves a working path. The floating
static-route workbook demonstrates the asymmetric return-path failure explicitly.

IOSvL2 does not implement SPAN or private VLANs. IOSv does not implement BFD.
These are feature constraints, not errors to hide with a successful YAML import.
Exercises needing those features require another verified platform or remain
unverified.
[IOSvL2 documentation](https://developer.cisco.com/docs/modeling-labs/iosvl2/) ·
[IOSv documentation](https://developer.cisco.com/docs/modeling-labs/iosv/).

The harness checks a privileged, responsive console after CML reports `BOOTED`.
First boots can take several minutes. Results count observational assertions
separately from transition/configuration commands; a successful command echo alone
does not establish that a protocol converged or that traffic passed.
