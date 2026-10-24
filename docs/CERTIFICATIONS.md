# Certification scope and compatibility

The directory names are stable identifiers, not a guarantee of current exam coverage.

| Existing track | Use and next step |
| --- | --- |
| 200-301 CCNA | Networking fundamentals; check the current Cisco exam blueprint when planning study. |
| 350-401 ENCOR | Enterprise core practice; an exercise title does not prove full blueprint coverage. |
| 300-410 ENARSI | Advanced routing exercises, including BGP and troubleshooting. |
| 350-701 SCOR | Security concepts and network scenarios. An IOSv router labelled as a firewall is not an ASAv/FTDv appliance. |
| 350-901 DEVCOR | **Legacy track.** Retained for existing links and forks. Do not present these 40 exercises as complete current AUTOCOR preparation. |

Cisco transitioned DevNet Professional to CCNP Automation on 3 February 2026.
The current 350-901 AUTOCOR exam is **Designing, Deploying, and Managing Network Automation Systems**.
The change includes substantive content changes; simply renaming this directory would be misleading.

The two curated webhook/validation labs teach transferable automation concepts,
but do not claim Cisco controller integration or complete AUTOCOR coverage.
Future AUTOCOR work should include actual Python/Ansible workflows, configuration
sources of truth, pre/post-change checks, CI/CD and network operations.

Sources, checked 24 October 2026:

- [Current AUTOCOR exam](https://www.cisco.com/site/us/en/learn/training-certifications/exams/autocor.html)
- [Cisco explanation of the transition and changed scope](https://blogs.cisco.com/learning/views-from-an-insider-on-the-ccnp-automation-track-autocor-edition)
- [CML reference platforms and virtualization limitations](https://developer.cisco.com/docs/modeling-labs/vm-images-for-cml-labs/)

## Images and licensing

The YAML files select a **node definition**, not a host-specific image ID. CML uses
the installed default image for that type. Check image availability and entitlement
before starting. Exact images used for functional tests are recorded separately.
No vendor image, license or entitlement file is distributed here.

The five-node limit is only one CML Free constraint. A topology with five or fewer
nodes is not automatically compatible with the reference images supplied with Free.
IOSv/IOSvL2, Ubuntu and any future appliance must be available under the user's
own installation and applicable license.

Resource numbers in the catalog are sums of default node RAM, **not** measured
peaks or an admission decision. Reserve memory/CPU for the CML controller and
the physical host. Simulated virtual platforms are intended for configuration
and control-plane exercises, not production throughput benchmarking.
