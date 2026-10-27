# ENCOR 029 - RADIUS and TACACS+ authentication

## Scope and prerequisites

The IOL-XE NAS sends real authentication exchanges to separate native FreeRADIUS and tac_plus services. Fixed lab-only users and shared keys are public teaching fixtures. FreeRADIUS accepts only the configured NAS source address and requires Message-Authenticator; password logging is disabled. The router has a deliberately unauthenticated CML serial console with privilege15 so an authentication fault cannot lock out the exercise owner. Acceptance covers server authentication and rejection, not an interactive SSH login, command authorization, accounting or a commercial ISE integration. The failure changes one shared-key relationship. A negative result alone does not identify a network or credential cause; the preceding network and credential controls and the independent TACACS+ success narrow this controlled experiment.

Use licensed reference images for iol-xe, radius, tacplus in CML 2.10.1. All addresses are educational. No Internet, external connector or production credentials are required. Starting state: Working isolated reference baseline. Functional status and exact tested images: [results](../../validation/RESULTS.md).

## Topology and addressing

- R1 Ethernet0/0 <-> RADIUS eth1
- R1 Ethernet0/1 <-> TACACS eth1

| Node | Interface | Address |
| --- | --- | --- |
| R1 | Loopback0 | `ip address 192.0.2.1 255.255.255.255` |
| R1 | Ethernet0/0 | `ip address 198.18.0.1 255.255.255.252` |
| R1 | Ethernet0/1 | `ip address 198.18.1.1 255.255.255.252` |
| RADIUS | eth1 | `198.18.0.2/30` |
| TACACS | eth1 | `198.18.1.2/30` |

## Tasks

1. Compare actual RADIUS and TACACS+ authentication from the same NAS.
2. Reject incorrect user passwords and recheck the working credentials.
3. Break only the RADIUS shared key while preserving TACACS+, then recover.

## Baseline acceptance

| Node | Command | Observable result |
| --- | --- | --- |
| R1 | `ping 198.18.0.2 repeat 3` | The RADIUS data interface and return path are reachable. |
| R1 | `ping 198.18.1.2 repeat 3` | The TACACS+ data interface and return path are reachable. |
| R1 | `show running-config | section aaa group server radius` | The RADIUS group actively requests and validates Message-Authenticator. |
| R1 | `test aaa group RAD-GROUP labuser Cml-User-Only-983 new-code` | The RAD-GROUP server accepts the actual authentication request. |
| R1 | `test aaa group TAC-GROUP labuser Cml-User-Only-983 legacy` | The TAC-GROUP server accepts the actual authentication request. |
| R1 | `test aaa group RAD-GROUP labuser Wrong-user-only-999 new-code` | The RAD-GROUP server does not accept this authentication request. |
| R1 | `test aaa group TAC-GROUP labuser Wrong-user-only-999 legacy` | The TAC-GROUP server does not accept this authentication request. |
| R1 | `test aaa group RAD-GROUP labuser Cml-User-Only-983 new-code` | The RAD-GROUP server accepts the actual authentication request. |
| R1 | `test aaa group TAC-GROUP labuser Cml-User-Only-983 legacy` | The TAC-GROUP server accepts the actual authentication request. |

## Transition: mismatch only the RADIUS shared key

On **R1**:

```ios
configure terminal
radius server LAB-RADIUS
key 0 Wrong-radius-only-999
end
```

- R1: `test aaa group RAD-GROUP labuser Cml-User-Only-983 new-code` -- The RAD-GROUP server does not accept this authentication request.
- R1: `test aaa group TAC-GROUP labuser Cml-User-Only-983 legacy` -- The TAC-GROUP server accepts the actual authentication request.

## Transition: restore the RADIUS shared key

On **R1**:

```ios
configure terminal
radius server LAB-RADIUS
key 0 Cml-Radius-Lab-Only-983
end
```

- R1: `test aaa group RAD-GROUP labuser Cml-User-Only-983 new-code` -- The RAD-GROUP server accepts the actual authentication request.
- R1: `test aaa group TAC-GROUP labuser Cml-User-Only-983 legacy` -- The TAC-GROUP server accepts the actual authentication request.

## Reference configuration and recovery

The checked-in topology carries the reference configurations below. To reset a disposable exercise, stop and wipe only your imported copy, then restart or import the YAML again. Never apply the fault actions to a production device. Fault transitions restore the routing baseline; file-copy exercises may leave their documented output until wipe. Repeat the applicable acceptance checks before ending the exercise.

### R1

```ios
hostname R1
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
 ip address 198.18.1.1 255.255.255.252
 no shutdown
 exit
aaa new-model
aaa authentication login CONSOLE none
line console 0
 login authentication CONSOLE
 privilege level 15
 exit
ip radius source-interface Ethernet0/0
ip tacacs source-interface Ethernet0/1
radius server LAB-RADIUS
 address ipv4 198.18.0.2 auth-port 1812 acct-port 1813
 timeout 2
 retransmit 0
 key 0 Cml-Radius-Lab-Only-983
 exit
tacacs server LAB-TACACS
 address ipv4 198.18.1.2
 timeout 2
 key 0 Cml-Tacacs-Lab-Only-983
 exit
aaa group server radius RAD-GROUP
 server name LAB-RADIUS
 send-ma
 validate-ma
 exit
aaa group server tacacs+ TAC-GROUP
 server name LAB-TACACS
 exit
end
```

### RADIUS: radiusd.conf

```text
# Basic freeRADIUS onfiguration

prefix = /usr
exec_prefix = /usr
sysconfdir = /etc
localstatedir = /var
sbindir = ${exec_prefix}/sbin
logdir = /var/log/freeradius
raddbdir = /etc/freeradius/3.0
radacctdir = ${logdir}/radacct
name = freeradius
confdir = ${raddbdir}
modconfdir = ${confdir}/mods-config
certdir = ${confdir}/certs
cadir   = ${confdir}/certs
run_dir = ${localstatedir}/run/${name}
db_dir = ${raddbdir}
libdir = /usr/lib/freeradius
pidfile = ${run_dir}/${name}.pid
max_request_time = 30
cleanup_delay = 5
max_requests = 16384
hostname_lookups = no

log {
    destination = syslog
    colourise = no
    file = ${logdir}/radius.log
    syslog_facility = daemon
    stripped_names = no
    auth = yes
    auth_reject = yes
    auth_badpass = no
    auth_goodpass = no
    msg_denied = "You are already logged in - access denied"
}

checkrad = ${sbindir}/checkrad

#ENV {
#}

security {
    user = freerad
    group = freerad
    allow_core_dumps = no
    max_attributes = 200
    reject_delay = 1
    status_server = yes
}

proxy_requests = no
#$INCLUDE proxy.conf

#$INCLUDE clients.conf
client all-devices {
    ipaddr = 198.18.0.1/32
    secret = Cml-Radius-Lab-Only-983
    require_message_authenticator = yes
    nas_type = cisco
}

thread pool {
    start_servers = 5
    max_servers = 32
    min_spare_servers = 3
    max_spare_servers = 10
    max_requests_per_server = 0
    auto_limit_acct = no
}

modules {
    $INCLUDE mods-enabled/
}

#instantiate {
#}

policy {
    $INCLUDE policy.d/
}

$INCLUDE sites-enabled/```

### RADIUS: users

```text
labuser Cleartext-Password := "Cml-User-Only-983"
```

### RADIUS: environment

```text
ARGS=-f -lstdout
```

### RADIUS: boot.sh

```bash
#!/bin/bash
set -eu
ip address add 198.18.0.2/30 dev eth1
ip link set eth1 up
ip route add 192.0.2.1/32 via 198.18.0.1 dev eth1
mkdir -p /lab
echo READY >/dev/console
exit 0
```

### RADIUS: mounts

```text
# Can map a volume with radius server data into the container
# it. By default, only type=volume is allowed, see
# /etc/default/docker-shim.env
# Note: Use source=<name> below; docker-shim scopes volumes to the lab
# by prefixing the name with the lab ID. Docker creates the volume on
# first use if it does not already exist. Only type, source, target,
# readonly, and tmpfs-* options are accepted in this file.
#
# type=volume,source=radiusdata,target=/var/somedir```

### TACACS: tac_plus.conf

```text
key = "Cml-Tacacs-Lab-Only-983"
accounting file = /var/log/tacplus-acct.log
group = netadmin {
  default service = permit
  service = exec { priv-lvl = 15 }
}
user = labuser {
  login = cleartext "Cml-User-Only-983"
  member = netadmin
}
```

### TACACS: boot.sh

```bash
#!/bin/bash
set -eu
ip address add 198.18.1.2/30 dev eth1
ip link set eth1 up
mkdir -p /lab
echo READY >/dev/console
exit 0
```

## Platform scope

Use the [reference-platform guide](../PLATFORMS.md) for the node models named by this workbook. Exact tested CML and image versions are recorded in the [results](../../validation/RESULTS.md). The checks verify the listed protocol and forwarding behavior, not hardware throughput, physical failure timing or complete certification coverage.
