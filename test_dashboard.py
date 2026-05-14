#!/usr/bin/env python3
"""Test dashboard by checking imports."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_dashboard_imports():
    print("Testing dashboard imports...")
    try:
        import streamlit
        print(f"✓ Streamlit: {streamlit.__version__}")
        import plotly
        print(f"✓ Plotly: {plotly.__version__}")
        print("✓ Dashboard module OK")
        return True
    except ImportError as e:
        print(f"✗ Import error: {e}")
        return False

if __name__ == "__main__":
    test_dashboard_imports()