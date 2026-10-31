# Platform behavior and evidence

A configured feature, a green boot state and successful forwarding are separate observations. Read the dated [functional receipts](../validation/RESULTS.md) for the exact topology hash, acceptance plan and image IDs. A workbook is not a platform certification.

## Packet visibility

The recorded `ioll2-xe-17-18-02` runs passed local SPAN and remote SPAN using an actual receive-only Linux packet observer. The proof includes a selected fresh HTTP request in a PCAP, a complete bounded absence window during the mirror fault, continued application service and a new packet after repair. It does not infer visibility from `show monitor` alone. The remote-SPAN lab exercises a remote VLAN across a trunk; it does not exercise ERSPAN/GRE even though its historical filename includes `erspan`.

Cisco lists SPAN as unsupported for [IOSvL2](https://developer.cisco.com/docs/modeling-labs/iosvl2/). The SPAN exercises therefore use their independently tested IOL-L2 image. Do not swap to IOSvL2 based only on accepted CLI syntax.

[The packet observer](../examples/security/packet_observer.py) selects a specific benchmark-address TCP request on the disposable capture guest data NIC. Its PCAP parser supports the documented Ethernet/VLAN/IPv4/TCP subset. It does not provide general TCP reassembly, checksums, an IDS or a production capture service.

## Access policy scope

ENCOR032 requires separate actual ingress clients: the PACL must reject only the selected access port, while the VACL must select both clients in the same VLAN. Positive management and reverse-direction controls must remain healthy. An ACL permit inside the VLAN access-map classifier identifies traffic; the access-map action decides whether to drop or forward it. These virtual packet results do not establish ASIC performance or physical-switch timing.

IP Source Guard remains an uncurated scaffold. An isolated `iosvl2-2020` probe reported an active correct DHCP binding but blocked the legitimately bound source after filtering was enabled. `cat9000v-q200-17-18-02` rejected `ip verify source`. The separate UADP probe did not establish its required baseline forwarding. An IOL-L2 trial obtained a client lease but did not populate the required snooping binding. These observations do not certify the feature on those tested combinations, and no passing source-guard receipt is published. Alternative platform/configuration work stays outside the verified suite until legitimate-source, alternate-source, enforcement and recovery gates all pass.

The tooling understands the documented Catalyst model port/RAM declarations and can reserve one larger case explicitly. This is framework capability, not a feature certificate. Q200 needs 12 GiB per switch and UADP 18 GiB; the [Cisco model page](https://developer.cisco.com/docs/modeling-labs/cat-9000v/) identifies these virtual platforms as beta.

## Resilience scope

The dual-stack campus requires separate IPv4/IPv6 HSRP group observations plus actual traffic through the virtual next hops. The enterprise-edge exercise additionally resets provider-side counters to observe the request path; a successful ping alone cannot establish which provider carried it. Equivalent provider/core loopbacks model an available equivalent endpoint, not stateful application continuity.

The tracked-campus exercise uses IOSv gateway routers because the tested IOL-L2 image did not expose the route-object tracking operational command. Its access switch SVI is an explicitly modeled traffic source, not a workstation or a physical-radio client. Gateway and route health are tested independently of local LAN availability.

CML virtual images have model-specific feature and resource limits. [Cisco reference-platform guidance](https://developer.cisco.com/docs/modeling-labs/vm-images-for-cml-labs/) explains why configured hardware features and throughput claims require separate care; these exercises assert only their recorded functional behaviors.

## Native simulated Wi-Fi

The recorded April 2026 Ubuntu Wireless AP/client models passed actual hostapd/wpa_supplicant association and interface-bound traffic tests. Both Ethernet ports are unwired. An SSID mismatch must prevent association and traffic through a complete observation window; a wrong WPA2 key must prevent completed authentication and traffic. Repair must recover three actual replies. The WPA2 exercise also requires the reported RSN key management and both CCMP ciphers to match its profile.

An 802.11 association during a failed key handshake does not establish authorized data access. The negative WPA2 check therefore distinguishes the kernel association from completed supplicant authentication. The helper signals only its recorded daemon PID with the expected executable and configuration path, retaining unrelated processes.

These fixtures use root-owned cloud-init files and verify successful initialization before testing. Files owned by a newly created user can instead require [deferred writing](https://docs.cloud-init.io/en/latest/reference/yaml_examples/write_files.html#defer-writing-content). The classroom PSK is public; the exercises cover protocol behavior, with no production key-management claim.

For these stock wireless definitions, the editable seed files are `user-data`, followed by `network-config`. The controller generates read-only `meta-data`; providing that file in a topology does not preserve it through export. Validation rejects that ignored file and reordered seeds so an imported topology must retain the configuration actually reviewed and tested.

The WLAN/VLAN exercise additionally bridges the AP radio to a real Linux 802.1Q uplink connected to an IOL-L2 trunk. Actual switch learning and client-to-SVI traffic must follow VLAN10; moving only the uplink to VLAN20 must break that traffic while radio association and the independent untagged control path survive. Repair must recover forwarding. This tests a transparent bridge/trunk teaching model; it does not certify Cisco wireless-controller VLAN policy or CAPWAP.

The guest WLAN exercise instead uses an exact IPv4 ingress routing-policy prohibition for one forwarded internal service. Three fresh guest connections must receive explicit network-policy rejection while WPA2/CCMP, the shared HTTP endpoint and independent internal-server controls remain healthy. A refused connection, timeout or authentication failure does not count as isolation. Withdrawing only the rule must permit actual HTTP and ICMP; restoring it must recover denial. The earlier local-table lookup leaves AP-local input outside this forwarded-service policy, as described in the [ip-rule manual](https://man7.org/linux/man-pages/man8/ip-rule.8.html).

[Cisco's wireless release notes](https://developer.cisco.com/docs/modeling-labs/cml-release-notes/) describe the virtual radio support as beta. Displayed bitrate, signal and packet timing are simulated observations. The tests do not establish RF coverage, physical performance, EAP/RADIUS, WPA3, PMF, the separate vAP image or Catalyst 9800 integration.

## Device-backed teaching controller

The controller exercises use separate client, service and CSR1000v guests. Northbound HTTP crosses its own benchmark link; the service collects real RESTCONF facts and changes one actual route through key-pinned NETCONF. Independent IOS RIB and ICMP checks establish forwarding. The recorded cases cover controller-process loss with continued forwarding, externally introduced route drift, off-link next-hop diagnosis, backend HTTPS loss without empty successful inventory, and approved reconciliation.

The application capstone additionally records a real withdrawal before its explicit application confirmation fault, then verifies compensation through a fresh device session. Service restart retains successful and failed jobs and ordered lifecycle history. Concurrent duplicates yield one fresh operation and one completed replay. The `changed` job field describes the before/desired difference; confirmed device observations and independent traffic controls establish the actual outcome. Failed or unverified compensation is never a successful job.

Recovery of a pending job after interruption is covered by a local model test. The CML restart receipt covers completed/failed job retention and replay; it does not establish arbitrary power-loss recovery. SQLite state and the operation lock belong to one owned service process. The public northbound token and local fixture approvals are classroom mechanisms. These local application exercises have their stated scope even where a historical filename mentions Catalyst Center; they are not receipts for a proprietary controller API or a distributed production service.

## Kernel MACsec

The recorded native net-tools pair uses the actual software SecY with strict GCM-AES-128, explicit SCI, replay protection and a 16-byte ICV. Each acceptance window couples interface-bound traffic with fresh expected-peer encrypted Ethernet frames and per-association receive-counter deltas. The wrong-key association must produce zero protected replies and new `InPktsNotValid` events while both plain underlay directions remain healthy. Selecting the retained SA0 must recover delivery without resetting its transmit packet number.

The classroom keys are public teaching vectors. Fresh locally administered MACs provide fresh SCIs for configured copies; peer SCI learning assumes the exclusive two-endpoint exercise link. This does not provide production key distribution, peer authentication, MKA or physical offload. The [ip-macsec manual](https://man7.org/linux/man-pages/man8/ip-macsec.8.html) explains the key/IV reuse constraint. Header parsing is wire observation; the kernel counters and actual forwarding tests establish the recorded cryptographic outcome. Native containers depend on their execution kernel, whose release is included in observations.

## IPv6 RA guard and learned routing state

ENARSI026 uses a native three-port software frame guard and three separate Ubuntu VMs. Both advertisers enable guest IPv6 forwarding so their kernel Neighbor Advertisements retain router status. A native host-only advertiser in the first unaccepted trial did not retain the learned default throughout subsequent checks; that trial is not functional acceptance evidence. The accepted VM topology requires an explicit 6656 MiB lab budget.

The guard validates the declared untagged IPv6 RA scope, including checksum, source, hop limit and bounded extension-header parsing. Actual untrusted RAs behind a Hop-by-Hop header must be blocked while connected IPv6 traffic still works. Withdrawing filtering must let the client kernel select the higher-preference rogue default. Restoring filtering alone does not remove a route already learned: the client explicitly removes that observed RA route before fresh advertisements prove it cannot return. Route selection uses an actual kernel lookup, not Internet traffic. This is not a Cisco ASIC, SEND, DHCPv6 or comprehensive first-hop-security implementation.

## Central SSH AAA and accounting

SCOR011 and ENCOR033 use the IOL image's actual VTY0-4 range. Acceptance reads the live login, exec-authorization, accounting and source-filter bindings before attempting network sessions; an accepted import alone does not establish that startup commands were applied. Network viewer sessions have privilege1, with no local viewer or if-authenticated fallback. The serial console remains a separate privileged recovery path in the disposable guest.

The authentication RADIUS group requests and validates Message-Authenticator, and FreeRADIUS requires it for Access-Request authentication. A separate accounting group uses the legacy RADIUS Request Authenticator. The initial combined-group trial produced invalid-Message-Authenticator accounting diagnostics in the tested IOL/FreeRADIUS image combination. This separation is an explicit interoperability boundary, not RadSec or a production transport recommendation. Cisco's [authenticator troubleshooting guide](https://www.cisco.com/c/en/us/support/docs/security-vpn/remote-authentication-dial-user-service-radius/118673-technote-radius-00.html) distinguishes the accounting authenticator from authentication Message-Authenticator.

Accounting acceptance requires actual fresh viewer Start/Stop records with the same session identifier. The fixture clears only its own regular log files before the measured session and preserves their ownership and permissions. Authentication success, log-file existence, unmatched events and duplicate copies alone cannot pass. Both RADIUS and TACACS+ sessions must demonstrate privilege1, denied configuration, wrong-password rejection and subsequent recovery from the controlled TACACS+ key mismatch. ENCOR033 additionally withdraws and restores only the VTY source filter against a separately routed client. Command accounting and a commercial ISE installation are outside these exercises.
