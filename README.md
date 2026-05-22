# CML - LABS

Ready-to-import Cisco Modeling Labs topologies for people studying Cisco
certifications hands-on.

Clone the repo, import a `.yaml` file into CML, start the lab, and work through
the tasks in the lab notes. No workbook, no hidden files, no vendor images in
the repo.

## Lab tracks

| Exam | Official exam name | Labs |
| --- | --- | ---: |
| 200-301 CCNA | Implementing and Administering Cisco Solutions | 50 |
| 350-401 ENCOR | Implementing and Operating Cisco Enterprise Network Core Technologies | 51 |
| 300-410 ENARSI | Implementing Cisco Enterprise Advanced Routing and Services | 46 |
| 350-901 DEVCOR | Developing Applications Using Cisco Core Platforms and APIs | 40 |
| 350-701 SCOR | Implementing and Operating Cisco Security Core Technologies | 46 |

Total: **233 CML labs**.

The collection includes blueprint-focused labs plus scenario-based labs such as
capstones, break/fix exercises, mini assessments, migration labs, and design
challenges.

## Repository layout

```text
labs/
  200-301-ccna-implementing-and-administering-cisco-solutions/
    network-fundamentals/
    network-access/
    ip-connectivity/
    ip-services/
    security/
    automation/
    scenario/
    troubleshooting/
    migration/
    assessment/
    capstone/

  350-401-encor-implementing-and-operating-cisco-enterprise-network-core-technologies/
    architecture/
    virtualization/
    infrastructure/
    network-assurance/
    security/
    automation/
    scenario/
    troubleshooting/
    migration/
    assessment/
    capstone/

  300-410-enarsi-implementing-cisco-enterprise-advanced-routing-and-services/
    layer-3/
    bgp/
    vpn/
    infra-security/
    infra-services/
    services/
    automation/
    troubleshooting/
    migration/
    assessment/
    capstone/

  350-901-devcor-developing-applications-using-cisco-core-platforms-and-apis/
    software-design/
    using-apis/
    cisco-platforms/
    deployment-security/
    deployment/
    infrastructure-automation/
    gitops/
    apis/
    webhooks/
    security/
    validation/
    assessment/
    capstone/

  350-701-scor-implementing-and-operating-cisco-security-core-technologies/
    security-concepts/
    network-security/
    cloud-content/
    endpoint/
    secure-access/
    visibility-enforcement/
    automation/
    firewall/
    management/
    nac/
    scenario/
    vpn/
    incident-response/
    visibility/
    assessment/
    capstone/
```

## How to use

1. Open Cisco Modeling Labs.
2. Import any `.yaml` file from `labs/`.
3. Start the lab.
4. Read the lab notes inside CML.
5. Configure, break, verify, fix, repeat.

The labs are intentionally compact, but some scenarios use more than five
nodes. CML Free can import larger labs, but it can only run up to five nodes at
the same time. For the full experience, this collection is best used with a
paid CML license.

## Disclaimer

This repo does not include Cisco images, licenses, entitlement files, exam
dumps, answer keys, or official courseware. It is just a practical lab library
for CML.

Cisco, Cisco Modeling Labs, IOS, IOS-XE, CCNA, CCNP, CCIE and related names
belong to Cisco Systems, Inc. This is an independent lab collection.
