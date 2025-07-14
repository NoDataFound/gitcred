import os
import re

def check_typography(content):
    """Yields findings for typographic tics."""
    # Em-dash (—) or En-dash (–) are strong indicators
    for i, line in enumerate(content.split('\n'), 1):
        if re.search(r'—|–', line):
            yield {
                "line_number": i,
                "line_content": line.strip(),
                "reason": "Typographic Anomaly: Contains em-dash or en-dash."
            }

def check_comment_style(content):
    """Yields findings for AI-like comment styles."""
    lines = content.split('\n')
    human_markers = ('TODO', 'FIXME', 'HACK', 'XXX', 'NOTE')
    
    for i, line in enumerate(lines, 1):
        stripped_line = line.strip()
        if not stripped_line.startswith('#'):
            continue

        # Skip human markers, as they are a strong signal of human authorship
        if any(marker in stripped_line.upper() for marker in human_markers):
            continue

        # Flag comments that are perfect, full sentences stating the obvious
        # Heuristic: Starts with a capital letter, ends with a period, has spaces (is a sentence).
        comment_text = stripped_line.lstrip('# ').strip()
        if comment_text and comment_text[0].isupper() and comment_text.endswith('.') and ' ' in comment_text:
            yield {
                "line_number": i,
                "line_content": line.strip(),
                "reason": "Verbose Comment: Overly formal, full-sentence comment."
            }

def check_naming_conventions(content):
    """Yields findings for overly generic variable/function names."""
    generic_names = [
        'data_to_process', 'process_data', 'my_list', 'temp_variable',
        'input_string', 'output_data', 'file_path', 'item_list', 'result_data'
    ]
    for i, line in enumerate(content.split('\n'), 1):
        for name in generic_names:
            # Use regex to find whole words to avoid partial matches (e.g., 'item' in 'items')
            if re.search(fr'\b{name}\b', line):
                yield {
                    "line_number": i,
                    "line_content": line.strip(),
                    "reason": f"Generic Naming: Uses placeholder name '{name}'."
                }
                break # Move to next line once one generic name is found

class VibeAnalyzer:
    """
    Analyzes a repository's "vibe", logs findings, and returns lines to exclude.
    """
    def __init__(self, repo_path):
        self.repo_path = repo_path
        self.findings = []

    def analyze(self):
        """
        Runs all heuristic checks on the repository files and collects findings.
        """
        for root, _, files in os.walk(self.repo_path):
            for file in files:
                file_path = os.path.join(root, file)
                relative_path = os.path.relpath(file_path, self.repo_path)
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                except Exception:
                    continue

                # Run checks and add file context to each finding
                if file.lower().endswith(('.md', '.txt')):
                    for finding in check_typography(content):
                        finding['file_name'] = relative_path
                        self.findings.append(finding)

                if file.lower().endswith(('.py', '.js', '.ts', '.c', '.cpp', '.sh')):
                    for finding in check_comment_style(content):
                        finding['file_name'] = relative_path
                        self.findings.append(finding)
                    for finding in check_naming_conventions(content):
                        finding['file_name'] = relative_path
                        self.findings.append(finding)
        
        # Create a simple set of (file, line) tuples for easy exclusion lookup
        excluded_lines = {(f['file_name'], f['line_number']) for f in self.findings}

        return self.findings, excluded_lines