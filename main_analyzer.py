import os
import shutil
import git
import json
import requests
import datetime
from github import Github, GithubException
import pandas as pd
import fade

# Import all your specified analyzers
from analyzers.python_analyzer import PythonAnalyzer
from analyzers.javascript_analyzer import JavaScriptAnalyzer
from analyzers.c_analyzer import CAnalyzer 
from analyzers.bash_analyzer import BashAnalyzer
from analyzers.vibe_analyzer import VibeAnalyzer

# This map is crucial for analyzing different repos
LANGUAGE_TO_ANALYZER_MAP = {
    "Python": PythonAnalyzer,
    "Jupyter Notebook": PythonAnalyzer,
    "JavaScript": JavaScriptAnalyzer,
    "TypeScript": JavaScriptAnalyzer,
    "C": CAnalyzer, 
    "C++": CAnalyzer, 
    "Shell": BashAnalyzer,
}

def fetch_contribution_graph(username, token):
    """
    Fetches the user's contribution graph data for the last year using the GraphQL API.
    Returns the calendar data or None on error.
    """
    if not token:
        return None # This feature requires authentication

    graphql_query = """
    query($userName:String!) {
      user(login: $userName){
        contributionsCollection {
          contributionCalendar {
            totalContributions
            weeks {
              contributionDays {
                contributionCount
                date
                weekday
              }
            }
          }
        }
      }
    }
    """
    headers = {"Authorization": f"bearer {token}"}
    try:
        response = requests.post(
            "https://api.github.com/graphql",
            json={"query": graphql_query, "variables": {"userName": username}},
            headers=headers
        )
        response.raise_for_status()
        data = response.json()
        if "errors" in data:
            return None
        return data["data"]["user"]["contributionsCollection"]["contributionCalendar"]
    except requests.exceptions.RequestException:
        return None

def render_ascii_graph(calendar_data):
    """
    Renders the contribution calendar data into a color-faded ASCII art graph.
    """
    if not calendar_data or not calendar_data["weeks"]:
        return "Could not retrieve contribution graph data."

    CHAR_MAP = {0: '·', 1: '░', 2: '▒', 3: '▓', 4: '█'}
    grid = [[' ' for _ in range(53)] for _ in range(7)]
    all_counts = [day['contributionCount'] for week in calendar_data["weeks"] for day in week['contributionDays']]
    if not all_counts or max(all_counts) == 0:
        return "No contributions found in the last year."
        
    max_contrib = max(all_counts)
    scale_factor = max_contrib / 4.0 if max_contrib > 0 else 1.0
    month_markers = {}
    current_month = -1

    for week_idx, week in enumerate(calendar_data["weeks"]):
        for day_data in week['contributionDays']:
            day_of_week = day_data['weekday']
            count = day_data['contributionCount']
            level = 0
            if count > 0:
                level = min(4, int(count / scale_factor) + 1)
            grid[day_of_week][week_idx] = CHAR_MAP[level]
            day_date = datetime.datetime.strptime(day_data['date'], '%Y-%m-%d').date()
            if day_date.month != current_month:
                current_month = day_date.month
                if week_idx > 0:
                    month_markers[week_idx] = day_date.strftime("%b")

    header = [' ' * 4] * 53
    for week_idx, month_abbr in month_markers.items():
        header[week_idx] = month_abbr.ljust(4)
    output_string = [" " * 5 + "".join(header).rstrip()]
    day_names = ["Sun ", "Mon ", "Tue ", "Wed ", "Thu ", "Fri ", "Sat "]
    for day_of_week in range(7):
        row_str = day_names[day_of_week] + " ".join(grid[day_of_week]).rstrip()
        output_string.append(row_str)
        
    #
    faded_graph = fade.purplepink("\n".join(output_string))
    
    return faded_graph

def get_user_and_repos(github_client, username):

    try:
        user = github_client.get_user(username)
        all_repos = list(user.get_repos())
        total_repo_count = len(all_repos)
        original_repos = sorted(
            [r for r in all_repos if not r.fork],
            key=lambda r: r.stargazers_count,
            reverse=True
        )
        return user, original_repos, total_repo_count
    except GithubException as e:
        return None, f"Could not access user '{username}'. Rate limit? ({e.data.get('message', '')})", None

def process_user_repos(user, repos_to_process, vibe_check_enabled=False):
    """
    Processes a specific list of repositories for a given user, with optional vibe check.
    """
    if not repos_to_process:
        return {"error": "No repositories were selected for analysis."}
    
    username = user.login
    output_dir = os.path.join("analysis", username)
    os.makedirs(output_dir, exist_ok=True)
    temp_dir = "temp_repos"
    if os.path.exists(temp_dir): shutil.rmtree(temp_dir)
    os.makedirs(temp_dir)

    all_concepts = {}
    proficiency_order = {"basic": 1, "intermediate": 2, "advanced": 3}
    all_comments, tech_stats, all_vibe_findings = [], [], []
    total_quality, total_security = {"violations": 0, "files_analyzed": 0}, []

    for repo in repos_to_process:
        language = repo.language
        analyzer_class = LANGUAGE_TO_ANALYZER_MAP.get(language)
        if not analyzer_class: continue

        try:
            repo_path = os.path.join(temp_dir, repo.name)
            git.Repo.clone_from(repo.clone_url, repo_path)
            
            tech_stats.extend(analyze_git_logs(repo_path))
            
            excluded_lines = set()
            if vibe_check_enabled:
                vibe_analyzer = VibeAnalyzer(repo_path)
                findings, excluded_lines = vibe_analyzer.analyze()
                for finding in findings:
                    finding['repo_name'] = repo.name
                all_vibe_findings.extend(findings)
            
            analyzer = analyzer_class(repo_path, excluded_lines=excluded_lines)
            
            deps = analyzer.get_dependencies()
            concept_map_path = f"concept_maps/{language.lower()}_map.json"
            if os.path.exists(concept_map_path):
                with open(concept_map_path, 'r') as f:
                    concept_map = json.load(f)
                
                for dep in deps:
                    for category, levels in concept_map.items():
                        for level_name, packages in levels.items():
                            if dep in packages:
                                current_level_value = proficiency_order.get(all_concepts.get(category), 0)
                                new_level_value = proficiency_order.get(level_name, 0)
                                if new_level_value > current_level_value:
                                    all_concepts[category] = level_name
            
            q = analyzer.analyze_quality()
            total_quality["violations"] += q.get("violations", 0)
            total_quality["files_analyzed"] += q.get("files_analyzed", 0)
            total_security.extend(analyzer.analyze_security())
            all_comments.extend(analyzer.harvest_comments())

        except Exception as e:
            print(f"Warning: Could not analyze {repo.name}. Error: {e}"); continue
    
    shutil.rmtree(temp_dir)

    if vibe_check_enabled and all_vibe_findings:
        df_vibe = pd.DataFrame(all_vibe_findings)
        df_vibe[['repo_name', 'file_name', 'line_number', 'line_content', 'reason']].to_csv(os.path.join(output_dir, "vibe_code.csv"), index=False)

    tech_analysis_created = False
    if tech_stats:
        pd.DataFrame(tech_stats).to_csv(os.path.join(output_dir, "technical_analysis.csv"), index=False)
        tech_analysis_created = True

    comments_log_created = False
    if all_comments:
        pd.DataFrame(all_comments).to_csv(os.path.join(output_dir, "comments_log.csv"), index=False)
        comments_log_created = True

    return {
        "user": user, "repos": repos_to_process, "concepts": all_concepts, "quality": total_quality, "security": total_security,
        "output_dir": output_dir, "comment_count": len(all_comments), "tech_analysis_created": tech_analysis_created, 
        "comments_log_created": comments_log_created, "vibe_finding_count": len(all_vibe_findings)
    }

def analyze_git_logs(repo_path):
    """
    Parses git logs to extract a detailed, commit-by-commit record.
    """
    try:
        repo = git.Repo(repo_path)
        commits_data = []
        for commit in repo.iter_commits():
            commits_data.append({
                "repo_name": os.path.basename(repo_path), "commit_hash": commit.hexsha, "author_name": commit.author.name,
                "author_email": commit.author.email, "commit_date": commit.committed_datetime.strftime("%Y-%m-%d %H:%M:%S"),
                "commit_message": commit.message.strip().replace('\n', ' | '), "files_changed": len(commit.stats.files),
                "lines_added": commit.stats.total.get('insertions', 0), "lines_deleted": commit.stats.total.get('deletions', 0),
            })
        return commits_data
    except Exception as e:
        return [{"repo_name": os.path.basename(repo_path), "error": f"Could not analyze Git logs: {e}"}]

def process_local_repo(repo_path, vibe_check_enabled=False):
    """Processes a single local repository, with optional vibe check."""
    if not os.path.isdir(repo_path): return {"error": f"Directory not found: {repo_path}"}
    repo_name = os.path.basename(os.path.normpath(repo_path))
    output_dir = os.path.join("analysis", repo_name)
    os.makedirs(output_dir, exist_ok=True)
    
    excluded_lines, vibe_findings = set(), []
    if vibe_check_enabled:
        vibe_analyzer = VibeAnalyzer(repo_path)
        vibe_findings, excluded_lines = vibe_analyzer.analyze()
        if vibe_findings:
            df_vibe = pd.DataFrame(vibe_findings); df_vibe['repo_name'] = repo_name
            df_vibe[['repo_name', 'file_name', 'line_number', 'line_content', 'reason']].to_csv(os.path.join(output_dir, "vibe_code.csv"), index=False)
            
    git_stats = analyze_git_logs(repo_path)
    if "error" in git_stats[0]: return {"error": git_stats[0]["error"]}
    pd.DataFrame(git_stats).to_csv(os.path.join(output_dir, "technical_analysis.csv"), index=False)
    
    all_concepts = {}; proficiency_order = {"basic": 1, "intermediate": 2, "advanced": 3}
    all_comments = []; total_quality = {"violations": 0, "files_analyzed": 0}; total_security = []
    
    # Assume Python for local analysis
    language = "Python"
    analyzer_class = LANGUAGE_TO_ANALYZER_MAP.get(language)
    
    if analyzer_class:
        analyzer = analyzer_class(repo_path, excluded_lines=excluded_lines)
        all_comments = analyzer.harvest_comments()
        if all_comments:
            pd.DataFrame(all_comments).to_csv(os.path.join(output_dir, "comments_log.csv"), index=False)
        
        q = analyzer.analyze_quality(); total_quality["violations"] += q.get("violations", 0); total_quality["files_analyzed"] += q.get("files_analyzed", 0)
        total_security.extend(analyzer.analyze_security())
        
        deps = analyzer.get_dependencies()
        concept_map_path = f"concept_maps/{language.lower()}_map.json"
        if os.path.exists(concept_map_path):
            with open(concept_map_path, 'r') as f:
                concept_map = json.load(f)
            for dep in deps:
                for category, levels in concept_map.items():
                    for level_name, packages in levels.items():
                        if dep in packages:
                            current_level_value = proficiency_order.get(all_concepts.get(category), 0)
                            new_level_value = proficiency_order.get(level_name, 0)
                            if new_level_value > current_level_value:
                                all_concepts[category] = level_name
    
    return {
        "repo_name": repo_name, "output_dir": output_dir, "git_stats": git_stats, "concepts": all_concepts,
        "quality": total_quality, "security": total_security, "comment_count": len(all_comments), 
        "vibe_finding_count": len(vibe_findings)
    }

def analyze_git_logs(repo_path):
    """
    Parses git logs to extract a detailed, commit-by-commit record.
    Returns a list of dictionaries, one for each commit.
    """
    try:
        repo = git.Repo(repo_path)
        commits_data = []
        for commit in repo.iter_commits():
            commits_data.append({
                "repo_name": os.path.basename(repo_path),
                "commit_hash": commit.hexsha,
                "author_name": commit.author.name,
                "author_email": commit.author.email,
                "commit_date": commit.committed_datetime.strftime("%Y-%m-%d %H:%M:%S"),
                "commit_message": commit.message.strip().replace('\n', ' | '),
                "files_changed": len(commit.stats.files),
                "lines_added": commit.stats.total.get('insertions', 0),
                "lines_deleted": commit.stats.total.get('deletions', 0),
            })
        return commits_data
    except git.InvalidGitRepositoryError:
        return [{"repo_name": os.path.basename(repo_path), "error": "Not a valid Git repository."}]
    except Exception as e:
        return [{"repo_name": os.path.basename(repo_path), "error": f"Could not analyze Git logs: {e}"}]

def process_local_repo(repo_path, vibe_check_enabled=False): # <-- NEW FLAG ADDED
    if not os.path.isdir(repo_path): return {"error": f"Directory not found: {repo_path}"}
    repo_name = os.path.basename(os.path.normpath(repo_path))
    output_dir = os.path.join("analysis", repo_name)
    os.makedirs(output_dir, exist_ok=True)
    
    excluded_lines = set()
    vibe_findings = []
    if vibe_check_enabled:
        vibe_analyzer = VibeAnalyzer(repo_path)
        vibe_findings, excluded_lines = vibe_analyzer.analyze()
        if vibe_findings:
            df_vibe = pd.DataFrame(vibe_findings)
            df_vibe['repo_name'] = repo_name # Add repo context
            df_vibe[['repo_name', 'file_name', 'line_number', 'line_content', 'reason']].to_csv(os.path.join(output_dir, "vibe_code.csv"), index=False)
            
    git_stats = analyze_git_logs(repo_path)
    pd.DataFrame(git_stats).to_csv(os.path.join(output_dir, "technical_analysis.csv"), index=False)
    
    if "error" in git_stats[0]: return {"error": git_stats[0]["error"]}
    
    analyzer = PythonAnalyzer(repo_path, excluded_lines=excluded_lines)
    comments = analyzer.harvest_comments()
    if comments: pd.DataFrame(comments).to_csv(os.path.join(output_dir, "comments_log.csv"), index=False)
    
    return {
        "repo_name": repo_name, "output_dir": output_dir, "git_stats": git_stats, 
        "comment_count": len(comments), "vibe_finding_count": len(vibe_findings)
    }