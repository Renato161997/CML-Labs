# CML - LABS

A public collection of Cisco Modeling Labs topologies for CCNA and CCNP
Enterprise practice.

The idea is simple: clone the repo, import a `.yaml` file into CML, start the
lab, and work from the tasks embedded in the lab notes. No separate workbook is
required.

## What's inside

- 40 CCNA labs
- 41 CCNP ENCOR labs
- CML 2.x `.yaml` files only
- Embedded startup configs and lab notes
- Small topologies designed to be quick to boot and easy to modify

## How to use

1. Open Cisco Modeling Labs.
2. Import one of the `.yaml` files from `labs/`.
3. Start the lab.
4. Read the lab notes inside CML.
5. Configure, break, fix, repeat.

The labs are grouped by track and topic:

```text
labs/
  ccna/
    network-fundamentals/
    network-access/
    ip-connectivity/
    ip-services/
    security/
    automation/
  ccnp-encor/
    architecture/
    virtualization/
    infrastructure/
    network-assurance/
    security/
    automation/
```

## Node definitions

Most labs use standard CML node definitions:

- `iosv`
- `iosvl2`
- `desktop`

If your CML instance uses different node definition names, import the lab and
remap the nodes, or edit the `node_definition` fields in the YAML.

## Lab index

### CCNA

| Area | Lab |
| --- | --- |
| Network fundamentals | `labs/ccna/network-fundamentals/001-osi-tcpip-traffic-path.yaml` |
| Network fundamentals | `labs/ccna/network-fundamentals/002-ipv4-subnetting-vlsm.yaml` |
| Network fundamentals | `labs/ccna/network-fundamentals/003-ipv6-addressing-static.yaml` |
| Network fundamentals | `labs/ccna/network-fundamentals/004-cdp-lldp-discovery.yaml` |
| Network fundamentals | `labs/ccna/network-fundamentals/005-interface-status-duplex.yaml` |
| Network fundamentals | `labs/ccna/network-fundamentals/006-wireless-architecture-cml.yaml` |
| Network access | `labs/ccna/network-access/007-vlan-router-on-a-stick.yaml` |
| Network access | `labs/ccna/network-access/008-access-trunk-native-vlan.yaml` |
| Network access | `labs/ccna/network-access/009-stp-root-selection.yaml` |
| Network access | `labs/ccna/network-access/010-portfast-bpduguard.yaml` |
| Network access | `labs/ccna/network-access/011-rapid-pvst-troubleshooting.yaml` |
| Network access | `labs/ccna/network-access/012-etherchannel-lacp.yaml` |
| Network access | `labs/ccna/network-access/013-layer2-security.yaml` |
| Network access | `labs/ccna/network-access/014-wlan-client-vlan-mapping.yaml` |
| IP connectivity | `labs/ccna/ip-connectivity/015-static-default-routes.yaml` |
| IP connectivity | `labs/ccna/ip-connectivity/016-floating-static-routes.yaml` |
| IP connectivity | `labs/ccna/ip-connectivity/017-single-area-ospfv2.yaml` |
| IP connectivity | `labs/ccna/ip-connectivity/018-ospfv2-neighbor-troubleshooting.yaml` |
| IP connectivity | `labs/ccna/ip-connectivity/019-first-hop-redundancy-hsrp.yaml` |
| IP connectivity | `labs/ccna/ip-connectivity/020-ipv6-static-routing.yaml` |
| IP connectivity | `labs/ccna/ip-connectivity/021-routing-table-selection.yaml` |
| IP connectivity | `labs/ccna/ip-connectivity/022-intervlan-troubleshooting.yaml` |
| IP services | `labs/ccna/ip-services/023-dhcp-server-relay.yaml` |
| IP services | `labs/ccna/ip-services/024-nat-pat-edge.yaml` |
| IP services | `labs/ccna/ip-services/025-ntp-time-sync.yaml` |
| IP services | `labs/ccna/ip-services/026-dns-client-resolution.yaml` |
| IP services | `labs/ccna/ip-services/027-syslog-snmp.yaml` |
| IP services | `labs/ccna/ip-services/028-qos-marking-classification.yaml` |
| IP services | `labs/ccna/ip-services/029-tftp-config-backup.yaml` |
| IP services | `labs/ccna/ip-services/030-sla-tracking-static-route.yaml` |
| Security | `labs/ccna/security/031-ssh-local-users-hardening.yaml` |
| Security | `labs/ccna/security/032-standard-extended-acls.yaml` |
| Security | `labs/ccna/security/033-dhcp-snooping-dai.yaml` |
| Security | `labs/ccna/security/034-port-security-sticky.yaml` |
| Security | `labs/ccna/security/035-ipsec-site-to-site-concepts.yaml` |
| Security | `labs/ccna/security/036-passwords-banners-secure-management.yaml` |
| Automation | `labs/ccna/automation/037-restconf-netconf-management.yaml` |
| Automation | `labs/ccna/automation/038-json-yaml-data-models.yaml` |
| Automation | `labs/ccna/automation/039-controller-based-networking.yaml` |
| Automation | `labs/ccna/automation/040-python-api-inventory.yaml` |

### CCNP ENCOR

| Area | Lab |
| --- | --- |
| Architecture | `labs/ccnp-encor/architecture/001-campus-two-three-tier-ha.yaml` |
| Architecture | `labs/ccnp-encor/architecture/002-fhrp-design-hsrp-vrrp.yaml` |
| Architecture | `labs/ccnp-encor/architecture/003-sdwan-control-data-plane.yaml` |
| Architecture | `labs/ccnp-encor/architecture/004-sdaccess-fabric-roles.yaml` |
| Architecture | `labs/ccnp-encor/architecture/005-qos-policy-interpretation.yaml` |
| Architecture | `labs/ccnp-encor/architecture/006-cef-cam-tcam-rib-fib.yaml` |
| Virtualization | `labs/ccnp-encor/virtualization/007-vrf-lite-route-leaking.yaml` |
| Virtualization | `labs/ccnp-encor/virtualization/008-gre-overlay-underlay.yaml` |
| Virtualization | `labs/ccnp-encor/virtualization/009-ipsec-gre-design.yaml` |
| Virtualization | `labs/ccnp-encor/virtualization/010-lisp-vxlan-concepts.yaml` |
| Virtualization | `labs/ccnp-encor/virtualization/011-virtual-switching-paths.yaml` |
| Infrastructure | `labs/ccnp-encor/infrastructure/012-dual-stack-campus.yaml` |
| Infrastructure | `labs/ccnp-encor/infrastructure/013-ospf-network-types.yaml` |
| Infrastructure | `labs/ccnp-encor/infrastructure/014-ospf-summarization-filtering.yaml` |
| Infrastructure | `labs/ccnp-encor/infrastructure/015-eigrp-named-mode.yaml` |
| Infrastructure | `labs/ccnp-encor/infrastructure/016-ospf-eigrp-redistribution.yaml` |
| Infrastructure | `labs/ccnp-encor/infrastructure/017-ebgp-ibgp-basics.yaml` |
| Infrastructure | `labs/ccnp-encor/infrastructure/018-bgp-path-selection.yaml` |
| Infrastructure | `labs/ccnp-encor/infrastructure/019-multilayer-switching-svi-routing.yaml` |
| Infrastructure | `labs/ccnp-encor/infrastructure/020-mst-rpvst-stp-tuning.yaml` |
| Infrastructure | `labs/ccnp-encor/infrastructure/021-lacp-pagp-etherchannel.yaml` |
| Infrastructure | `labs/ccnp-encor/infrastructure/022-ipv6-first-hop-and-routing.yaml` |
| Network assurance | `labs/ccnp-encor/network-assurance/023-span-rspan-erspan.yaml` |
| Network assurance | `labs/ccnp-encor/network-assurance/024-ip-sla-tracking.yaml` |
| Network assurance | `labs/ccnp-encor/network-assurance/025-netflow-telemetry.yaml` |
| Network assurance | `labs/ccnp-encor/network-assurance/026-syslog-snmp-ntp.yaml` |
| Network assurance | `labs/ccnp-encor/network-assurance/027-dna-center-assurance-concepts.yaml` |
| Network assurance | `labs/ccnp-encor/network-assurance/028-troubleshooting-path.yaml` |
| Security | `labs/ccnp-encor/security/029-aaa-radius-tacacs.yaml` |
| Security | `labs/ccnp-encor/security/030-8021x-mab-concepts.yaml` |
| Security | `labs/ccnp-encor/security/031-control-plane-policing.yaml` |
| Security | `labs/ccnp-encor/security/032-acl-vacl-pacl.yaml` |
| Security | `labs/ccnp-encor/security/033-infrastructure-device-hardening.yaml` |
| Security | `labs/ccnp-encor/security/034-dhcp-snooping-dai-ipsg.yaml` |
| Security | `labs/ccnp-encor/security/035-macsec-concepts.yaml` |
| Security | `labs/ccnp-encor/security/036-secure-management-plane.yaml` |
| Automation | `labs/ccnp-encor/automation/037-restconf-netconf-yang.yaml` |
| Automation | `labs/ccnp-encor/automation/038-python-requests-network-change.yaml` |
| Automation | `labs/ccnp-encor/automation/039-ansible-network-baseline.yaml` |
| Automation | `labs/ccnp-encor/automation/040-json-yaml-jinja2.yaml` |
| Automation | `labs/ccnp-encor/automation/041-event-driven-automation.yaml` |

## A note on images and licensing

This repo only contains topology files. It does not include Cisco images,
licenses, entitlement files, exam dumps, or official courseware.

Cisco, Cisco Modeling Labs, IOS, IOS-XE and related names belong to Cisco
Systems, Inc. This is an independent lab collection.
