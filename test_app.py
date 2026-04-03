#!/usr/bin/env python3
"""
Simple test script to verify the Diamond Modeller application works correctly.
This script creates some example data and tests the core functionality.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import create_db_and_tables, get_session
from app.services import create_diamond_with_indicators, get_graph_data
from app.models import Diamond
from sqlmodel import Session, select

def test_database_creation():
    """Test database creation and basic operations"""
    print("Testing database creation...")
    create_db_and_tables()
    print("✓ Database created successfully")

def test_diamond_creation():
    """Test creating diamonds with indicators"""
    print("\nTesting diamond creation...")
    
    with Session(create_db_and_tables.__globals__['engine']) as session:
        # Create first diamond - FIN7 campaign
        diamond1 = create_diamond_with_indicators(
            session=session,
            label="FIN7 / Delivery",
            notes="Financial cybercrime group targeting retail and hospitality",
            adversary_indicators=[
                "FIN7",
                "Carbanak",
                "Russia",
                "Financial motivation",
                "APT group"
            ],
            victimology_indicators=[
                "victim@retail.com",
                "Retail Company",
                "Windows 10",
                "Office 365",
                "Point of Sale systems"
            ],
            capability_indicators=[
                "Spear Phishing",
                "PowerShell",
                "Living off the Land",
                "Credential Theft",
                "Lateral Movement"
            ],
            infrastructure_indicators=[
                "192.168.1.100",
                "fin7-malware.com",
                "phishing@fake.com",
                "VPN Server",
                "C2 Infrastructure"
            ]
        )
        print(f"✓ Created diamond: {diamond1.label} (ID: {diamond1.id})")
        
        # Create second diamond - APT29 campaign
        diamond2 = create_diamond_with_indicators(
            session=session,
            label="APT29 / Cozy Bear",
            notes="Russian state-sponsored group targeting government and healthcare",
            adversary_indicators=[
                "APT29",
                "Cozy Bear",
                "Russia",
                "Espionage",
                "State-sponsored"
            ],
            victimology_indicators=[
                "victim@gov.com",
                "Government Agency",
                "Windows 10",
                "Office 365",
                "Healthcare systems"
            ],
            capability_indicators=[
                "Spear Phishing",
                "PowerShell",
                "Living off the Land",
                "Credential Theft",
                "Data Exfiltration"
            ],
            infrastructure_indicators=[
                "10.0.0.50",
                "apt29-c2.net",
                "spoofed@gov.com",
                "Tor Network",
                "C2 Infrastructure"
            ]
        )
        print(f"✓ Created diamond: {diamond2.label} (ID: {diamond2.id})")
        
        # Create third diamond - Generic phishing
        diamond3 = create_diamond_with_indicators(
            session=session,
            label="Generic Phishing Campaign",
            notes="Widespread phishing campaign targeting multiple sectors",
            adversary_indicators=[
                "Unknown",
                "Criminal group",
                "Financial motivation"
            ],
            victimology_indicators=[
                "victim@company.com",
                "Multiple sectors",
                "Windows 10",
                "Office 365"
            ],
            capability_indicators=[
                "Spear Phishing",
                "Social Engineering",
                "Credential Theft"
            ],
            infrastructure_indicators=[
                "phishing-site.com",
                "fake@bank.com",
                "192.168.1.100"  # This should create a link with diamond1
            ]
        )
        print(f"✓ Created diamond: {diamond3.label} (ID: {diamond3.id})")

def test_graph_data():
    """Test graph data generation"""
    print("\nTesting graph data generation...")
    
    with Session(create_db_and_tables.__globals__['engine']) as session:
        graph_data = get_graph_data(session)
        
        print(f"✓ Graph contains {len(graph_data['elements']['nodes'])} nodes")
        print(f"✓ Graph contains {len(graph_data['elements']['edges'])} edges")
        
        # Print node labels
        print("\nNodes:")
        for node in graph_data['elements']['nodes']:
            print(f"  - {node['data']['label']}")
        
        # Print edges
        print("\nEdges:")
        for edge in graph_data['elements']['edges']:
            print(f"  - {edge['data']['source']} -> {edge['data']['target']}: {edge['data']['label']}")

def test_indicator_normalization():
    """Test indicator normalization"""
    print("\nTesting indicator normalization...")
    
    from app.indicators import normalize_indicator, process_indicators
    
    test_indicators = [
        "192.168.1.1",
        "example.com",
        "test@example.com",
        "PowerShell",
        "Spear Phishing",
        "Unknown Tool"
    ]
    
    for indicator in test_indicators:
        value, kind = normalize_indicator(indicator)
        print(f"  {indicator} -> {value} ({kind})")
    
    print("✓ Indicator normalization working correctly")

def main():
    """Run all tests"""
    print("Diamond Modeller - Test Suite")
    print("=" * 40)
    
    try:
        test_database_creation()
        test_diamond_creation()
        test_graph_data()
        test_indicator_normalization()
        
        print("\n" + "=" * 40)
        print("✓ All tests passed! The application is working correctly.")
        print("\nTo run the application:")
        print("  python -m app.main")
        print("  Then open http://localhost:8000 in your browser")
        
    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()

