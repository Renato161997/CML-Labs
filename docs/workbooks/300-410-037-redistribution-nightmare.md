# Redistribution Nightmare

## Scope and prerequisites

Four IOL-XE routers form two routing domains with two ASBRs. The live service is LEFT Loopback100203.0.113.100/32; LEFT Loopback0192.0.2.1/32 is an independent healthy control. Explicit prefix lists limit redistribution to the exercise endpoints. OSPF-origin routes receive tag100 in EIGRP; EIGRP-origin routes receive tag200 in OSPF. Both boundaries initially reject returned-origin tags. B3 external EIGRP distance is deliberately lowered to90 before removing its E2O tag100 rejection and B2 O2E tag200 rejection. Both sides of the returned-origin protection must be disabled to sustain feedback. Acceptance requires the changed route selection and an actual external LSA advertised by B3, not just configuration presence. With the original service interface shut down, a route must persist through redistribution feedback while the real service fails and the independent endpoint remains healthy. Restoring the tag guard and normal distance must withdraw that ghost route before the service is restored. This is a bounded four-router control-plane feedback exercise, not a production convergence or general loop-freedom proof. Nominal RAM is4GiB.

Use licensed reference images for iol-xe in CML 2.10.1. All addresses are educational. No Internet, external connector or production credentials are required. Starting state: Working isolated reference baseline. Functional status and exact tested images: [results](../../validation/RESULTS.md).

## Topology and addressing

- LEFT Ethernet0/0 <-> B2 Ethernet0/0
- LEFT Ethernet0/1 <-> B3 Ethernet0/0
- B2 Ethernet0/1 <-> RIGHT Ethernet0/0
- B3 Ethernet0/1 <-> RIGHT Ethernet0/1

| Node | Interface | Address |
| --- | --- | --- |
| LEFT | Loopback0 | `ip address 192.0.2.1 255.255.255.255` |
| LEFT | Loopback100 | `ip address 203.0.113.100 255.255.255.255` |
| LEFT | Ethernet0/0 | `ip address 198.18.12.1 255.255.255.252` |
| LEFT | Ethernet0/1 | `ip address 198.18.13.1 255.255.255.252` |
| B2 | Loopback0 | `ip address 192.0.2.2 255.255.255.255` |
| B2 | Ethernet0/0 | `ip address 198.18.12.2 255.255.255.252` |
| B2 | Ethernet0/1 | `ip address 198.18.24.1 255.255.255.252` |
| B3 | Loopback0 | `ip address 192.0.2.3 255.255.255.255` |
| B3 | Ethernet0/0 | `ip address 198.18.13.2 255.255.255.252` |
| B3 | Ethernet0/1 | `ip address 198.18.34.1 255.255.255.252` |
| RIGHT | Loopback0 | `ip address 192.0.2.4 255.255.255.255` |
| RIGHT | Ethernet0/0 | `ip address 198.18.24.2 255.255.255.252` |
| RIGHT | Ethernet0/1 | `ip address 198.18.34.2 255.255.255.252` |

## Tasks

1. Trace a real OSPF-origin service through two independent OSPF/EIGRP redistribution boundaries.
2. Change the second boundary external administrative distance, then remove its origin-tag export guard and observe an actual reflected external LSA.
3. Withdraw the original service and distinguish a persistent feedback route from real reachability; repair origin filtering and distance before restoring service.

## Baseline acceptance

| Node | Command | Observable result |
| --- | --- | --- |
| RIGHT | `show ip route 203.0.113.100` | The service is a real tagged external EIGRP route. |
| B3 | `show ip route 203.0.113.100` | Normal administrative distance selects the native OSPF route. |
| RIGHT | `ping 203.0.113.100 source Loopback0 repeat 3` | Actual endpoint traffic succeeds. |
| RIGHT | `ping 192.0.2.1 source Loopback0 repeat 3` | Actual endpoint traffic succeeds. |

## Transition: prefer the returned external route but retain its export guard

On **B3**:

```ios
configure terminal
router eigrp 100
distance eigrp 90 90
end
```

- B3: `show ip route 203.0.113.100` -- The changed external distance actually selects the returned tagged EIGRP route.
- RIGHT: `ping 203.0.113.100 source Loopback0 repeat 3` -- Actual endpoint traffic succeeds.
- RIGHT: `ping 192.0.2.1 source Loopback0 repeat 3` -- Actual endpoint traffic succeeds.

## Transition: remove the origin-tag export guard

On **B3**:

```ios
configure terminal
no route-map E2O deny 10
end
```

- B3: `show ip route 203.0.113.100` -- The changed external distance actually selects the returned tagged EIGRP route.
- B2: `show ip ospf database external 203.0.113.100` -- The second boundary has actually reflected the OSPF-origin prefix into an external OSPF LSA.
- RIGHT: `ping 203.0.113.100 source Loopback0 repeat 3` -- Actual endpoint traffic succeeds.
- RIGHT: `ping 192.0.2.1 source Loopback0 repeat 3` -- Actual endpoint traffic succeeds.

## Transition: remove the second returned-origin guard

On **B2**:

```ios
configure terminal
no route-map O2E deny 10
end
```

- B2: `show ip ospf database external 203.0.113.100` -- The second boundary has actually reflected the OSPF-origin prefix into an external OSPF LSA.
- RIGHT: `show ip route 203.0.113.100` -- The service is a real tagged external EIGRP route.
- RIGHT: `ping 203.0.113.100 source Loopback0 repeat 3` -- Actual endpoint traffic succeeds.
- RIGHT: `ping 192.0.2.1 source Loopback0 repeat 3` -- Actual endpoint traffic succeeds.

## Transition: withdraw the real service and observe persistent feedback

On **LEFT**:

```ios
configure terminal
interface Loopback100
shutdown
end
```

- B2: `show ip ospf database external 203.0.113.100` -- The second boundary has actually reflected the OSPF-origin prefix into an external OSPF LSA.
- RIGHT: `show ip route 203.0.113.100` -- The service is a real tagged external EIGRP route.
- RIGHT: `ping 203.0.113.100 source Loopback0 repeat 3` -- Actual endpoint traffic cannot reach the withdrawn service.
- RIGHT: `ping 192.0.2.1 source Loopback0 repeat 3` -- Actual endpoint traffic succeeds.
- RIGHT: `show ip route 203.0.113.100` -- The ghost route remains after the failed data-plane probes.

## Transition: repair origin rejection and normal external distance

On **B3**:

```ios
configure terminal
route-map E2O deny 10
match tag 100
exit
router eigrp 100
distance eigrp 90 170
end
```

- RIGHT: `show ip route 203.0.113.100` -- After the return-export guard is repaired the withdrawn service route disappears.
- RIGHT: `ping 203.0.113.100 source Loopback0 repeat 3` -- Actual endpoint traffic cannot reach the withdrawn service.
- RIGHT: `ping 192.0.2.1 source Loopback0 repeat 3` -- Actual endpoint traffic succeeds.

## Transition: restore the second returned-origin guard

On **B2**:

```ios
configure terminal
route-map O2E deny 10
match tag 200
end
```

- RIGHT: `show ip route 203.0.113.100` -- After the return-export guard is repaired the withdrawn service route disappears.
- RIGHT: `ping 192.0.2.1 source Loopback0 repeat 3` -- Actual endpoint traffic succeeds.

## Transition: restore the actual service

On **LEFT**:

```ios
configure terminal
interface Loopback100
no shutdown
end
```

- RIGHT: `show ip route 203.0.113.100` -- The service is a real tagged external EIGRP route.
- B3: `show ip route 203.0.113.100` -- Normal administrative distance selects the native OSPF route.
- RIGHT: `ping 203.0.113.100 source Loopback0 repeat 3` -- Actual endpoint traffic succeeds.
- RIGHT: `ping 192.0.2.1 source Loopback0 repeat 3` -- Actual endpoint traffic succeeds.

## Reference configuration and recovery

The checked-in topology carries the reference configurations below. To reset a disposable exercise, stop and wipe only your imported copy, then restart or import the YAML again. Never apply the fault actions to a production device. Fault transitions restore the routing baseline; file-copy exercises may leave their documented output until wipe. Repeat the applicable acceptance checks before ending the exercise.

### LEFT

```ios
hostname LEFT
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
interface Loopback100
 ip address 203.0.113.100 255.255.255.255
 no shutdown
 exit
interface Ethernet0/0
 ip address 198.18.12.1 255.255.255.252
 no shutdown
 exit
interface Ethernet0/1
 ip address 198.18.13.1 255.255.255.252
 no shutdown
 exit
router ospf 1
 router-id 192.0.2.1
 passive-interface default
 no passive-interface Ethernet0/0
 no passive-interface Ethernet0/1
 no passive-interface Loopback0
 no passive-interface Loopback100
 exit
interface Ethernet0/0
 ip ospf 1 area 0
 ip ospf network point-to-point
 exit
interface Ethernet0/1
 ip ospf 1 area 0
 ip ospf network point-to-point
 exit
interface Loopback0
 ip ospf 1 area 0
 ip ospf network point-to-point
 exit
interface Loopback100
 ip ospf 1 area 0
 ip ospf network point-to-point
 exit
end
```

### B2

```ios
hostname B2
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
 ip address 192.0.2.2 255.255.255.255
 no shutdown
 exit
interface Ethernet0/0
 ip address 198.18.12.2 255.255.255.252
 no shutdown
 exit
interface Ethernet0/1
 ip address 198.18.24.1 255.255.255.252
 no shutdown
 exit
ip prefix-list OSPF-ENDPOINTS permit 192.0.2.1/32
ip prefix-list OSPF-ENDPOINTS permit 203.0.113.100/32
ip prefix-list ALL-ENDPOINTS permit 192.0.2.1/32
ip prefix-list ALL-ENDPOINTS permit 192.0.2.4/32
ip prefix-list ALL-ENDPOINTS permit 203.0.113.100/32
route-map O2E deny 10
 match tag 200
 exit
route-map O2E permit 20
 match ip address prefix-list OSPF-ENDPOINTS
 set tag 100
 exit
route-map E2O deny 10
 match tag 100
 exit
route-map E2O permit 20
 match ip address prefix-list ALL-ENDPOINTS
 set tag 200
 exit
router ospf 1
 router-id 192.0.2.2
 passive-interface default
 no passive-interface Ethernet0/0
 no passive-interface Loopback0
 exit
interface Ethernet0/0
 ip ospf 1 area 0
 ip ospf network point-to-point
 exit
interface Loopback0
 ip ospf 1 area 0
 ip ospf network point-to-point
 exit
router ospf 1
 redistribute eigrp 100 subnets route-map E2O
 exit
router eigrp 100
 eigrp router-id 192.0.2.2
 no auto-summary
 network 198.18.24.0 0.0.0.3
 default-metric 10000 100 255 1 1500
 redistribute ospf 1 match internal external 1 external 2 route-map O2E
 exit
end
```

### B3

```ios
hostname B3
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
 ip address 192.0.2.3 255.255.255.255
 no shutdown
 exit
interface Ethernet0/0
 ip address 198.18.13.2 255.255.255.252
 no shutdown
 exit
interface Ethernet0/1
 ip address 198.18.34.1 255.255.255.252
 no shutdown
 exit
ip prefix-list OSPF-ENDPOINTS permit 192.0.2.1/32
ip prefix-list OSPF-ENDPOINTS permit 203.0.113.100/32
ip prefix-list ALL-ENDPOINTS permit 192.0.2.1/32
ip prefix-list ALL-ENDPOINTS permit 192.0.2.4/32
ip prefix-list ALL-ENDPOINTS permit 203.0.113.100/32
route-map O2E deny 10
 match tag 200
 exit
route-map O2E permit 20
 match ip address prefix-list OSPF-ENDPOINTS
 set tag 100
 exit
route-map E2O deny 10
 match tag 100
 exit
route-map E2O permit 20
 match ip address prefix-list ALL-ENDPOINTS
 set tag 200
 exit
router ospf 1
 router-id 192.0.2.3
 passive-interface default
 no passive-interface Ethernet0/0
 no passive-interface Loopback0
 exit
interface Ethernet0/0
 ip ospf 1 area 0
 ip ospf network point-to-point
 exit
interface Loopback0
 ip ospf 1 area 0
 ip ospf network point-to-point
 exit
router ospf 1
 redistribute eigrp 100 subnets route-map E2O
 exit
router eigrp 100
 eigrp router-id 192.0.2.3
 no auto-summary
 network 198.18.34.0 0.0.0.3
 default-metric 10000 100 255 1 1500
 redistribute ospf 1 match internal external 1 external 2 route-map O2E
 exit
end
```

### RIGHT

```ios
hostname RIGHT
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
 ip address 192.0.2.4 255.255.255.255
 no shutdown
 exit
interface Ethernet0/0
 ip address 198.18.24.2 255.255.255.252
 no shutdown
 exit
interface Ethernet0/1
 ip address 198.18.34.2 255.255.255.252
 no shutdown
 exit
router eigrp 100
 eigrp router-id 192.0.2.4
 no auto-summary
 network 198.18.24.0 0.0.0.3
 network 198.18.34.0 0.0.0.3
 network 192.0.2.4 0.0.0.0
 exit
end
```

## Platform scope

Use the [reference-platform guide](../PLATFORMS.md) for the node models named by this workbook. Exact tested CML and image versions are recorded in the [results](../../validation/RESULTS.md). The checks verify the listed protocol and forwarding behavior, not hardware throughput, physical failure timing or complete certification coverage.
