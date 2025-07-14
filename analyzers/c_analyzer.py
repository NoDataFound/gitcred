import os
import subprocess
import json
import re
from .base_analyzer import BaseAnalyzer

class CAnalyzer(BaseAnalyzer):
    def __init__(self, repo_path, excluded_lines=None): 
        super().__init__(repo_path)
        self.excluded_lines = excluded_lines or set() 

    def get_dependencies(self):
        """
        Parses .c and .h files for #include <...> directives.
        It uses a simple heuristic: includes with a '/' are likely external libraries.
        e.g., <curl/curl.h> or <openssl/ssl.h>
        """
        deps = set()
        # Regex to find system-style includes like #include <library/header.h>
        include_re = re.compile(r'^\s*#include\s+<([^>]+)>')
        target_extensions = (".c", ".h", ".cpp", ".hpp")

        for root, _, files in os.walk(self.repo_path):
            for file in files:
                if file.endswith(target_extensions):
                    file_path = os.path.join(root, file)
                    try:
                        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                            for line in f:
                                match = include_re.match(line)
                                if match:
                                    include_path = match.group(1)
                                    # Heuristic: if it contains a slash, it's likely a library subdirectory
                                    if '/' in include_path:
                                        # Extract the library name (e.g., 'curl' from 'curl/curl.h')
                                        lib_name = include_path.split('/')[0]
                                        deps.add(lib_name)
                    except Exception:
                        pass
        return list(deps)

    def analyze_quality(self):
        """
        Analyzes C/C++ files for style and logic errors using clang-tidy.
        NOTE: For best results, the repo should contain a 'compile_commands.json' file.
        This analyzer will attempt to run without it, but results may be limited.
        """
        violations = 0
        files_analyzed = 0
        target_extensions = (".c", ".h", ".cpp", ".hpp")
        
        try:
            for root, _, files in os.walk(self.repo_path):
                for file in files:
                    if file.endswith(target_extensions):
                        files_analyzed += 1
                        file_path = os.path.join(root, file)
                        # We add '--' to separate clang-tidy options from file paths
                        # We hide stdout and check stderr for warnings/errors
                        result = subprocess.run(
                            ['clang-tidy', file_path, '--'],
                            capture_output=True, text=True, check=False
                        )
                        if result.stderr:
                            # Simple metric: count the number of lines containing "warning:"
                            violations += result.stderr.lower().count("warning:")
        except FileNotFoundError:
            # clang-tidy is not installed, so we can't analyze.
            print("Warning: 'clang-tidy' not found. Skipping C/C++ quality analysis.")
            return {"violations": 0, "files_analyzed": 0}
            
        return {"violations": violations, "files_analyzed": files_analyzed}

    def analyze_security(self):
        """Analyzes C/C++ code for vulnerabilities using flawfinder."""
        issues = []
        try:
            # Flawfinder runs on the entire directory at once.
            result = subprocess.run(
                ['flawfinder', '--quiet', '--csv', self.repo_path],
                capture_output=True, text=True, check=False
            )
            # The CSV output is: File,Line,Column,Level,Category,Name,Warning
            if result.stdout:
                lines = result.stdout.strip().split('\n')
                # Skip the header line
                for line in lines[1:]:
                    parts = line.split(',', 6) # Split into 7 parts max
                    if len(parts) == 7:
                        issues.append({
                            'issue_severity': f"LEVEL_{parts[3]}", # e.g., LEVEL_4
                            'issue_text': f"[{parts[5]}] {parts[6]}", # e.g., [gets] Check buffer boundaries
                            'filename': parts[0]
                        })
        except FileNotFoundError:
            print("Warning: 'flawfinder' not found. Skipping C/C++ security analysis.")
            return []
            
        return issues

    def harvest_comments(self):
        """Extracts single-line (//) and block (/*...*/) comments from C/C++ files."""
        comments = []
        # This regex is robust for both comment types
        comment_re = re.compile(r'\/\/(.*)|\/\*(.*?)\*\/', re.DOTALL)
        target_extensions = (".c", ".h", ".cpp", ".hpp")

        for root, _, files in os.walk(self.repo_path):
            for file in files:
                if file.endswith(target_extensions):
                    file_path = os.path.join(root, file)
                    try:
                        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read()
                            for match in comment_re.finditer(content):
                                # Group 1 is for //, Group 2 is for /* */
                                comment_text = match.group(1) or match.group(2)
                                if comment_text:
                                    line_num = content.count('\n', 0, match.start()) + 1
                                    comments.append({
                                        "file_name": os.path.relpath(file_path, self.repo_path),
                                        "line": line_num,
                                        "comment": comment_text.strip().replace('\n', ' ') # Flatten block comments
                                    })
                    except Exception:
                        pass
        return comments