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

[Cisco's wireless release notes](https://developer.cisco.com/docs/modeling-labs/cml-release-notes/) describe the virtual radio support as beta. Displayed bitrate, signal and packet timing are simulated observations. The tests do not establish RF coverage, physical performance, EAP/RADIUS, WPA3, PMF, the separate vAP image or Catalyst 9800 integration.
