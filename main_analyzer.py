import os
import shutil
import git
import json
from github import Github, GithubException
import pandas as pd
from analyzers.python_analyzer import PythonAnalyzer

# This map is crucial for analyzing different Python-based repos
LANGUAGE_TO_ANALYZER_MAP = {
    "Python": PythonAnalyzer,
    "Jupyter Notebook": PythonAnalyzer
}

def get_user_and_repos(github_client, username):
    """Fetches the user object and a list of their original repositories."""
    try:
        user = github_client.get_user(username)
        repos = sorted(
            [r for r in user.get_repos() if not r.fork], 
            key=lambda r: r.stargazers_count, 
            reverse=True
        )
        return user, repos
    except GithubException as e:
        return None, f"Could not access user '{username}'. Rate limit? ({e.data.get('message', '')})"

def process_user_repos(user, repos_to_process):
    """Processes a specific list of repositories for a given user."""
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
    all_comments, tech_stats = [], []
    total_quality, total_security = {"violations": 0, "files_analyzed": 0}, []

    for repo in repos_to_process:
        language = repo.language
        analyzer_class = LANGUAGE_TO_ANALYZER_MAP.get(language)
        if not analyzer_class: continue

        try:
            repo_path = os.path.join(temp_dir, repo.name)
            
   
            # This will download the entire history, fixing the "bad object" error.
            git.Repo.clone_from(repo.clone_url, repo_path)
   
            
            tech_stats.extend(analyze_git_logs(repo_path))
            
            analyzer = analyzer_class(repo_path)
            
            deps = analyzer.get_dependencies()
            concept_map_path = "concept_maps/python_map.json"
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
            rc = analyzer.harvest_comments()
            for c in rc: c['repo_name'] = repo.name
            all_comments.extend(rc)

        except Exception as e:
            print(f"Warning: Could not analyze {repo.name}. Error: {e}"); continue
    
    shutil.rmtree(temp_dir)

    tech_analysis_created = False
    if tech_stats:
        pd.DataFrame(tech_stats).to_csv(os.path.join(output_dir, "technical_analysis.csv"), index=False)
        tech_analysis_created = True

    comments_log_created = False
    if all_comments:
        pd.DataFrame(all_comments)[['repo_name', 'file_name', 'line', 'comment']].to_csv(os.path.join(output_dir, "comments_log.csv"), index=False)
        comments_log_created = True

    return {"user": user, "repos": repos_to_process, "concepts": all_concepts, "quality": total_quality, "security": total_security,
            "output_dir": output_dir, "comment_count": len(all_comments), "tech_analysis_created": tech_analysis_created, "comments_log_created": comments_log_created}

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

def process_local_repo(repo_path):
    """Processes a single local repository."""
    if not os.path.isdir(repo_path): return {"error": f"Directory not found: {repo_path}"}
    repo_name = os.path.basename(os.path.normpath(repo_path))
    output_dir = os.path.join("analysis", repo_name)
    os.makedirs(output_dir, exist_ok=True)
    
    git_stats = analyze_git_logs(repo_path)
    pd.DataFrame(git_stats).to_csv(os.path.join(output_dir, "technical_analysis.csv"), index=False)
    
    if "error" in git_stats[0]: return {"error": git_stats[0]["error"]}
    
    analyzer = PythonAnalyzer(repo_path)
    comments = analyzer.harvest_comments()
    if comments: pd.DataFrame(comments)[['file_name', 'line', 'comment']].to_csv(os.path.join(output_dir, "comments_log.csv"), index=False)
    
    return {"repo_name": repo_name, "output_dir": output_dir, "git_stats": git_stats, "comment_count": len(comments)}
def process_local_repo(repo_path):
    """Processes a single local repository."""
    if not os.path.isdir(repo_path): return {"error": f"Directory not found: {repo_path}"}
    repo_name = os.path.basename(os.path.normpath(repo_path))
    output_dir = os.path.join("analysis", repo_name)
    os.makedirs(output_dir, exist_ok=True)
    
    git_stats = analyze_git_logs(repo_path) 
    pd.DataFrame(git_stats).to_csv(os.path.join(output_dir, "technical_analysis.csv"), index=False)
    
    # Simple check for error in the first record
    if "error" in git_stats[0]: return {"error": git_stats[0]["error"]}
    
    analyzer = PythonAnalyzer(repo_path)
    comments = analyzer.harvest_comments()
    if comments: pd.DataFrame(comments)[['file_name', 'line', 'comment']].to_csv(os.path.join(output_dir, "comments_log.csv"), index=False)
    
    # For local mode, the git_stats list itself is the primary data
    return {"repo_name": repo_name, "output_dir": output_dir, "git_stats": git_stats, "comment_count": len(comments)}
