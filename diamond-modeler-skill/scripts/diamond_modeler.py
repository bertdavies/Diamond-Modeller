#!/usr/bin/env python3
"""
Diamond Modeler REST API client.

Provides CRUD operations for diamonds, links, graph data, export/import,
settings, and hypothesis generation against a running Diamond Modeler instance.

Author: Albert Davies
License: CC BY-NC-SA 4.0

Usage:
    from diamond_modeler import DiamondModelerClient
    client = DiamondModelerClient("http://localhost:8000")
    client.create_diamond(label="Recon", adversary_indicators=["APT29"])

Only dependency: requests
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import requests


class DiamondModelerError(Exception):
    """Raised when the Diamond Modeler API returns an error."""

    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"HTTP {status_code}: {detail}")


class DiamondModelerClient:
    """Client for the Diamond Modeler REST API."""

    def __init__(self, base_url: str = "http://localhost:8000", timeout: int = 120):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._session = requests.Session()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _url(self, path: str) -> str:
        return f"{self.base_url}{path}"

    def _check(self, resp: requests.Response) -> requests.Response:
        if resp.status_code >= 400:
            try:
                body = resp.json()
                detail = body.get("detail") or body.get("message") or json.dumps(body)
            except Exception:
                detail = resp.text[:500]
            raise DiamondModelerError(resp.status_code, detail)
        return resp

    def _indicators_to_str(self, indicators: Optional[List[str]]) -> str:
        if not indicators:
            return ""
        return "\n".join(indicators)

    # ------------------------------------------------------------------
    # Diamond CRUD
    # ------------------------------------------------------------------

    def create_diamond(
        self,
        label: str,
        notes: str = "",
        color: str = "#4ecdc4",
        adversary_indicators: Optional[List[str]] = None,
        victimology_indicators: Optional[List[str]] = None,
        capability_indicators: Optional[List[str]] = None,
        infrastructure_indicators: Optional[List[str]] = None,
    ) -> str:
        """Create a new diamond. Returns the HTML fragment (diamond list)."""
        resp = self._check(
            self._session.post(
                self._url("/create-diamond"),
                data={
                    "label": label,
                    "notes": notes,
                    "color": color,
                    "adversary_indicators": self._indicators_to_str(adversary_indicators),
                    "victimology_indicators": self._indicators_to_str(victimology_indicators),
                    "capability_indicators": self._indicators_to_str(capability_indicators),
                    "infrastructure_indicators": self._indicators_to_str(infrastructure_indicators),
                },
                timeout=self.timeout,
            )
        )
        return resp.text

    def get_diamond(self, diamond_id: int) -> Dict[str, Any]:
        """Get diamond summary (id, label, notes, color, timestamps)."""
        resp = self._check(
            self._session.get(self._url(f"/diamonds/{diamond_id}"), timeout=self.timeout)
        )
        return resp.json()

    def get_diamond_details(self, diamond_id: int) -> Dict[str, Any]:
        """Get full diamond details including indicators per vertex."""
        resp = self._check(
            self._session.get(self._url(f"/diamonds/{diamond_id}/details"), timeout=self.timeout)
        )
        return resp.json()

    def get_diamond_for_edit(self, diamond_id: int) -> Dict[str, Any]:
        """Get diamond data pre-filled for editing (indicators as newline strings)."""
        resp = self._check(
            self._session.get(self._url(f"/diamonds/{diamond_id}/edit"), timeout=self.timeout)
        )
        return resp.json()

    def list_diamonds(self, query: str = "") -> str:
        """Search/list diamonds. Returns HTML fragment. Use get_graph() for structured data."""
        params = {}
        if query:
            params["query"] = query
        resp = self._check(
            self._session.get(self._url("/diamonds/"), params=params, timeout=self.timeout)
        )
        return resp.text

    def update_diamond(
        self,
        diamond_id: int,
        label: str = "",
        notes: str = "",
        color: str = "#4ecdc4",
        adversary_indicators: Optional[List[str]] = None,
        victimology_indicators: Optional[List[str]] = None,
        capability_indicators: Optional[List[str]] = None,
        infrastructure_indicators: Optional[List[str]] = None,
    ) -> str:
        """Update an existing diamond. Returns HTML fragment."""
        resp = self._check(
            self._session.put(
                self._url(f"/diamonds/{diamond_id}"),
                data={
                    "label": label,
                    "notes": notes,
                    "color": color,
                    "adversary_indicators": self._indicators_to_str(adversary_indicators),
                    "victimology_indicators": self._indicators_to_str(victimology_indicators),
                    "capability_indicators": self._indicators_to_str(capability_indicators),
                    "infrastructure_indicators": self._indicators_to_str(infrastructure_indicators),
                },
                timeout=self.timeout,
            )
        )
        return resp.text

    def delete_diamond(self, diamond_id: int) -> Dict[str, Any]:
        """Delete a single diamond and all its associated data."""
        resp = self._check(
            self._session.delete(self._url(f"/diamonds/{diamond_id}"), timeout=self.timeout)
        )
        return resp.json()

    def delete_all_diamonds(self) -> Dict[str, Any]:
        """Delete ALL diamonds, vertices, indicators, and edges."""
        resp = self._check(
            self._session.delete(self._url("/diamonds/remove-all/"), timeout=self.timeout)
        )
        return resp.json()

    # ------------------------------------------------------------------
    # Links
    # ------------------------------------------------------------------

    def create_link(
        self, src_diamond_id: int, dst_diamond_id: int, reason: str
    ) -> Dict[str, Any]:
        """Create a manual link between two diamonds."""
        resp = self._check(
            self._session.post(
                self._url("/links/"),
                json={
                    "src_diamond_id": src_diamond_id,
                    "dst_diamond_id": dst_diamond_id,
                    "reason": reason,
                },
                timeout=self.timeout,
            )
        )
        return resp.json()

    def regenerate_links(self) -> Dict[str, Any]:
        """Rebuild all automatic links based on indicator overlaps."""
        resp = self._check(
            self._session.post(self._url("/regenerate-links"), timeout=self.timeout)
        )
        return resp.json()

    # ------------------------------------------------------------------
    # Graph
    # ------------------------------------------------------------------

    def get_graph(self) -> Dict[str, Any]:
        """Get the full graph in Cytoscape format: { elements: { nodes, edges } }."""
        resp = self._check(
            self._session.get(self._url("/graph"), timeout=self.timeout)
        )
        return resp.json()

    # ------------------------------------------------------------------
    # Export / Import
    # ------------------------------------------------------------------

    def export_analysis(self) -> Dict[str, Any]:
        """Export the full analysis (diamonds + edges) as a JSON dict."""
        resp = self._check(
            self._session.get(self._url("/api/export-analysis"), timeout=self.timeout)
        )
        return resp.json()

    def export_analysis_to_file(self, path: Union[str, Path]) -> Path:
        """Export analysis and save to a JSON file. Returns the file path."""
        data = self.export_analysis()
        path = Path(path)
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return path

    def import_analysis(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Import analysis from a JSON dict. Replaces all current data."""
        resp = self._check(
            self._session.post(
                self._url("/api/import-analysis"),
                json=data,
                timeout=self.timeout,
            )
        )
        return resp.json()

    def import_analysis_from_file(self, path: Union[str, Path]) -> Dict[str, Any]:
        """Load a JSON file and import it. Replaces all current data."""
        path = Path(path)
        data = json.loads(path.read_text(encoding="utf-8"))
        return self.import_analysis(data)

    # ------------------------------------------------------------------
    # Settings
    # ------------------------------------------------------------------

    def set_openai_api_key(self, api_key: str) -> Dict[str, Any]:
        """Set the OpenAI API key (stored in .env on the server)."""
        resp = self._check(
            self._session.post(
                self._url("/api/settings/openai-api-key"),
                json={"api_key": api_key},
                timeout=self.timeout,
            )
        )
        return resp.json()

    def get_openai_api_key_status(self) -> Dict[str, Any]:
        """Check whether an OpenAI API key is configured. Returns { set: bool }."""
        resp = self._check(
            self._session.get(
                self._url("/api/settings/openai-api-key"), timeout=self.timeout
            )
        )
        return resp.json()

    # ------------------------------------------------------------------
    # Hypothesis Generation (Attribution)
    # ------------------------------------------------------------------

    def generate_hypotheses(
        self, save_path: Optional[Union[str, Path]] = None
    ) -> Union[Dict[str, Any], Path]:
        """
        Run hypothesis generation. If the server returns a PDF, save it to
        save_path (or a default name) and return the Path. If the server
        returns JSON (error or non-PDF success), return the parsed dict.
        """
        resp = self._session.post(
            self._url("/conduct-attribution"), timeout=self.timeout
        )
        content_type = resp.headers.get("Content-Type", "")
        if resp.ok and "application/pdf" in content_type:
            if save_path is None:
                disp = resp.headers.get("Content-Disposition", "")
                if "filename=" in disp:
                    import re
                    m = re.search(r'filename="?([^";\n]+)"?', disp)
                    save_path = m.group(1).strip() if m else "attribution_report.pdf"
                else:
                    save_path = "attribution_report.pdf"
            save_path = Path(save_path)
            save_path.write_bytes(resp.content)
            return save_path
        self._check(resp)
        return resp.json()

    # ------------------------------------------------------------------
    # Convenience: bulk create from intelligence
    # ------------------------------------------------------------------

    KILL_CHAIN_PHASES = {
        "KC1": "Reconnaissance",
        "KC2": "Weaponisation",
        "KC3": "Delivery",
        "KC4": "Exploitation",
        "KC5": "Installation",
        "KC6": "Command & Control",
        "KC7": "Actions on Objectives",
    }

    MITRE_TACTICS = {
        "TA0043": "Reconnaissance",
        "TA0042": "Resource Development",
        "TA0001": "Initial Access",
        "TA0002": "Execution",
        "TA0003": "Persistence",
        "TA0004": "Privilege Escalation",
        "TA0005": "Defence Evasion",
        "TA0006": "Credential Access",
        "TA0007": "Discovery",
        "TA0008": "Lateral Movement",
        "TA0009": "Collection",
        "TA0011": "Command & Control",
        "TA0010": "Exfiltration",
        "TA0040": "Impact",
    }

    KILL_CHAIN_COLORS = {
        "KC1": "#3498db",
        "KC2": "#9b59b6",
        "KC3": "#e74c3c",
        "KC4": "#e67e22",
        "KC5": "#f1c40f",
        "KC6": "#1abc9c",
        "KC7": "#2c3e50",
    }

    def create_diamonds_from_phases(
        self, phases: List[Dict[str, Any]], regenerate: bool = True
    ) -> List[str]:
        """
        Bulk-create diamonds from a list of phase dicts. Each dict should have
        at least 'label' and optionally 'notes', 'color', and indicator lists.
        Returns list of HTML fragments. Optionally regenerates links after.
        """
        results = []
        for phase in phases:
            result = self.create_diamond(
                label=phase["label"],
                notes=phase.get("notes", ""),
                color=phase.get("color", "#4ecdc4"),
                adversary_indicators=phase.get("adversary_indicators"),
                victimology_indicators=phase.get("victimology_indicators"),
                capability_indicators=phase.get("capability_indicators"),
                infrastructure_indicators=phase.get("infrastructure_indicators"),
            )
            results.append(result)
        if regenerate:
            self.regenerate_links()
        return results

    def create_kill_chain_diamonds(
        self,
        adversary: str,
        phases: Dict[str, Dict[str, Any]],
        regenerate: bool = True,
    ) -> List[str]:
        """
        Create one diamond per kill chain phase.

        Args:
            adversary: Threat actor name (e.g. "UNC1234", "APT29").
            phases: Dict keyed by phase code ("KC1"–"KC7"). Each value is a dict
                    with optional keys: notes, color, adversary_indicators,
                    victimology_indicators, capability_indicators,
                    infrastructure_indicators.
            regenerate: Whether to regenerate links after bulk creation.

        Labels are formatted as "<phase_code> <adversary>" (e.g. "KC3 UNC1234").
        A default colour per phase is applied unless overridden.
        """
        ordered_keys = [k for k in self.KILL_CHAIN_PHASES if k in phases]
        results = []
        for code in ordered_keys:
            data = phases[code]
            phase_name = self.KILL_CHAIN_PHASES[code]
            label = f"{code} {adversary}"
            default_notes = f"{phase_name} phase."
            result = self.create_diamond(
                label=label,
                notes=data.get("notes", default_notes),
                color=data.get("color", self.KILL_CHAIN_COLORS.get(code, "#4ecdc4")),
                adversary_indicators=data.get("adversary_indicators"),
                victimology_indicators=data.get("victimology_indicators"),
                capability_indicators=data.get("capability_indicators"),
                infrastructure_indicators=data.get("infrastructure_indicators"),
            )
            results.append(result)
        if regenerate:
            self.regenerate_links()
        return results

    def create_mitre_tactic_diamonds(
        self,
        adversary: str,
        tactics: Dict[str, Dict[str, Any]],
        regenerate: bool = True,
    ) -> List[str]:
        """
        Create one diamond per MITRE ATT&CK tactic.

        Args:
            adversary: Threat actor name (e.g. "UNC1234", "APT29").
            tactics: Dict keyed by tactic ID ("TA0001"–"TA0043"). Each value is
                     a dict with optional keys: notes, color,
                     adversary_indicators, victimology_indicators,
                     capability_indicators, infrastructure_indicators.
            regenerate: Whether to regenerate links after bulk creation.

        Labels are formatted as "<tactic_id> <adversary>" (e.g. "TA0001 UNC1234").
        """
        ordered_keys = [k for k in self.MITRE_TACTICS if k in tactics]
        results = []
        for tactic_id in ordered_keys:
            data = tactics[tactic_id]
            tactic_name = self.MITRE_TACTICS[tactic_id]
            label = f"{tactic_id} {adversary}"
            default_notes = f"{tactic_name} tactic."
            result = self.create_diamond(
                label=label,
                notes=data.get("notes", default_notes),
                color=data.get("color", "#4ecdc4"),
                adversary_indicators=data.get("adversary_indicators"),
                victimology_indicators=data.get("victimology_indicators"),
                capability_indicators=data.get("capability_indicators"),
                infrastructure_indicators=data.get("infrastructure_indicators"),
            )
            results.append(result)
        if regenerate:
            self.regenerate_links()
        return results

    # ------------------------------------------------------------------
    # Health check
    # ------------------------------------------------------------------

    def ping(self) -> bool:
        """Return True if the Diamond Modeler app is reachable."""
        try:
            resp = self._session.get(self._url("/graph"), timeout=5)
            return resp.ok
        except Exception:
            return False


if __name__ == "__main__":
    client = DiamondModelerClient()
    if client.ping():
        print("Diamond Modeler is reachable.")
        graph = client.get_graph()
        nodes = graph.get("elements", {}).get("nodes", [])
        edges = graph.get("elements", {}).get("edges", [])
        print(f"Graph: {len(nodes)} diamonds, {len(edges)} edges.")
    else:
        print("ERROR: Diamond Modeler is not reachable at http://localhost:8000")
