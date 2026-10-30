# Dual ISP BGP Edge

## Scope and prerequisites

Three isolated IOL-XE routers implement an enterprise edge and two independent eBGP provider ASes. Both providers own the same isolated service loopback203.0.113.9, deliberately modeling a replicated service identity rather than Internet reachability. The edge exports only its own probe loopback and accepts only the service prefix. Local preference200 versus100 selects the primary. Peer shutdown must change the actual RIB next hop and preserve the same source-loopback service probe. The backup also advertises203.0.113.66; retained received-routes prove it exists before an intentional prefix-list expansion admits it. Removing that expansion must withdraw it again while the expected service stays healthy. All sessions and prefixes remain inside the isolated lab. Nominal RAM is3GiB.

Use licensed reference images for iol-xe in CML 2.10.1. All addresses are educational. No Internet, external connector or production credentials are required. Starting state: Working isolated reference baseline. Functional status and exact tested images: [results](../../validation/RESULTS.md).

## Topology and addressing

- EDGE Ethernet0/0 <-> ISP1 Ethernet0/0
- EDGE Ethernet0/1 <-> ISP2 Ethernet0/0

| Node | Interface | Address |
| --- | --- | --- |
| EDGE | Loopback0 | `ip address 192.0.2.1 255.255.255.255` |
| EDGE | Ethernet0/0 | `ip address 198.18.0.1 255.255.255.252` |
| EDGE | Ethernet0/1 | `ip address 198.18.0.5 255.255.255.252` |
| ISP1 | Ethernet0/0 | `ip address 198.18.0.2 255.255.255.252` |
| ISP1 | Loopback0 | `ip address 203.0.113.9 255.255.255.255` |
| ISP2 | Ethernet0/0 | `ip address 198.18.0.6 255.255.255.252` |
| ISP2 | Loopback0 | `ip address 203.0.113.9 255.255.255.255` |
| ISP2 | Loopback1 | `ip address 203.0.113.66 255.255.255.255` |

## Tasks

1. Inspect two real eBGP service paths and the primary local-preference decision.
2. Administratively remove only the primary BGP peer and prove backup forwarding.
3. Expose and repair an inbound prefix-policy mistake while preventing enterprise transit export.

## Baseline acceptance

| Node | Command | Observable result |
| --- | --- | --- |
| EDGE | `show ip route 203.0.113.9` | The primary provider is the actual installed service path. |
| EDGE | `show ip bgp 203.0.113.9` | Both post-policy provider paths actually exist with the expected local preferences; received-only copies are not counted as extra providers. |
| EDGE | `ping 203.0.113.9 source Loopback0 repeat 3` | The selected provider actually returns the service probe. |
| EDGE | `show ip route 203.0.113.66` | The unrelated provider prefix is absent from the edge RIB. |
| EDGE | `show ip bgp neighbors 198.18.0.6 received-routes` | The backup really advertises the filtered prefix; absence is a policy result. |

## Transition: remove only the primary BGP session

On **EDGE**:

```ios
configure terminal
router bgp 65000
neighbor 198.18.0.2 shutdown
end
```

- EDGE: `show ip route 203.0.113.9` -- The backup provider becomes the actual installed path.
- EDGE: `ping 203.0.113.9 source Loopback0 repeat 3` -- The selected provider actually returns the service probe.

## Transition: restore the preferred provider

On **EDGE**:

```ios
configure terminal
router bgp 65000
no neighbor 198.18.0.2 shutdown
end
```

- EDGE: `show ip route 203.0.113.9` -- The primary provider is the actual installed service path.
- EDGE: `ping 203.0.113.9 source Loopback0 repeat 3` -- The selected provider actually returns the service probe.

## Transition: admit an unintended provider prefix

On **EDGE**:

```ios
configure terminal
ip prefix-list SERVICE-ONLY seq 20 permit 203.0.113.66/32
do clear ip bgp 198.18.0.6 soft in
end
```

- EDGE: `show ip route 203.0.113.66` -- The policy error installs the backup-only prefix.
- EDGE: `ping 203.0.113.66 source Loopback0 repeat 3` -- The unintended prefix really forwards traffic.

## Transition: restore the strict import allowlist

On **EDGE**:

```ios
configure terminal
no ip prefix-list SERVICE-ONLY seq 20 permit 203.0.113.66/32
do clear ip bgp 198.18.0.6 soft in
end
```

- EDGE: `show ip route 203.0.113.66` -- The unrelated provider prefix is absent from the edge RIB.
- EDGE: `show ip route 203.0.113.9` -- The primary provider is the actual installed service path.
- EDGE: `ping 203.0.113.9 source Loopback0 repeat 3` -- The selected provider actually returns the service probe.

## Reference configuration and recovery

The checked-in topology carries the reference configurations below. To reset a disposable exercise, stop and wipe only your imported copy, then restart or import the YAML again. Never apply the fault actions to a production device. Fault transitions restore the routing baseline; file-copy exercises may leave their documented output until wipe. Repeat the applicable acceptance checks before ending the exercise.

### EDGE

```ios
hostname EDGE
no ip domain-lookup
no service config
ip cef
line console 0
 exec-timeout 0 0
 logging synchronous
 exit
interface range Ethernet0/0 - 3
 no ip address
 shutdown
 exit
interface Loopback0
 ip address 192.0.2.1 255.255.255.255
 no shutdown
 exit
interface Ethernet0/0
 ip address 198.18.0.1 255.255.255.252
 no shutdown
 exit
interface Ethernet0/1
 ip address 198.18.0.5 255.255.255.252
 no shutdown
 exit
ip prefix-list EDGE-ONLY seq 10 permit 192.0.2.1/32
ip prefix-list SERVICE-ONLY seq 10 permit 203.0.113.9/32
route-map PRIMARY-IN permit 10
 match ip address prefix-list SERVICE-ONLY
 set local-preference 200
 exit
route-map SECONDARY-IN permit 10
 match ip address prefix-list SERVICE-ONLY
 set local-preference 100
 exit
router bgp 65000
 bgp router-id 192.0.2.1
 network 192.0.2.1 mask 255.255.255.255
 neighbor 198.18.0.2 remote-as 65001
 neighbor 198.18.0.2 route-map PRIMARY-IN in
 neighbor 198.18.0.2 prefix-list EDGE-ONLY out
 neighbor 198.18.0.2 soft-reconfiguration inbound
 neighbor 198.18.0.6 remote-as 65002
 neighbor 198.18.0.6 route-map SECONDARY-IN in
 neighbor 198.18.0.6 prefix-list EDGE-ONLY out
 neighbor 198.18.0.6 soft-reconfiguration inbound
 exit
end
```

### ISP1

```ios
hostname ISP1
no ip domain-lookup
no service config
ip cef
line console 0
 exec-timeout 0 0
 logging synchronous
 exit
interface range Ethernet0/0 - 3
 no ip address
 shutdown
 exit
interface Ethernet0/0
 ip address 198.18.0.2 255.255.255.252
 no shutdown
 exit
interface Loopback0
 ip address 203.0.113.9 255.255.255.255
 no shutdown
 exit
router bgp 65001
 bgp router-id 192.0.2.2
 neighbor 198.18.0.1 remote-as 65000
 network 203.0.113.9 mask 255.255.255.255
 exit
end
```

### ISP2

```ios
hostname ISP2
no ip domain-lookup
no service config
ip cef
line console 0
 exec-timeout 0 0
 logging synchronous
 exit
interface range Ethernet0/0 - 3
 no ip address
 shutdown
 exit
interface Ethernet0/0
 ip address 198.18.0.6 255.255.255.252
 no shutdown
 exit
interface Loopback0
 ip address 203.0.113.9 255.255.255.255
 no shutdown
 exit
interface Loopback1
 ip address 203.0.113.66 255.255.255.255
 no shutdown
 exit
router bgp 65002
 bgp router-id 192.0.2.3
 neighbor 198.18.0.5 remote-as 65000
 network 203.0.113.9 mask 255.255.255.255
 network 203.0.113.66 mask 255.255.255.255
 exit
end
```

## Platform scope

Use the [reference-platform guide](../PLATFORMS.md) for the node models named by this workbook. Exact tested CML and image versions are recorded in the [results](../../validation/RESULTS.md). The checks verify the listed protocol and forwarding behavior, not hardware throughput, physical failure timing or complete certification coverage.
