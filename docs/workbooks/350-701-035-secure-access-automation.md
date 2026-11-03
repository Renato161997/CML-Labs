# Secure Access Automation: Grant, Timed Revocation and Repair

## Scope and prerequisites

An actual IOSv router grants a fixed classroom source temporary TCP-8080 access and autonomously revokes it with an EEM countdown applet. Two native service peers independently measure real application/admin HTTP and routed ICMP. The initial ACL denies application and administration, permits ICMP and remains bound to the client-facing interface throughout. The privileged serial-console operator represents the classroom approval boundary; there is no user enrollment, identity provider, ZTNA cloud, northbound request API or production access broker. Source IPv4 is not authenticated user identity.

After the operator's explicit source/port grant, the router registers a one-shot 45-second EEM timer. Application HTTP must actually succeed before expiry while administration remains blocked and both local listeners stay healthy. The acceptance script then waits fifty monotonic seconds in a separate endpoint, after which the router must have restored the deny rule and actual application requests must fail. A unique per-phase buffered-log marker emitted after the CLI actions and the actual EEM event history accompany the packet evidence. These observations establish the tested expiry outcome; no real-time scheduling guarantee or sub-second timing precision is claimed.

Removing the applet and deliberately regranting the same source is a negative control: after another fifty seconds, application access must still work. Therefore a static firewall rule or a failed endpoint cannot masquerade as autonomous expiry. Re-registering the countdown with a distinct second marker must revoke that still-working grant again, with admin denial, ICMP and service controls preserved. No client traffic or operator follow-up is required to trigger expiry once the timer is armed. The timer is one-shot and is explicitly removed before re-registration; the reference ends with application access denied.

The ACL grants the fixed source TCP port 8080 to any routed destination; in this closed topology the only such service is OUTSIDE 198.18.20.20. It must not be treated as a production per-resource or per-person policy. The CLI edits remove/re-add one ACL sequence while the ACL stays defined; this is not an atomic transaction or a proof of zero transient packet loss. An unarmed timer, router restart, timer-service failure or operator/root changes can invalidate the lifetime policy. This is device-local time-bound access automation, not a durable distributed lease system. The [Cisco IOS EEM timer reference](https://www.cisco.com/c/en/us/td/docs/ios-xml/ios/eem/command/eem-cr-book/eem-cr-e2.html) documents countdown and one-shot behavior. IOL-XE lacks this tested EEM implementation, so IOSv is required. No external connector, real account, production secret or original user lab is used.


Use licensed reference images for iosv, net-tools in CML 2.10.1. All addresses are educational. No Internet, external connector or production credentials are required. Starting state: Working isolated reference baseline. Functional status and exact tested images: [results](../../validation/RESULTS.md).

## Topology and addressing

- FW GigabitEthernet0/0 <-> INSIDE eth1
- FW GigabitEthernet0/1 <-> OUTSIDE eth1

| Node | Interface | Address |
| --- | --- | --- |
| FW | GigabitEthernet0/0 | `ip address 198.18.10.1 255.255.255.0` |
| FW | GigabitEthernet0/1 | `ip address 198.18.20.1 255.255.255.0` |
| INSIDE | eth1 | `198.18.10.10/24` |
| OUTSIDE | eth1 | `198.18.20.20/24` |

## Tasks

1. Grant a fixed source temporary real application access while preserving admin denial and positive controls.
2. Observe autonomous IOSv EEM countdown expiry with actual packet denial and unique execution evidence.
3. Remove the automation as a negative control, prove access persists, then restore the timer and revoke it again.

## Baseline acceptance

| Node | Command | Observable result |
| --- | --- | --- |
| INSIDE | `python3 /lab/t.py probe 198.18.20.20` | The actual plain-HTTP connection is blocked while its separately checked server stays healthy. |
| INSIDE | `python3 /lab/t.py probe 198.18.20.20 --port 9090` | The actual plain-HTTP connection is blocked while its separately checked server stays healthy. |
| OUTSIDE | `python3 /lab/t.py probe 198.18.20.20` | The actual plain-HTTP connection succeeds with the expected observed peer. |
| OUTSIDE | `python3 /lab/t.py probe 198.18.20.20 --port 9090` | The actual plain-HTTP connection succeeds with the expected observed peer. |
| INSIDE | `ping -n -c 3 -W 1 198.18.20.20` | The routed control path remains healthy independently of time-limited application access. |
| FW | `show ip interface GigabitEthernet0/0 | include Inbound` | The actual ingress ACL stays bound through grant, expiry and the missing-automation negative control. |

## Transition: grant the classroom source and arm the first expiry

On **FW**:

```ios
configure terminal
ip access-list extended ACCESS-IN
no 10
10 permit tcp host 198.18.10.10 any eq 8080
exit
event manager applet EXPIRE-ACCESS
event timer countdown time 45
action 1.0 cli command "enable"
action 2.0 cli command "configure terminal"
action 3.0 cli command "ip access-list extended ACCESS-IN"
action 4.0 cli command "no 10"
action 5.0 cli command "10 deny tcp host 198.18.10.10 any eq 8080"
action 6.0 cli command "end"
action 7.0 syslog msg "CML-ACCESS-FIRST-EXPIRED"
exit
end
```

- INSIDE: `python3 /lab/t.py probe 198.18.20.20` -- The actual plain-HTTP connection succeeds with the expected observed peer.
- INSIDE: `python3 /lab/t.py probe 198.18.20.20 --port 9090` -- The actual plain-HTTP connection is blocked while its separately checked server stays healthy.
- OUTSIDE: `python3 /lab/t.py probe 198.18.20.20` -- The actual plain-HTTP connection succeeds with the expected observed peer.
- OUTSIDE: `python3 /lab/t.py probe 198.18.20.20 --port 9090` -- The actual plain-HTTP connection succeeds with the expected observed peer.
- INSIDE: `ping -n -c 3 -W 1 198.18.20.20` -- The routed control path remains healthy independently of time-limited application access.
- FW: `show ip interface GigabitEthernet0/0 | include Inbound` -- The actual ingress ACL stays bound through grant, expiry and the missing-automation negative control.

## Transition: observe the first autonomous expiry

On **INSIDE**:

```bash
python3 -c 'import time;time.sleep(50);print(1)'
```

- INSIDE: `python3 /lab/t.py probe 198.18.20.20` -- The actual plain-HTTP connection is blocked while its separately checked server stays healthy.
- INSIDE: `python3 /lab/t.py probe 198.18.20.20 --port 9090` -- The actual plain-HTTP connection is blocked while its separately checked server stays healthy.
- OUTSIDE: `python3 /lab/t.py probe 198.18.20.20` -- The actual plain-HTTP connection succeeds with the expected observed peer.
- OUTSIDE: `python3 /lab/t.py probe 198.18.20.20 --port 9090` -- The actual plain-HTTP connection succeeds with the expected observed peer.
- INSIDE: `ping -n -c 3 -W 1 198.18.20.20` -- The routed control path remains healthy independently of time-limited application access.
- FW: `show ip interface GigabitEthernet0/0 | include Inbound` -- The actual ingress ACL stays bound through grant, expiry and the missing-automation negative control.
- FW: `show logging | include CML-ACCESS-FIRST-EXPIRED` -- The unique phase marker is emitted only after the real EEM actions have restored application denial.
- FW: `show event manager history events` -- The actual IOSv event history records the countdown applet invocation.

## Transition: remove expiry automation and deliberately regrant access

On **FW**:

```ios
configure terminal
no event manager applet EXPIRE-ACCESS
ip access-list extended ACCESS-IN
no 10
10 permit tcp host 198.18.10.10 any eq 8080
exit
end
```

- INSIDE: `python3 /lab/t.py probe 198.18.20.20` -- The actual plain-HTTP connection succeeds with the expected observed peer.
- INSIDE: `python3 /lab/t.py probe 198.18.20.20 --port 9090` -- The actual plain-HTTP connection is blocked while its separately checked server stays healthy.
- OUTSIDE: `python3 /lab/t.py probe 198.18.20.20` -- The actual plain-HTTP connection succeeds with the expected observed peer.
- OUTSIDE: `python3 /lab/t.py probe 198.18.20.20 --port 9090` -- The actual plain-HTTP connection succeeds with the expected observed peer.
- INSIDE: `ping -n -c 3 -W 1 198.18.20.20` -- The routed control path remains healthy independently of time-limited application access.
- FW: `show ip interface GigabitEthernet0/0 | include Inbound` -- The actual ingress ACL stays bound through grant, expiry and the missing-automation negative control.

## Transition: prove a grant without automation does not expire

On **INSIDE**:

```bash
python3 -c 'import time;time.sleep(50);print(1)'
```

- INSIDE: `python3 /lab/t.py probe 198.18.20.20` -- The actual plain-HTTP connection succeeds with the expected observed peer.
- INSIDE: `python3 /lab/t.py probe 198.18.20.20 --port 9090` -- The actual plain-HTTP connection is blocked while its separately checked server stays healthy.
- OUTSIDE: `python3 /lab/t.py probe 198.18.20.20` -- The actual plain-HTTP connection succeeds with the expected observed peer.
- OUTSIDE: `python3 /lab/t.py probe 198.18.20.20 --port 9090` -- The actual plain-HTTP connection succeeds with the expected observed peer.
- INSIDE: `ping -n -c 3 -W 1 198.18.20.20` -- The routed control path remains healthy independently of time-limited application access.
- FW: `show ip interface GigabitEthernet0/0 | include Inbound` -- The actual ingress ACL stays bound through grant, expiry and the missing-automation negative control.

## Transition: restore the one-shot expiry for the still-active grant

On **FW**:

```ios
configure terminal
event manager applet EXPIRE-ACCESS
event timer countdown time 45
action 1.0 cli command "enable"
action 2.0 cli command "configure terminal"
action 3.0 cli command "ip access-list extended ACCESS-IN"
action 4.0 cli command "no 10"
action 5.0 cli command "10 deny tcp host 198.18.10.10 any eq 8080"
action 6.0 cli command "end"
action 7.0 syslog msg "CML-ACCESS-SECOND-EXPIRED"
exit
end
```

- INSIDE: `python3 /lab/t.py probe 198.18.20.20` -- The actual plain-HTTP connection succeeds with the expected observed peer.
- INSIDE: `python3 /lab/t.py probe 198.18.20.20 --port 9090` -- The actual plain-HTTP connection is blocked while its separately checked server stays healthy.
- OUTSIDE: `python3 /lab/t.py probe 198.18.20.20` -- The actual plain-HTTP connection succeeds with the expected observed peer.
- OUTSIDE: `python3 /lab/t.py probe 198.18.20.20 --port 9090` -- The actual plain-HTTP connection succeeds with the expected observed peer.
- INSIDE: `ping -n -c 3 -W 1 198.18.20.20` -- The routed control path remains healthy independently of time-limited application access.
- FW: `show ip interface GigabitEthernet0/0 | include Inbound` -- The actual ingress ACL stays bound through grant, expiry and the missing-automation negative control.

## Transition: observe fresh autonomous revocation after repair

On **INSIDE**:

```bash
python3 -c 'import time;time.sleep(50);print(1)'
```

- INSIDE: `python3 /lab/t.py probe 198.18.20.20` -- The actual plain-HTTP connection is blocked while its separately checked server stays healthy.
- INSIDE: `python3 /lab/t.py probe 198.18.20.20 --port 9090` -- The actual plain-HTTP connection is blocked while its separately checked server stays healthy.
- OUTSIDE: `python3 /lab/t.py probe 198.18.20.20` -- The actual plain-HTTP connection succeeds with the expected observed peer.
- OUTSIDE: `python3 /lab/t.py probe 198.18.20.20 --port 9090` -- The actual plain-HTTP connection succeeds with the expected observed peer.
- INSIDE: `ping -n -c 3 -W 1 198.18.20.20` -- The routed control path remains healthy independently of time-limited application access.
- FW: `show ip interface GigabitEthernet0/0 | include Inbound` -- The actual ingress ACL stays bound through grant, expiry and the missing-automation negative control.
- FW: `show logging | include CML-ACCESS-SECOND-EXPIRED` -- The unique phase marker is emitted only after the real EEM actions have restored application denial.
- FW: `show event manager history events` -- The actual IOSv event history records the countdown applet invocation.

## Reference configuration and recovery

The checked-in topology carries the reference configurations below. To reset a disposable exercise, stop and wipe only your imported copy, then restart or import the YAML again. Never apply the fault actions to a production device. Fault transitions restore the routing baseline; file-copy exercises may leave their documented output until wipe. Repeat the applicable acceptance checks before ending the exercise.

### FW

```ios
hostname FW
no ip domain-lookup
no service config
ip cef
line console 0
 exec-timeout 0 0
 logging synchronous
 exit
no logging console
logging buffered 32768 informational
ip access-list extended ACCESS-IN
 10 deny tcp host 198.18.10.10 any eq 8080
 20 deny tcp any host 198.18.20.20 eq 9090
 30 permit icmp any any
 40 deny ip any any
 exit
interface GigabitEthernet0/0
 ip address 198.18.10.1 255.255.255.0
 no shutdown
 ip access-group ACCESS-IN in
 exit
interface GigabitEthernet0/1
 ip address 198.18.20.1 255.255.255.0
 no shutdown
 exit
end
```

### Independent service probes

The [unchanged HTTP packet/peer fixture](../../examples/security/traffic_fixture.py) supplies real application/admin requests. The IOSv reference configuration and EEM CLI above implement the actual enforcement and expiry. Inspect only this imported copy. Configuration strings, elapsed time alone and a healthy local listener cannot substitute for the documented remote packet outcomes and unique expiry markers.

## Platform scope

Use the [reference-platform guide](../PLATFORMS.md) for the node models named by this workbook. Exact tested CML and image versions are recorded in the [results](../../validation/RESULTS.md). The checks verify the listed protocol and forwarding behavior, not hardware throughput, physical failure timing or complete certification coverage.
