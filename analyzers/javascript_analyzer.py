import os
import subprocess
import json
import re
from .base_analyzer import BaseAnalyzer

class JavaScriptAnalyzer(BaseAnalyzer):
    def __init__(self, repo_path, excluded_lines=None): 
        super().__init__(repo_path)
        self.excluded_lines = excluded_lines or set() 
    def get_dependencies(self):
        """Parses package.json for dependencies."""
        deps = []
        package_json_path = os.path.join(self.repo_path, 'package.json')
        if os.path.exists(package_json_path):
            try:
                with open(package_json_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # Get both regular and dev dependencies
                    if 'dependencies' in data and isinstance(data['dependencies'], dict):
                        deps.extend(data['dependencies'].keys())
                    if 'devDependencies' in data and isinstance(data['devDependencies'], dict):
                        deps.extend(data['devDependencies'].keys())
            except (json.JSONDecodeError, IOError):
                # Ignore if package.json is malformed or unreadable
                pass
        return list(set(deps)) # Return unique dependencies

    def analyze_quality(self):
        """Analyzes JS/TS files for style violations using ESLint."""
        violations = 0
        files_analyzed = 0
        # Check if eslint is configured in package.json to avoid running it unnecessarily
        package_json_path = os.path.join(self.repo_path, 'package.json')
        has_eslint = False
        if os.path.exists(package_json_path):
            with open(package_json_path, 'r', encoding='utf-8') as f:
                content = f.read()
                if '"eslint"' in content:
                    has_eslint = True
        
        if not has_eslint:
            return {"violations": 0, "files_analyzed": 0}

        try:
            # Run eslint with --format json to get machine-readable output
            # npx allows running without a global install
            result = subprocess.run(
                ['npx', 'eslint', '.', '--format', 'json'],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                check=False
            )
            # ESLint can return an empty string if no files are found
            if result.stdout:
                report = json.loads(result.stdout)
                files_analyzed = len(report)
                for file_report in report:
                    violations += file_report.get('errorCount', 0)
        except (json.JSONDecodeError, FileNotFoundError):
            # Fail gracefully if npx/eslint is not found or JSON is bad
            return {"violations": 0, "files_analyzed": 0}

        return {"violations": violations, "files_analyzed": files_analyzed}

    def analyze_security(self):
        """Analyzes dependencies for vulnerabilities using npm audit."""
        package_lock_path = os.path.join(self.repo_path, 'package-lock.json')
        
        # npm audit requires a lock file. If it doesn't exist, we can't run it.
        if not os.path.exists(package_lock_path):
            # Attempt to create it by running npm install
            try:
                subprocess.run(['npm', 'install', '--package-lock-only'], cwd=self.repo_path, capture_output=True)
                if not os.path.exists(package_lock_path):
                    return [] # Still no lock file, can't proceed
            except FileNotFoundError:
                return [] # npm not installed

        try:
            # Run npm audit with --json flag
            result = subprocess.run(
                ['npm', 'audit', '--json'],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                check=False
            )
            if result.stdout:
                report = json.loads(result.stdout)
                # We can simplify the output for consistency
                simplified_issues = []
                advisories = report.get('advisories', {})
                for advisory_id in advisories:
                    advisory = advisories[advisory_id]
                    simplified_issues.append({
                        'issue_severity': advisory.get('severity', 'UNKNOWN').upper(),
                        'issue_text': advisory.get('title', 'No title'),
                        'filename': advisory.get('module_name', 'Unknown module')
                    })
                return simplified_issues
        except (json.JSONDecodeError, FileNotFoundError):
            return [] # Fail gracefully if npm not found or JSON is bad
        
        return []

    def harvest_comments(self):
        """Extracts single-line and block comments from JS/TS files."""
        comments = []
        # Regex to find // single line comments and /* block comments */
        comment_re = re.compile(r'\/\/(.*)|\/\*(.*?)\*\/', re.DOTALL)
        target_extensions = (".js", ".jsx", ".ts", ".tsx")

        for root, _, files in os.walk(self.repo_path):
            for file in files:
                if file.endswith(target_extensions):
                    file_path = os.path.join(root, file)
                    try:
                        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read()
                            # Find all non-overlapping matches
                            for match in comment_re.finditer(content):
                                # The matched text is either in group 1 (//) or group 2 (/*)
                                comment_text = match.group(1) or match.group(2)
                                if comment_text:
                                    # Basic line number approximation by counting newlines before the match
                                    line_num = content.count('\n', 0, match.start()) + 1
                                    comments.append({
                                        "file_name": os.path.relpath(file_path, self.repo_path),
                                        "line": line_num,
                                        "comment": comment_text.strip()
                                    })
                    except Exception:
                        pass
        return comments