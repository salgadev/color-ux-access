"""
Accessibility Report Generator based on WCAG Standards
"""

import json
import re
from datetime import datetime
from typing import Dict, List, Any, Optional

class WCAGStandards:
    """WCAG 2.1/2.2 color contrast and color usage standards"""
    
    # Contrast ratios
    CONTRAST_RATIOS = {
        'AA_NORMAL_TEXT': 4.5,
        'AA_LARGE_TEXT': 3.0,
        'AA_UI_COMPONENTS': 3.0,  # WCAG 2.1
        'AAA_NORMAL_TEXT': 7.0,
        'AAA_LARGE_TEXT': 4.5
    }
    
    # Success criteria references
    SUCCESS_CRITERIA = {
        '1.4.3': 'Contrast (Minimum) - AA',
        '1.4.6': 'Contrast (Enhanced) - AAA',
        '1.4.11': 'Non-text Contrast - AA (WCAG 2.1)',
        '1.4.1': 'Use of Color - A'
    }

class AccessibilityReport:
    """Generate accessibility reports based on VLM analysis"""
    
    def __init__(self):
        self.standards = WCAGStandards()
    
    def parse_vlm_output(self, vlm_output: str) -> List[Dict[str, Any]]:
        """
        Parse VLM output to extract accessibility issues
        Expected format: JSON array of issues with description, type, remediation, bbox
        """
        issues = []
        
        try:
            # Try to extract JSON from the output
            json_match = re.search(r'\[.*\]', vlm_output, re.DOTALL)
            if json_match:
                json_str = json_match.group()
                parsed_issues = json.loads(json_str)
                
                if isinstance(parsed_issues, list):
                    for issue in parsed_issues:
                        if isinstance(issue, dict):
                            # Standardize issue format
                            standardized_issue = {
                                'description': issue.get('description', ''),
                                'type': issue.get('type', 'unknown'),
                                'remediation': issue.get('remediation', ''),
                                'bbox': issue.get('bbox', issue.get('point', [])),
                                'wcag_references': self._map_to_wcag(issue.get('type', '')),
                                'severity': self._assess_severity(issue.get('type', ''), issue.get('description', ''))
                            }
                            issues.append(standardized_issue)
                else:
                    # Single issue object
                    if isinstance(parsed_issues, dict):
                        issue = parsed_issues
                        standardized_issue = {
                            'description': issue.get('description', ''),
                            'type': issue.get('type', 'unknown'),
                            'remediation': issue.get('remediation', ''),
                            'bbox': issue.get('bbox', issue.get('point', [])),
                            'wcag_references': self._map_to_wcag(issue.get('type', '')),
                            'severity': self._assess_severity(issue.get('type', ''), issue.get('description', ''))
                        }
                        issues.append(standardized_issue)
            else:
                # Fallback: treat as text analysis
                issues = self._parse_text_analysis(vlm_output)
                
        except (json.JSONDecodeError, Exception) as e:
            print(f"Error parsing VLM output: {e}")
            # Fallback to text parsing
            issues = self._parse_text_analysis(vlm_output)
        
        return issues
    
    def _map_to_wcag(self, issue_type: str) -> List[str]:
        """Map issue type to WCAG success criteria."""
        issue_type_lower = issue_type.lower()
        wcag_refs = []

        if 'contrast' in issue_type_lower and 'ui' in issue_type_lower:
            wcag_refs.append('1.4.11')  # Non-text Contrast
        if 'contrast' in issue_type_lower and 'text' in issue_type_lower:
            wcag_refs.extend(['1.4.3', '1.4.6'])  # Contrast (Minimum and Enhanced)
        if 'color-only' in issue_type_lower or 'color only' in issue_type_lower:
            wcag_refs.append('1.4.1')  # Use of Color
        if 'color-dependent' in issue_type_lower or 'color dependent' in issue_type_lower:
            wcag_refs.append('1.4.1')
        if 'ui' in issue_type_lower or 'component' in issue_type_lower or 'button' in issue_type_lower or 'input' in issue_type_lower:
            if '1.4.11' not in wcag_refs:
                wcag_refs.append('1.4.11')  # Non-text Contrast

        return wcag_refs if wcag_refs else ['1.4.3']  # Default to contrast check

    def _assess_severity(self, issue_type: str, description: str) -> str:
        """Assess severity based on issue type and description."""
        issue_type_lower = issue_type.lower()
        desc_lower = description.lower()

        # Critical: blocks core task completion
        if any(word in issue_type_lower for word in ['critical', 'severe', 'major']):
            return 'critical'
        if any(word in desc_lower for word in [
            'cannot submit', 'cannot complete', 'form submission blocked',
            'invisible', 'unreadable', 'cannot see', 'cannot distinguish',
            'error state invisible', 'no way to tell',
        ]):
            return 'critical'

        # Serious: significant confusion or delay
        if any(word in issue_type_lower for word in ['serious', 'error state', 'status indicator']):
            return 'serious'
        if any(word in desc_lower for word in [
            'difficult', 'hard to see', 'low visibility', 'confusing',
            'cannot identify', 'cannot tell which', 'ambiguous',
        ]):
            return 'serious'

        # Moderate: workaround exists
        if any(word in issue_type_lower for word in ['moderate', 'medium']):
            return 'moderate'
        if any(word in desc_lower for word in ['minor', 'slight', 'could be better']):
            return 'moderate'

        # Contrast-specific: extract ratio if mentioned
        if 'contrast' in issue_type_lower:
            contrast_match = re.search(r'(\d+(?:\.\d+)?):1', desc_lower)
            if contrast_match:
                ratio = float(contrast_match.group(1))
                if ratio < 3.0:
                    return 'critical'
                elif ratio < 4.5:
                    return 'serious'
                else:
                    return 'moderate'

        return 'moderate'  # Default
    
    def _parse_text_analysis(self, text: str) -> List[Dict[str, Any]]:
        """Parse free-text VLM analysis into structured issues"""
        issues = []
        
        # Simple heuristic: look for common accessibility issue patterns
        lines = text.split('\n')
        current_issue = {}
        
        for line in lines:
            line = line.strip()
            if not line:
                if current_issue:
                    issues.append(self._finalize_issue(current_issue))
                    current_issue = {}
                continue
                
            # Look for issue indicators
            if any(word in line.lower() for word in ['issue', 'problem', 'concern', 'violation', 'fail']):
                if current_issue:
                    issues.append(self._finalize_issue(current_issue))
                current_issue = {
                    'description': line,
                    'type': self._infer_type_from_text(line),
                    'remediation': '',
                    'bbox': []
                }
            elif 'recommend' in line.lower() or 'suggest' in line.lower() or 'should' in line.lower():
                if current_issue:
                    current_issue['remediation'] = line
            elif current_issue and 'description' in current_issue:
                # Append to description
                current_issue['description'] += ' ' + line
        
        # Don't forget the last issue
        if current_issue:
            issues.append(self._finalize_issue(current_issue))
            
        return issues
    
    def _infer_type_from_text(self, text: str) -> str:
        """Infer issue type from text description"""
        text_lower = text.lower()
        if 'contrast' in text_lower:
            return 'low contrast'
        elif 'color' in text_lower and ('dependent' in text_lower or 'only' in text_lower):
            return 'color-dependent element'
        elif 'text' in text_lower and ('size' in text_lower or 'readable' in text_lower):
            return 'text readability'
        else:
            return 'accessibility issue'
    
    def _finalize_issue(self, issue: Dict[str, Any]) -> Dict[str, Any]:
        """Finalize issue with WCAG references and severity"""
        issue['wcag_references'] = self._map_to_wcag(issue.get('type', ''))
        issue['severity'] = self._assess_severity(issue.get('type', ''), issue.get('description', ''))
        return issue
    
    def generate_report(self, url: str, vlm_analysis: str, screenshot_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Generate a complete accessibility report
        
        Returns:
            Dictionary containing the full report
        """
        issues = self.parse_vlm_output(vlm_analysis)
        
        # Calculate summary statistics
        total_issues = len(issues)
        high_severity = len([i for i in issues if i.get('severity') == 'high'])
        medium_severity = len([i for i in issues if i.get('severity') == 'medium'])
        low_severity = len([i for i in issues if i.get('severity') == 'low'])
        
        # Determine overall compliance level
        if high_severity == 0 and medium_severity <= 2:
            compliance_level = "Good"
        elif high_severity == 0:
            compliance_level = "Fair"
        elif high_severity <= 2:
            compliance_level = "Poor"
        else:
            compliance_level = "Non-compliant"
        
        report = {
            'metadata': {
                'url': url,
                'timestamp': datetime.now().isoformat(),
                'tool': 'Color-UX-Access with Qwen2.5-VL-32B-Instruct',
                'wcag_version': '2.1/2.2',
                'screenshot_analyzed': screenshot_path
            },
            'summary': {
                'total_issues': total_issues,
                'high_severity': high_severity,
                'medium_severity': medium_severity,
                'low_severity': low_severity,
                'compliance_level': compliance_level,
                'wcag_version_tested': '2.1/2.2 AA'
            },
            'issues': issues,
            'wcag_standards_referenced': list(self.standards.SUCCESS_CRITERIA.values()),
            'recommendations': self._generate_recommendations(issues)
        }
        
        return report
    
    def _generate_recommendations(self, issues: List[Dict[str, Any]]) -> List[str]:
        """Generate prioritized recommendations based on issues"""
        recommendations = []
        
        # Group issues by type for batch recommendations
        issue_types = {}
        for issue in issues:
            issue_type = issue.get('type', 'unknown')
            if issue_type not in issue_types:
                issue_types[issue_type] = []
            issue_types[issue_type].append(issue)
        
        # Priority recommendations
        if any('contrast' in issue_type.lower() for issue_type in issue_types.keys()):
            recommendations.append({
                'priority': 'high',
                'category': 'Color Contrast',
                'recommendation': 'Ensure all text and UI components meet WCAG 2.1 AA contrast ratios (4.5:1 for normal text, 3:1 for large text and UI components). Use a contrast checker to verify compliance.',
                'wcag_reference': '1.4.3, 1.4.11'
            })
        
        if any('color-dependent' in issue_type.lower() for issue_type in issue_types.keys()):
            recommendations.append({
                'priority': 'high',
                'category': 'Use of Color',
                'recommendation': 'Do not rely solely on color to convey information. Add text labels, icons, or patterns to supplement color coding.',
                'wcag_reference': '1.4.1'
            })
        
        # Add general recommendations
        recommendations.append({
            'priority': 'medium',
            'category': 'Testing',
            'recommendation': 'Test with actual users who have color vision deficiencies and use automated accessibility testing tools regularly.',
            'wcag_reference': 'General'
        })
        
        return recommendations
    
    def format_report_as_markdown(self, report: Dict[str, Any]) -> str:
        """Format the report as readable Markdown"""
        md = []
        md.append(f"# Accessibility Audit Report")
        md.append(f"**URL:** {report['metadata']['url']}")
        md.append(f"**Timestamp:** {report['metadata']['timestamp']}")
        md.append(f"**Tool:** {report['metadata']['tool']}")
        md.append(f"**WCAG Version:** {report['metadata']['wcag_version']}")
        md.append("")
        
        md.append("## Executive Summary")
        summary = report['summary']
        md.append(f"- **Total Issues Found:** {summary['total_issues']}")
        md.append(f"- **High Severity:** {summary['high_severity']}")
        md.append(f"- **Medium Severity:** {summary['medium_severity']}")
        md.append(f"- **Low Severity:** {summary['low_severity']}")
        md.append(f"- **Compliance Level:** {summary['compliance_level']}")
        md.append(f"- **WCAG Level Tested:** {summary['wcag_version_tested']}")
        md.append("")
        
        md.append("## Issues Found")
        if not report['issues']:
            md.append("No accessibility issues detected.")
        else:
            for i, issue in enumerate(report['issues'], 1):
                md.append(f"### Issue {i}: {issue.get('type', 'Unknown').title()}")
                md.append(f"- **Description:** {issue.get('description', 'N/A')}")
                md.append(f"- **Type:** {issue.get('type', 'N/A')}")
                md.append(f"- **Severity:** {issue.get('severity', 'N/A').title()}")
                md.append(f"- **Location:** {issue.get('bbox', 'Not specified')}")
                if issue.get('wcag_references'):
                    md.append(f"- **WCAG References:** {', '.join(issue['wcag_references'])}")
                md.append(f"- **Remediation:** {issue.get('remediation', 'No specific remediation provided')}")
                md.append("")
        
        md.append("## Recommendations")
        for rec in report['recommendations']:
            md.append(f"### {rec['category']} ({rec['priority'].title()} Priority)")
            md.append(f"{rec['recommendation']}")
            md.append(f"*WCAG Reference: {rec['wcag_reference']}*")
            md.append("")
        
        md.append("## WCAG Standards Referenced")
        for standard in report['wcag_standards_referenced']:
            md.append(f"- {standard}")
        md.append("")
        
        md.append("--")
        md.append(f"*Report generated by Color-UX-Access on {report['metadata']['timestamp']}*")
        
        return '\n'.join(md)

def main():
    """Test the report generator"""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python accessibility_report.py <vlm_output_file_or_text> [url]")
        sys.exit(1)
    
    # Read VLM output
    vlm_input = sys.argv[1]
    url = sys.argv[2] if len(sys.argv) > 2 else "https://example.com"
    
    # Try to read from file, otherwise treat as direct text
    try:
        with open(vlm_input, 'r', encoding='utf-8') as f:
            vlm_output = f.read()
    except FileNotFoundError:
        vlm_output = vlm_input
    
    # Generate report
    reporter = AccessibilityReport()
    report = reporter.generate_report(url, vlm_output)
    
    # Output as JSON
    print(json.dumps(report, indent=2))
    
    # Also output markdown version
    print("\n" + "="*50)
    print("MARKDOWN VERSION:")
    print("="*50)
    print(reporter.format_report_as_markdown(report))

if __name__ == "__main__":
    main()