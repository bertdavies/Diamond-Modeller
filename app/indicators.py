"""
Diamond Modeler — indicator normalisation and classification.

Author: Albert Davies
License: CC BY-NC-SA 4.0
"""

import re
import hashlib
from typing import List, Tuple
from app.models import IndicatorKind

def normalize_indicator(raw_value: str) -> Tuple[str, IndicatorKind]:
    """Normalize and classify an indicator"""
    # Clean the indicator
    value = raw_value.strip().lower()
    
    # Classify the indicator type
    if is_ip_address(value):
        kind = IndicatorKind.IP
    elif is_domain(value):
        kind = IndicatorKind.DOMAIN
    elif is_email(value):
        kind = IndicatorKind.EMAIL
    elif is_tool(value):
        kind = IndicatorKind.TOOL
    elif is_ttp(value):
        kind = IndicatorKind.TTP
    else:
        kind = IndicatorKind.OTHER
    
    return value, kind

def is_ip_address(value: str) -> bool:
    """Check if value is an IP address"""
    ip_pattern = r'^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$'
    return bool(re.match(ip_pattern, value))

def is_domain(value: str) -> bool:
    """Check if value is a domain"""
    domain_pattern = r'^[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?)*$'
    return bool(re.match(domain_pattern, value)) and '.' in value

def is_email(value: str) -> bool:
    """Check if value is an email address"""
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(email_pattern, value))

def is_tool(value: str) -> bool:
    """Check if value is a tool (heuristic)"""
    tool_keywords = ['tool', 'software', 'malware', 'exploit', 'payload', 'backdoor', 'trojan', 'virus']
    return any(keyword in value for keyword in tool_keywords)

def is_ttp(value: str) -> bool:
    """Check if value is a TTP (heuristic)"""
    ttp_keywords = ['technique', 'tactic', 'procedure', 'attack', 'method', 'approach', 'strategy']
    return any(keyword in value for keyword in ttp_keywords)

def generate_hash(value: str) -> str:
    """Generate hash for indicator"""
    return hashlib.md5(value.encode()).hexdigest()

def process_indicators(raw_indicators: List[str]) -> List[Tuple[str, str, IndicatorKind, str]]:
    """Process a list of raw indicators and return normalized data"""
    processed = []
    for raw in raw_indicators:
        if raw.strip():  # Skip empty indicators
            value, kind = normalize_indicator(raw)
            hash_value = generate_hash(value)
            processed.append((value, raw, kind, hash_value))
    return processed

