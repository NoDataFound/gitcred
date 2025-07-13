import os
import subprocess
import json
import re
from .base_analyzer import BaseAnalyzer

class BashAnalyzer(BaseAnalyzer):
    """
    Concrete analyzer for Bash/Shell scripts.
    Relies on the external tool: shellcheck.
    """

    def get_dependencies(self):
        """
        Parses shell scripts for common commands that imply a dependency on a tool.
        This is a heuristic for identifying tool usage.
        """
        deps = set()
        # A list of common commands that are good indicators of the script's purpose
        known_commands = [
            'curl', 'wget', 'jq', 'yq', 'git', 'docker', 'kubectl', 'helm',
            'terraform', 'ansible', 'aws', 'gcloud', 'az', 'openssl', 'sed', 'awk'
        ]
        # Regex to find if a known command is used as a standalone word
        command_re = re.compile(r'\b(' + '|'.join(known_commands) + r')\b')
        target_extensions = (".sh", ".bash", ".ksh")

        for root, _, files in os.walk(self.repo_path):
            for file in files:
                if file.endswith(target_extensions):
                    file_path = os.path.join(root, file)
                    try:
                        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read()
                            found_cmds = command_re.findall(content)
                            deps.update(found_cmds)
                    except Exception:
                        pass
        return list(deps)

    def analyze_quality(self):
        """
        Analyzes shell scripts for quality and style issues using shellcheck.
        The number of violations is the total number of comments from shellcheck.
        """
        violations = 0
        files_analyzed = 0
        
        try:
            # Run shellcheck on the entire directory, getting JSON output
            result = subprocess.run(
                ['shellcheck', '-f', 'json', '-S', 'warning', '.'],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                check=False
            )
            if result.stdout:
                report = json.loads(result.stdout)
                # Count the number of files with issues and the total number of comments (violations)
                files_analyzed = len(report)
                for file_report in report:
                    violations += len(file_report.get('comments', []))
        except FileNotFoundError:
            print("Warning: 'shellcheck' not found. Skipping Shell quality analysis.")
            return {"violations": 0, "files_analyzed": 0}
        except (json.JSONDecodeError, Exception):
            # Handle cases where shellcheck fails or returns bad JSON
            return {"violations": 0, "files_analyzed": 0}

        return {"violations": violations, "files_analyzed": files_analyzed}

    def analyze_security(self):
        """
        Uses shellcheck's findings to identify security-related issues.
        Also performs a simple regex search for potentially hardcoded secrets.
        """
        issues = []
        
        # 1. Get security warnings from shellcheck
        try:
            result = subprocess.run(
                ['shellcheck', '-f', 'json', '-S', 'style', '.'],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                check=False
            )
            if result.stdout:
                report = json.loads(result.stdout)
                for file_report in report:
                    for comment in file_report.get('comments', []):
                        # Shellcheck's SC2046, SC2006, etc., are often security-relevant
                        issues.append({
                            'issue_severity': comment.get('level', 'warning').upper(),
                            'issue_text': f"[{comment.get('code')}] {comment.get('message')}",
                            'filename': file_report.get('file')
                        })
        except (FileNotFoundError, json.JSONDecodeError):
            pass # We already warned about shellcheck in the quality check

        # 2. Regex for hardcoded secrets
        secret_re = re.compile(r'(key|secret|token|password)\s*=\s*["\'][A-Za-z0-9\/\+]{12,}', re.IGNORECASE)
        target_extensions = (".sh", ".bash", ".ksh", ".env")

        for root, _, files in os.walk(self.repo_path):
            for file in files:
                if file.endswith(target_extensions):
                    file_path = os.path.join(root, file)
                    try:
                        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                            for i, line in enumerate(f, 1):
                                if secret_re.search(line):
                                    issues.append({
                                        'issue_severity': 'HIGH',
                                        'issue_text': f"Potential hardcoded secret found on line {i}",
                                        'filename': os.path.relpath(file_path, self.repo_path)
                                    })
                    except Exception:
                        pass
                        
        return issues

    def harvest_comments(self):
        """Extracts single-line comments (#) from shell scripts."""
        comments = []
        target_extensions = (".sh", ".bash", ".ksh")

        for root, _, files in os.walk(self.repo_path):
            for file in files:
                if file.endswith(target_extensions):
                    file_path = os.path.join(root, file)
                    try:
                        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                            for i, line in enumerate(f, 1):
                                # Skip shebang line
                                if i == 1 and line.startswith("#!"):
                                    continue
                                if '#' in line:
                                    comment_text = line.split('#', 1)[1].strip()
                                    if comment_text:
                                        comments.append({
                                            "file_name": os.path.relpath(file_path, self.repo_path),
                                            "line": i,
                                            "comment": comment_text
                                        })
                    except Exception:
                        pass
        return comments