# WLAN Client Mapping: Radio, Bridge and Tagged VLAN

## Scope and prerequisites

A native Ubuntu Wireless AP and client exchange actual frames over the CML simulated radio. Only the AP ens2 is wired, to Ethernet0/0 on an IOL-L2 switch. The AP bridges wlan0 to an 802.1Q subinterface; neither the WLAN port nor bridge has an IPv4 endpoint. The client 198.18.10.2/24 must reach the actual switch VLAN10 SVI 198.18.10.1/24. An independent untagged control subnet connects AP ens2 198.18.0.1/30 to switch VLAN1 198.18.0.2/30. The switch trunk permits VLANs 1, 10 and 20. VLAN20 deliberately has no SVI.

The controlled fault moves only the WLAN bridge uplink from VLAN10 to VLAN20. Client addressing, completed radio association, AP operation and the untagged control path must remain healthy, while fresh client ARP/ICMP can no longer reach the VLAN10 SVI. Dynamic MAC learning must be observed on the newly selected VLAN. Restoring VLAN10 must recover actual traffic. Neighbor caches are flushed before data tests so an old ARP entry cannot hide a wrong VLAN. This is a Linux bridge/trunk teaching model: no Cisco controller, CAPWAP tunnel, WPA authentication, RF-performance or production segmentation claim. The open WLAN is deliberate. Nominal RAM is 5120 MiB, requiring the explicitly reserved larger-case test mode.

Use licensed reference images for ioll2-xe, wireless-ap, wireless-client in CML 2.10.1. All addresses are educational. No Internet, external connector or production credentials are required. Starting state: Working isolated reference baseline. Functional status and exact tested images: [results](../../validation/RESULTS.md).

## Topology and addressing

- AP ens2 <-> SW Ethernet0/0

| Node | Interface | Address |
| --- | --- | --- |
| AP | ens2 (untagged control) | 198.18.0.1/30 |
| AP | wlan0 / br0 | Transparent L2 bridge, no IPv4 address |
| AP | v10 / v20 | Tagged ens2 VLAN10 / VLAN20; only one belongs to br0 |
| CLIENT | wlan0 | 198.18.10.2/24 |
| SW | Vlan1 | `ip address 198.18.0.2 255.255.255.252` |
| SW | Vlan10 | `ip address 198.18.10.1 255.255.255.0` |

## Tasks

1. Correlate actual radio association, a transparent WLAN bridge, 802.1Q uplink selection and switch learning.
2. Introduce an incorrect VLAN mapping while retaining wireless and independent uplink health.
3. Observe failed fresh traffic, restore VLAN10 and prove end-to-end forwarding again.

## Baseline acceptance

| Node | Command | Observable result |
| --- | --- | --- |
| CLIENT | `python3 /lab/v.py check` | Actual WLAN association stays completed; three fresh interface-bound requests receive all replies from the switch VLAN10 SVI. |
| AP | `python3 /lab/v.py check --vlan 10` | Actual AP state, bridge port/tag selection and three independent untagged uplink replies agree. |
| SW | `show mac address-table dynamic vlan 10` | The switch actually learns a dynamic source in the selected tagged VLAN on the AP trunk. |

## Transition: map the WLAN to the wrong tagged VLAN

On **AP**:

```ios
python3 /lab/v.py map --vlan 20
```

- AP: `python3 /lab/v.py check --vlan 20` -- Actual AP state, bridge port/tag selection and three independent untagged uplink replies agree.
- CLIENT: `python3 /lab/v.py check --expect down` -- Actual WLAN association stays completed; three fresh interface-bound requests receive zero replies after neighbor-cache flushing.
- SW: `show mac address-table dynamic vlan 20` -- The switch actually learns a dynamic source in the selected tagged VLAN on the AP trunk.

## Transition: restore the WLAN VLAN10 uplink

On **AP**:

```ios
python3 /lab/v.py map --vlan 10
```

- CLIENT: `python3 /lab/v.py check` -- Actual WLAN association stays completed; three fresh interface-bound requests receive all replies from the switch VLAN10 SVI.
- AP: `python3 /lab/v.py check --vlan 10` -- Actual AP state, bridge port/tag selection and three independent untagged uplink replies agree.
- SW: `show mac address-table dynamic vlan 10` -- The switch actually learns a dynamic source in the selected tagged VLAN on the AP trunk.

## Reference configuration and recovery

The checked-in topology carries the reference configurations below. To reset a disposable exercise, stop and wipe only your imported copy, then restart or import the YAML again. Never apply the fault actions to a production device. Fault transitions restore the routing baseline; file-copy exercises may leave their documented output until wipe. Repeat the applicable acceptance checks before ending the exercise.

### Wireless guests

The YAML embeds the root-owned cloud-init files. Readable sources: [radio protocol checks](../../examples/wireless/radio_probe.py) and [bridge/VLAN fixture](../../examples/wireless/vlan_probe.py). Embedded bytes are checked automatically. The only cable is the AP-to-switch trunk; the client has no wired path.

### SW

```ios
hostname SW
no ip domain-lookup
no service config
ip cef
line console 0
 exec-timeout 0 0
 logging synchronous
 exit
vtp mode transparent
spanning-tree mode rapid-pvst
interface range Ethernet0/0 - 3
 shutdown
 exit
no logging console
ip routing
vlan 10
 name WLAN
 exit
vlan 20
 name WRONG-MAPPING
 exit
interface Ethernet0/0
 switchport trunk encapsulation dot1q
 switchport mode trunk
 switchport trunk native vlan 1
 switchport trunk allowed vlan 1,10,20
 spanning-tree portfast trunk
 no shutdown
 exit
interface Vlan1
 ip address 198.18.0.2 255.255.255.252
 no shutdown
 exit
interface Vlan10
 ip address 198.18.10.1 255.255.255.0
 no shutdown
 exit
end
```

## Platform scope

Use the [reference-platform guide](../PLATFORMS.md) for the node models named by this workbook. Exact tested CML and image versions are recorded in the [results](../../validation/RESULTS.md). The checks verify the listed protocol and forwarding behavior, not hardware throughput, physical failure timing or complete certification coverage.
