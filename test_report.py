#!/usr/bin/env python
"""
Test script to generate an accessibility report using the mock VLM from app.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import analyze_image_with_vlm
from PIL import Image
import json
from accessibility_report import AccessibilityReport

def main():
    # Create a dummy image for testing
    img = Image.new('RGB', (100, 100), color='white')
    
    # Get mock VLM analysis
    vlm_output = analyze_image_with_vlm(img, "Test prompt")
    print("VLM Output:")
    print(vlm_output)
    
    # Generate report
    reporter = AccessibilityReport()
    report = reporter.generate_report("https://example.com", vlm_output)
    
    # Print report as JSON
    print("\nAccessibility Report (JSON):")
    print(json.dumps(report, indent=2))
    
    # Also output markdown
    print("\n" + "="*50)
    print("MARKDOWN VERSION:")
    print("="*50)
    print(reporter.format_report_as_markdown(report))

if __name__ == "__main__":
    main()