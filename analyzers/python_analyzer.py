import os
import subprocess
import json
import re
from .base_analyzer import BaseAnalyzer

class PythonAnalyzer(BaseAnalyzer):
    """Concrete analyzer for Python repositories that can exclude specific lines."""

    def __init__(self, repo_path, excluded_lines=None):
        """
        Initialize the analyzer.
        :param repo_path: Path to the repository.
        :param excluded_lines: A set of (file_path, line_number) tuples to ignore.
        """
        super().__init__(repo_path)
        self.excluded_lines = excluded_lines or set()

    def get_dependencies(self):
        # This function is unaffected by line exclusion
        deps, req_path = [], os.path.join(self.repo_path, 'requirements.txt')
        if os.path.exists(req_path):
            try:
                with open(req_path, 'r', errors='ignore') as f:
                    deps = [line.split('==')[0].strip().lower() for line in f if line.strip() and not line.startswith('#')]
            except Exception: pass
        return deps

    def harvest_comments(self):
        """Extracts comments, skipping any lines flagged by the Vibe Analyzer."""
        comments = []
        for root, _, files in os.walk(self.repo_path):
            for file in files:
                if file.endswith(".py"):
                    file_path = os.path.join(root, file)
                    relative_path = os.path.relpath(file_path, self.repo_path)
                    try:
                        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                            for i, line in enumerate(f, 1):
                                # *** EXCLUSION LOGIC HERE ***
                                if (relative_path, i) in self.excluded_lines:
                                    continue
                                
                                if '#' in line:
                                    comment_text = line.split('#', 1)[1].strip()
                                    if comment_text:
                                        comments.append({
                                            "file_name": relative_path,
                                            "line": i,
                                            "comment": comment_text
                                        })
                    except Exception:
                        pass
        return comments

    def analyze_quality(self):
        """Analyzes PEP 8 compliance, skipping violations from flagged lines."""
        violations, files_analyzed = 0, 0
        for root, _, files in os.walk(self.repo_path):
            for file in files:
                if file.endswith(".py"):
                    files_analyzed += 1
                    file_path = os.path.join(root, file)
                    relative_path = os.path.relpath(file_path, self.repo_path)
                    try:
                        result = subprocess.run(['flake8', file_path], capture_output=True, text=True, check=False)
                        if result.stdout:
                            for line in result.stdout.strip().split('\n'):
                                try:
                                    # flake8 format is usually file:line:col: code message
                                    line_num = int(line.split(':')[1])
                                    # *** EXCLUSION LOGIC HERE ***
                                    if (relative_path, line_num) not in self.excluded_lines:
                                        violations += 1
                                except (IndexError, ValueError):
                                    # If parsing fails, just count it
                                    violations += 1
                    except Exception:
                        pass
        return {"violations": violations, "files_analyzed": files_analyzed}

    def analyze_security(self):
        """Analyzes for vulnerabilities, skipping issues from flagged lines."""
        try:
            result = subprocess.run(['bandit', '-r', self.repo_path, '-f', 'json'], capture_output=True, text=True, check=False)
            report = json.loads(result.stdout)
            
            filtered_results = []
            for issue in report.get('results', []):
                # Bandit's filename is already relative
                filename = issue.get('filename')
                line_range = issue.get('line_range', [])
                
                # Check if any line in the range is excluded
                is_excluded = any((filename, i) in self.excluded_lines for i in line_range)
                
                # *** EXCLUSION LOGIC HERE ***
                if not is_excluded:
                    filtered_results.append(issue)

            return filtered_results
        except Exception:
            return []