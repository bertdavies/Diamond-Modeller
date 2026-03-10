import hashlib, re

class ToolBus:
    @staticmethod
    def list_openai_tools():
        return [
            {"type": "function", "function": {
                "name": "map_attack",
                "description": "Normalize TTP names to MITRE ATT&CK technique IDs (best-effort).",
                "parameters": {"type":"object","properties":{"ttps":{"type":"array","items":{"type":"string"}}},"required":["ttps"]}
            }}
        ]

    @staticmethod
    async def execute(name, args):
        """Execute a tool by name with given arguments"""
        if name == "map_attack":
            return await ToolBus.map_attack_impl(**args)
        else:
            return {"error": f"Unknown tool: {name}"}

    @staticmethod
    def map_attack_impl(ttps):
        """Map TTP names to MITRE ATT&CK technique IDs"""
        # Simple mapping for common TTPs
        attack_mapping = {
            "phishing": "T1566",
            "social engineering": "T1566",
            "vishing": "T1566.002",
            "spear phishing": "T1566.001",
            "malware": "T1204",
            "trojan": "T1204.002",
            "ransomware": "T1486",
            "keylogger": "T1056.001",
            "backdoor": "T1505.003",
            "persistence": "T1055",
            "privilege escalation": "T1055",
            "lateral movement": "T1021",
            "command and control": "T1071",
            "c2": "T1071",
            "data exfiltration": "T1041",
            "credential theft": "T1555",
            "password spraying": "T1110.003",
            "brute force": "T1110",
            "dll hijacking": "T1574.002",
            "process injection": "T1055",
            "living off the land": "T1059",
            "powershell": "T1059.001",
            "cmd": "T1059.003",
            "wmi": "T1047",
            "scheduled task": "T1053",
            "registry": "T1547.001",
            "service": "T1543.003",
            "dll sideloading": "T1574.002",
            "dns tunneling": "T1071.004",
            "http": "T1071.001",
            "https": "T1071.001",
            "ftp": "T1071.002",
            "smb": "T1021.002",
            "rdp": "T1021.001",
            "ssh": "T1021.004",
            "vnc": "T1021.005",
            "remote desktop": "T1021.001",
            "fileless": "T1055",
            "memory": "T1055",
            "injection": "T1055",
            "hook": "T1179",
            "api": "T1106",
            "hooking": "T1179",
            "dll": "T1574",
            "executable": "T1204",
            "script": "T1059",
            "batch": "T1059.003",
            "vbs": "T1059.005",
            "javascript": "T1059.007",
            "hta": "T1059.005",
            "wscript": "T1059.005",
            "cscript": "T1059.005",
            "rundll32": "T1218.011",
            "regsvr32": "T1218.010",
            "mshta": "T1218.005",
            "certutil": "T1105",
            "bitsadmin": "T1197",
            "wmic": "T1047",
            "sc": "T1055",
            "net": "T1055",
            "at": "T1053.002",
            "schtasks": "T1053.005",
            "task scheduler": "T1053.005",
            "startup": "T1547",
            "autorun": "T1547",
            "run key": "T1547.001",
            "shell": "T1059",
            "bash": "T1059.004",
            "sh": "T1059.004",
            "zsh": "T1059.004",
            "fish": "T1059.004",
            "csh": "T1059.004",
            "tcsh": "T1059.004",
            "ksh": "T1059.004",
            "ash": "T1059.004",
            "dash": "T1059.004",
            "mksh": "T1059.004",
            "yash": "T1059.004",
            "busybox": "T1059.004",
            "netcat": "T1090",
            "nc": "T1090",
            "socat": "T1090",
            "ncat": "T1090",
            "openssl": "T1090",
            "stunnel": "T1090",
            "proxychains": "T1090",
            "proxytunnel": "T1090",
            "httptunnel": "T1090",
            "dns2tcp": "T1090",
            "iodine": "T1090",
            "dnscat": "T1090",
            "dns": "T1071.004",
            "icmp": "T1090",
            "ping": "T1090",
            "traceroute": "T1090",
            "tracert": "T1090",
            "pathping": "T1090",
            "arp": "T1090",
            "nslookup": "T1090",
            "dig": "T1090",
            "host": "T1090",
            "whois": "T1090",
            "tcpdump": "T1090",
            "wireshark": "T1090",
            "tshark": "T1090",
            "tcpflow": "T1090",
            "ngrep": "T1090",
            "netstat": "T1090",
            "ss": "T1090",
            "lsof": "T1090",
            "fuser": "T1090",
            "ps": "T1090",
            "top": "T1090",
            "htop": "T1090",
            "iotop": "T1090",
            "nethogs": "T1090",
            "iftop": "T1090",
            "nload": "T1090",
            "vnstat": "T1090",
            "vnstati": "T1090",
            "bmon": "T1090",
            "slurm": "T1090",
            "bwm-ng": "T1090",
            "cbm": "T1090",
            "speedometer": "T1090",
            "pktstat": "T1090",
            "netwatch": "T1090",
            "trafshow": "T1090",
            "tcptrack": "T1090",
            "vstat": "T1090",
            "netstat": "T1090",
            "ss": "T1090",
            "lsof": "T1090",
            "fuser": "T1090",
            "ps": "T1090",
            "top": "T1090",
            "htop": "T1090",
            "iotop": "T1090",
            "nethogs": "T1090",
            "iftop": "T1090",
            "nload": "T1090",
            "vnstat": "T1090",
            "vnstati": "T1090",
            "bmon": "T1090",
            "slurm": "T1090",
            "bwm-ng": "T1090",
            "cbm": "T1090",
            "speedometer": "T1090",
            "pktstat": "T1090",
            "netwatch": "T1090",
            "trafshow": "T1090",
            "tcptrack": "T1090",
            "vstat": "T1090"
        }
        
        results = []
        for ttp in ttps:
            ttp_lower = ttp.lower().strip()
            if ttp_lower in attack_mapping:
                results.append({
                    "original": ttp,
                    "technique_id": attack_mapping[ttp_lower],
                    "technique_name": ttp_lower.replace("_", " ").title()
                })
            else:
                # Try partial matching
                found = False
                for key, technique_id in attack_mapping.items():
                    if key in ttp_lower or ttp_lower in key:
                        results.append({
                            "original": ttp,
                            "technique_id": technique_id,
                            "technique_name": key.replace("_", " ").title(),
                            "confidence": "low"
                        })
                        found = True
                        break
                
                if not found:
                    results.append({
                        "original": ttp,
                        "technique_id": "T0000",
                        "technique_name": "Unknown",
                        "confidence": "none"
                    })
        
        return results