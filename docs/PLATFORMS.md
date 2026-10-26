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
| CSR 1000v | GigabitEthernet1 | 3072 MiB | Full IOS XE console/API prerequisites; check each workbook's live result |
| net-tools | eth0 management, eth1 first lab data interface | 512 MiB | Native Python, requests, curl and Net-SNMP client tools |
| RADIUS / TACACS+ / syslog | eth0 management, eth1 first lab data interface | 512 MiB | Dedicated native server definitions; service-specific configurations |

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

The harness requires a running node process and checks a privileged, responsive
console. A `STARTED` API state still needs explicit interactive confirmation; it
is recorded as observed and is never relabeled `BOOTED`.
Native server containers must answer `id -u` with zero before the harness assigns
an identifying shell prompt. This changes only the disposable console's PS1, not
users or credentials. The SSH and WebSocket console paths have both been checked
on the native net-tools reference image. Keep native shell acceptance commands
short: interactive line editing can redraw and corrupt long command echoes.
The native net-tools interactive console is port 0. The dedicated syslog, RADIUS
and TACACS+ definitions expose their daemon output on port 0 and a separate shell
on port 1; the harness selects that shell for acceptance commands.
An IP-specific daemon listener can start before day-0 addresses are applied.
The syslog exercise uses the supported `ip-freebind(yes)` option, keeping the
listener on the lab data address while allowing that startup order.
[CML native container definitions](https://github.com/CiscoLearning/cml-docker-containers).
First boots can take several minutes. Results count observational assertions
separately from transition/configuration commands; a successful command echo alone
does not establish that a protocol converged or that traffic passed.
