---
name: diamond-modeller-skill
description: >
  Interact with the Diamond Modeller REST API to create, read, update, and delete
  Diamond Model entries for cyber threat intelligence analysis. Use this skill when
  you need to convert threat intelligence into Diamond Model data, add diamonds to
  the graph, query existing diamonds and graph edges, update indicator data, export
  or import analysis, or trigger hypothesis generation. Covers all CRUD operations
  against the Diamond Modeller app running on localhost.
license: CC BY-NC-SA 4.0
compatibility: "Requires Python 3.10+, requests library, and a running Diamond Modeller instance on localhost"
metadata:
  author: "Albert Davies"
  version: "1.0"
allowed-tools: "Bash(python3:*) Bash(python:*) Read"
---

# Diamond Modeller Skill

## When to Use This Skill

Use this skill when the user wants to:

- **Create diamonds** from threat intelligence (reports, IOCs, incident data)
- **Read or query** existing diamonds, their details, or the graph structure
- **Update** diamond labels, notes, colours, or indicators
- **Delete** individual diamonds or clear the entire graph
- **Export** the current analysis as JSON for sharing
- **Import** a previously exported analysis JSON
- **Generate hypotheses** (attribution analysis) from the current graph
- **Create manual links** between diamonds
- **Regenerate automatic links** after bulk changes
- **Manage settings** such as the OpenAI API key

## Instructions

### 1. Ensure the Diamond Modeller app is running

The app must be running on `http://localhost:8000` (default). If it's on a different port, pass the `base_url` parameter when instantiating the client.

### 2. Use the Python client

Run the client script at `scripts/diamond_modeller.py`. It exposes a `DiamondModellerClient` class with methods for every API endpoint.

```python
# Example: instantiate and use
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from diamond_modeller import DiamondModellerClient

client = DiamondModellerClient()  # defaults to http://localhost:8000
```

### 3. Converting intelligence into diamonds

When given threat intelligence (a report, a set of IOCs, incident notes), you MUST create **one diamond per kill chain phase** (or per MITRE ATT&CK tactic if the user requests it). Populate each with the indicators observed at that stage.

#### Label convention

Labels MUST follow the format `<phase-code> <adversary>`:

| Framework | Prefix | Example label |
|---|---|---|
| Lockheed Kill Chain | `KC1`–`KC7` | `KC3 UNC1234` |
| MITRE ATT&CK Tactic | `TA0001`–`TA0043` | `TA0001 UNC1234` |

Kill chain phase codes:

| Code | Phase |
|---|---|
| `KC1` | Reconnaissance |
| `KC2` | Weaponisation |
| `KC3` | Delivery |
| `KC4` | Exploitation |
| `KC5` | Installation |
| `KC6` | Command & Control |
| `KC7` | Actions on Objectives |

Common MITRE ATT&CK tactic codes:

| Code | Tactic |
|---|---|
| `TA0043` | Reconnaissance |
| `TA0042` | Resource Development |
| `TA0001` | Initial Access |
| `TA0002` | Execution |
| `TA0003` | Persistence |
| `TA0004` | Privilege Escalation |
| `TA0005` | Defence Evasion |
| `TA0006` | Credential Access |
| `TA0007` | Discovery |
| `TA0008` | Lateral Movement |
| `TA0009` | Collection |
| `TA0011` | Command & Control |
| `TA0010` | Exfiltration |
| `TA0040` | Impact |

#### Notes field

The `notes` field on every diamond MUST be used to capture context and metadata about that phase. Include:

- A brief narrative of what happened at this phase
- Timeframes or dates if known (e.g. "Observed 2026-02-14 to 2026-02-16")
- Confidence level (e.g. "High confidence based on PCAP analysis")
- Source references (e.g. "Per Mandiant report M-TRENDS-2026")
- Any caveats or analyst remarks

#### Example: Kill chain mode

```python
client.create_diamond(
    label="KC3 APT29",
    notes="Delivery via spear-phishing emails with macro-enabled DOCX. "
          "Observed 2026-02-14. High confidence. Source: IR case #4412.",
    color="#e74c3c",
    adversary_indicators=["APT29", "Cozy Bear"],
    victimology_indicators=["ACME Corp", "jsmith@acme.com"],
    capability_indicators=["Spear Phishing", "Macro dropper"],
    infrastructure_indicators=["198.51.100.12", "cdn-update.com"]
)
```

#### Example: MITRE tactic mode

```python
client.create_diamond(
    label="TA0001 APT29",
    notes="Initial Access achieved through spear-phishing link (T1566.002). "
          "Victim clicked link on 2026-02-14 09:32 UTC. Medium confidence.",
    color="#e74c3c",
    adversary_indicators=["APT29", "Cozy Bear"],
    victimology_indicators=["ACME Corp", "jsmith@acme.com"],
    capability_indicators=["T1566.002 Spear Phishing Link"],
    infrastructure_indicators=["198.51.100.12", "cdn-update.com"]
)
```

#### Convenience helpers

The client has two dedicated methods for bulk creation:

```python
# Kill chain mode (default)
client.create_kill_chain_diamonds(
    adversary="UNC1234",
    phases={
        "KC1": {
            "notes": "Open-source recon on target org. Source: passive DNS logs.",
            "adversary_indicators": ["UNC1234"],
            "capability_indicators": ["Google dorking", "LinkedIn scraping"],
            "infrastructure_indicators": ["cdn-update.com"],
            "victimology_indicators": ["ACME Corp"]
        },
        "KC3": {
            "notes": "Spear-phishing with weaponised DOCX. Observed 2026-02-14.",
            "adversary_indicators": ["UNC1234"],
            "capability_indicators": ["Spear Phishing", "Macro dropper"],
            "infrastructure_indicators": ["cdn-update.com", "198.51.100.12"],
            "victimology_indicators": ["ACME Corp", "jsmith@acme.com"]
        }
    }
)

# MITRE tactic mode
client.create_mitre_tactic_diamonds(
    adversary="UNC1234",
    tactics={
        "TA0043": {
            "notes": "Reconnaissance via passive DNS and social media. Low confidence.",
            "adversary_indicators": ["UNC1234"],
            "capability_indicators": ["Passive DNS recon"],
            "infrastructure_indicators": ["cdn-update.com"],
            "victimology_indicators": ["ACME Corp"]
        },
        "TA0001": {
            "notes": "Initial Access via spear-phishing link (T1566.002). High confidence.",
            "adversary_indicators": ["UNC1234"],
            "capability_indicators": ["T1566.002 Spear Phishing Link"],
            "infrastructure_indicators": ["198.51.100.12"],
            "victimology_indicators": ["ACME Corp"]
        }
    }
)
```

### 4. Reading graph data

```python
# List all diamonds
diamonds = client.list_diamonds()

# Get full details of a diamond (includes indicators per vertex)
details = client.get_diamond_details(diamond_id=1)

# Get the full graph (nodes + edges) in Cytoscape format
graph = client.get_graph()
```

### 5. Updating a diamond

```python
client.update_diamond(
    diamond_id=1,
    label="Delivery Phase (updated)",
    notes="Updated notes",
    color="#3498db",
    adversary_indicators=["APT29"],
    capability_indicators=["Spear Phishing", "PowerShell dropper"],
    infrastructure_indicators=["198.51.100.12"]
)
```

### 6. Deleting

```python
client.delete_diamond(diamond_id=1)
client.delete_all_diamonds()
```

### 7. Export / Import

```python
data = client.export_analysis()
# Save data to a file, share it, then import:
client.import_analysis(data)
```

### 8. Hypothesis generation

```python
# Ensure API key is set first
client.set_openai_api_key("sk-...")
# Generate hypotheses (downloads PDF, returns path or bytes)
result = client.generate_hypotheses(save_path="report.pdf")
```

## Examples

### Example 1: Kill chain from an incident report

**Input:**

> "UNC1234 conducted reconnaissance on ACME Corp using LinkedIn and Google dorking, then
> delivered a spear-phishing email with a macro-enabled DOCX on 2026-02-14.
> C2 was at 198.51.100.12 and cdn-update.com. Cobalt Strike beacon was used
> for lateral movement. Data was exfiltrated via HTTPS to exfil-drop.net."

**What the agent should do:**

1. Identify the adversary: `UNC1234`
2. Map activities to kill chain phases
3. Create one diamond per phase with the correct `KC` label format
4. Fill `notes` with narrative, dates, and confidence

```python
client.create_kill_chain_diamonds(
    adversary="UNC1234",
    phases={
        "KC1": {
            "notes": "Recon via LinkedIn and Google dorking targeting ACME Corp. Pre-2026-02-14.",
            "adversary_indicators": ["UNC1234"],
            "capability_indicators": ["LinkedIn scraping", "Google dorking"],
            "infrastructure_indicators": ["cdn-update.com"],
            "victimology_indicators": ["ACME Corp"]
        },
        "KC3": {
            "notes": "Spear-phishing email with macro-enabled DOCX delivered 2026-02-14. High confidence.",
            "adversary_indicators": ["UNC1234"],
            "capability_indicators": ["Spear Phishing", "Macro dropper"],
            "infrastructure_indicators": ["cdn-update.com", "198.51.100.12"],
            "victimology_indicators": ["ACME Corp"]
        },
        "KC6": {
            "notes": "C2 via Cobalt Strike beacon to 198.51.100.12 and cdn-update.com.",
            "adversary_indicators": ["UNC1234"],
            "capability_indicators": ["Cobalt Strike"],
            "infrastructure_indicators": ["198.51.100.12", "cdn-update.com"],
            "victimology_indicators": ["ACME Corp"]
        },
        "KC7": {
            "notes": "Data exfiltration over HTTPS to exfil-drop.net. Lateral movement observed.",
            "adversary_indicators": ["UNC1234"],
            "capability_indicators": ["Cobalt Strike", "HTTPS exfil"],
            "infrastructure_indicators": ["exfil-drop.net"],
            "victimology_indicators": ["ACME Corp"]
        }
    }
)
```

### Example 2: MITRE tactic mode

**Input:**

> "Map the same UNC1234 intrusion to MITRE ATT&CK tactics."

```python
client.create_mitre_tactic_diamonds(
    adversary="UNC1234",
    tactics={
        "TA0043": {
            "notes": "Reconnaissance: LinkedIn and Google dorking. Low-medium confidence.",
            "adversary_indicators": ["UNC1234"],
            "capability_indicators": ["T1593 Search Open Websites", "T1589 Gather Victim Identity"],
            "infrastructure_indicators": ["cdn-update.com"],
            "victimology_indicators": ["ACME Corp"]
        },
        "TA0001": {
            "notes": "Initial Access via spear-phishing attachment (T1566.001). 2026-02-14.",
            "adversary_indicators": ["UNC1234"],
            "capability_indicators": ["T1566.001 Spear Phishing Attachment"],
            "infrastructure_indicators": ["cdn-update.com", "198.51.100.12"],
            "victimology_indicators": ["ACME Corp"]
        },
        "TA0011": {
            "notes": "C2 using Cobalt Strike (T1071.001 Web Protocols). High confidence from PCAP.",
            "adversary_indicators": ["UNC1234"],
            "capability_indicators": ["T1071.001 Web Protocols", "Cobalt Strike"],
            "infrastructure_indicators": ["198.51.100.12", "cdn-update.com"],
            "victimology_indicators": ["ACME Corp"]
        },
        "TA0010": {
            "notes": "Exfiltration over HTTPS to exfil-drop.net (T1048.002).",
            "adversary_indicators": ["UNC1234"],
            "capability_indicators": ["T1048.002 Exfiltration Over Asymmetric Encrypted Non-C2"],
            "infrastructure_indicators": ["exfil-drop.net"],
            "victimology_indicators": ["ACME Corp"]
        }
    }
)
```

### Example 3: Single diamond with rich notes

```python
client.create_diamond(
    label="KC4 APT29",
    notes=(
        "Exploitation of CVE-2024-1234 in victim web server. "
        "Observed 2026-02-15 03:22 UTC. "
        "High confidence based on exploit artefacts in /tmp/. "
        "Ref: IR case #4412, Mandiant report M-TRENDS-2026 p.42. "
        "Caveat: exploit may have been reused from public PoC."
    ),
    adversary_indicators=["APT29"],
    capability_indicators=["CVE-2024-1234", "PowerShell dropper"],
    infrastructure_indicators=["198.51.100.12"],
    victimology_indicators=["ACME Corp"]
)
```

## Edge Cases

- **Duplicate labels**: The API rejects diamonds with duplicate labels. Labels are unique by design (`KC3 UNC1234` vs `KC3 UNC5678` are different). If the same adversary appears in two analyses, disambiguate with a suffix (e.g. `KC3 UNC1234 Feb2026`).
- **Empty indicators**: Vertices with no indicators are valid — pass empty lists `[]` or omit them.
- **App not running**: All methods raise `ConnectionError` if the app is unreachable. Check that the server is running first.
- **Import replaces data**: `import_analysis()` deletes all current diamonds and edges before importing. Warn the user or export first.
- **Generate hypotheses requires OpenAI key**: Call `set_openai_api_key()` or ensure `.env` has `OPENAI_API_KEY` before generating hypotheses.
- **Large indicator lists**: Pass indicators as lists of strings, one indicator per item. Do not join with newlines — the client handles serialisation.
- **Notes should never be empty**: Always add context — even a single sentence about what happened, when, and at what confidence level.
- **Kill chain vs MITRE**: Default to kill chain (`KC`) unless the user explicitly asks for MITRE ATT&CK (`TA`). Never mix both frameworks in the same analysis.

## Directory Structure

```text
diamond-modeller-skill/
├── SKILL.md                        # This file
├── scripts/
│   └── diamond_modeller.py          # Python client with CRUD functions
└── references/
    └── API_REFERENCE.md            # Full REST API endpoint reference
```

### scripts/

`diamond_modeller.py` — A self-contained Python module exposing `DiamondModellerClient`. Only dependency is `requests` (standard in most environments). All methods return parsed JSON or raise on error.

### references/

`API_REFERENCE.md` — Detailed endpoint documentation with request/response schemas. Read this file if you need to understand payload formats or construct raw HTTP requests.
