import os
import sys
import argparse
import pandas as pd
import fade

# --- WARNING SUPPRESSION MUST GO FIRST ---
import warnings
from urllib3.exceptions import NotOpenSSLWarning
warnings.filterwarnings("ignore", category=NotOpenSSLWarning)
# --- END OF FIX ---

from dotenv import load_dotenv
from github import Github
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from simple_term_menu import TerminalMenu
# Import all necessary functions, including the new graph ones
from main_analyzer import get_user_and_repos, process_user_repos, process_local_repo, fetch_contribution_graph, render_ascii_graph

def display_online_results(console, results, ascii_graph=None):
    """
    This function displays the comprehensive summary report.
    """
    user, repos = results["user"], results["repos"]
    concepts = results.get("concepts", {})
    
    console.print(Panel(f"[bold green]Analysis for {user.name or user.login} complete![/]", title="Overall Summary", border_style="green", subtitle="Straight outta commits."))
    if ascii_graph:
        console.print("\n[bold green]Contribution Graph (Last Year)[/bold green]")
        print(ascii_graph) 
        console.print()
    repo_details = [{"name": r.name, "stars": r.stargazers_count, "forks": r.forks_count, "language": r.language or "N/A"} for r in repos]
    impact_text = Text(f"Analyzed Repos: {len(repos)} | ", style="bold")
    impact_text.append(f"Total Stars (in selection): {sum(r['stars'] for r in repo_details)} ★ | ", style="bold yellow")
    impact_text.append(f"Total Forks (in selection): {sum(r['forks'] for r in repo_details)} 🍴", style="bold blue")
    console.print(Panel(impact_text, title="[bold cyan]Impact Summary[/]", border_style="cyan"))

    if concepts:
        levels = {"basic": [], "intermediate": [], "advanced": []}
        for concept, level in concepts.items():
            if level in levels:
                levels[level].append(concept)
        
        skill_text = ""
        if levels["basic"]:
            skill_text += "[bold][+] Basic[/bold]\n" + "\n".join([f"  - {c}" for c in sorted(levels["basic"])]) + "\n"
        if levels["intermediate"]:
            skill_text += "[bold][+] Intermediate[/bold]\n" + "\n".join([f"  - {c}" for c in sorted(levels["intermediate"])]) + "\n"
        if levels["advanced"]:
            skill_text += "[bold][+] Advanced[/bold]\n" + "\n".join([f"  - {c}" for c in sorted(levels["advanced"])])
        
        if skill_text:
            console.print(Panel(skill_text.strip(), title="[bold magenta]Inferred Skillset / Concepts[/]", border_style="magenta"))

    table_repos = Table(title="Top 10 Repositories by Stars (in selection)")
    table_repos.add_column("Name", style="cyan"); table_repos.add_column("Language", style="green"); table_repos.add_column("Stars ★", style="yellow"); table_repos.add_column("Forks 🍴", style="blue")
    df_repos = pd.DataFrame(repo_details).sort_values(by="stars", ascending=False).head(10)
    for _, row in df_repos.iterrows():
        table_repos.add_row(row['name'], row['language'], str(row['stars']), str(row['forks']))
    console.print(table_repos)
    
    quality, security = results["quality"], results["security"]
    files_analyzed = quality.get("files_analyzed", 0)
    if files_analyzed > 0:
        avg_violations = quality.get("violations", 0) / files_analyzed
        high_issues = sum(1 for s in security if s.get('issue_severity') == 'HIGH')
        quality_text = f"PEP Compliance (violations/file): [bold]{avg_violations:.2f}[/bold]\nHigh-Severity Security Issues: [bold red]{high_issues}[/bold red]"
        console.print(Panel(quality_text, title="[bold yellow]Python Code Quality[/bold yellow]", border_style="yellow"))

    summary_data = []
    if concepts:
        for category, level in concepts.items():
            summary_data.append({"Category": "Skillset", "Item": category, "Level": level, "Value": ""})
    
    summary_data.append({"Category": "Impact", "Item": "Analyzed Repositories", "Level": "", "Value": len(repos)})
    summary_data.append({"Category": "Impact", "Item": "Total Stars", "Level": "", "Value": sum(r['stars'] for r in repo_details)})
    summary_data.append({"Category": "Impact", "Item": "Total Forks", "Level": "", "Value": sum(r['forks'] for r in repo_details)})
    if files_analyzed > 0:
        avg_violations_val = quality.get('violations', 0) / files_analyzed
        summary_data.append({"Category": "Quality", "Item": "Avg PEP8 Violations", "Level": "", "Value": f"{avg_violations_val:.2f}"})
        summary_data.append({"Category": "Quality", "Item": "High-Severity Security Issues", "Level": "", "Value": sum(1 for s in security if s.get('issue_severity') == 'HIGH')})

    summary_df = pd.DataFrame(summary_data)
    summary_path = os.path.join(results['output_dir'], "summary.csv")
    summary_df.to_csv(summary_path, index=False)
    
    saved_files_messages = []
    saved_files_messages.append(f"[green]Summary saved to:[/][bold cyan] {summary_path}[/]")
    
    if results.get("tech_analysis_created"):
        saved_files_messages.append(f"[green]Technical stats saved to:[/][bold cyan] {os.path.join(results['output_dir'], 'technical_analysis.csv')}[/]")
    if results.get("comments_log_created"):
        saved_files_messages.append(f"[green]Comments log saved to:[/][bold cyan] {os.path.join(results['output_dir'], 'comments_log.csv')}[/]")
    
    if results.get("vibe_finding_count", 0) > 0:
        saved_files_messages.append(f"[yellow]Vibe Check log saved to:[/][bold yellow] {os.path.join(results['output_dir'], 'vibe_code.csv')}[/]")
        saved_files_messages.append("[dim yellow]   └─ Subsequent analyses excluded these flagged lines.[/dim yellow]")

    console.print(Panel("\n".join(saved_files_messages), title="Saved Files", border_style="green"))


def main():
    try:
        with open("banner.txt", "r") as f: print(fade.greenblue(f.read()))
    except FileNotFoundError: print("\n--- GitCred v0.2.3 ---\n")
    
    parser = argparse.ArgumentParser(description="GitCred CLI")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("-u", "--users", nargs='+', help="One or more GitHub usernames.")
    group.add_argument("-f", "--file", help="Path to a file with one username per line.")
    group.add_argument("-l", "--local", help="Path to a local Git repository directory.")
    parser.add_argument("--vibe", action="store_true", help="Enable the AI Vibe Check & Exclusion filter during analysis.")
    args = parser.parse_args()
    console = Console()

    if args.local:
        status_text = f"[bold green]Analyzing local repo at {args.local}"
        if args.vibe: status_text += " with Vibe Check enabled..."
        else: status_text += "..."
        
        with console.status(status_text):
            results = process_local_repo(args.local, vibe_check_enabled=args.vibe)
        
        if "error" in results: console.print(f"[bold red]Error: {results['error']}[/]"); sys.exit(1)
        
        st = results['git_stats'][0] 
        console.print(Panel(f"Commits: {len(results['git_stats'])}, First Commit: {st['commit_date']}", title="Git Log Stats"))
        console.print(f"[green]All output saved to[/] [bold cyan]{results['output_dir']}[/]")
        if results.get("vibe_finding_count", 0) > 0:
            console.print(f"[yellow]Vibe Check found and logged {results['vibe_finding_count']} indicators.[/]")
    else:
        usernames = args.users if args.users else []
        if args.file:
            try:
                with open(args.file, 'r') as f:
                    usernames.extend([line.strip() for line in f if line.strip() and not line.strip().startswith('#')])
            except FileNotFoundError: console.print(f"[bold red]Error: File not found at '{args.file}'[/]"); sys.exit(1)
        
        load_dotenv(); GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
        if GITHUB_TOKEN: g = Github(GITHUB_TOKEN)
        else: console.print("[bold yellow]Warning: No API Token found. Contribution graph will be disabled.[/]"); g = Github()
        
        for username in set(usernames):
            console.print(Panel(f"Fetching data for [bold cyan]{username}[/]", border_style="blue"))
            user, repos, total_repo_count = get_user_and_repos(g, username)
            
            ascii_graph = None
            if GITHUB_TOKEN:
                with console.status("[green]Fetching contribution graph...[/]"):
                    graph_data = fetch_contribution_graph(username, GITHUB_TOKEN)
                    if graph_data:
                        ascii_graph = render_ascii_graph(graph_data)
            
            if user is None: 
                console.print(f"[bold red]{repos}[/]"); continue
            
            console.print(f"User has [bold]{total_repo_count}[/bold] total repositories. Found [bold green]{len(repos)}[/bold green] original repositories available for analysis.")
            
            if not repos: console.print(f"[yellow]User '{username}' has no original public repositories.[/]"); continue
            
            menu_entries = [f"[a] SELECT ALL ({len(repos)} repositories)"]
            menu_entries.extend([f"[{r.stargazers_count} ★] {r.name} ({r.language or 'N/A'})" for r in repos])
            terminal_menu = TerminalMenu(menu_entries, title=f"Select repositories for {username} to analyze.", multi_select=True, show_multi_select_hint=True)
            selected_indices = terminal_menu.show()
            if selected_indices is None: console.print("[yellow]No selection made. Skipping user.[/]"); continue
            repos_to_process = [repos[i-1] for i in selected_indices if i > 0] if 0 not in selected_indices else repos
            if not repos_to_process: console.print("[yellow]No repositories selected. Skipping user.[/]"); continue

            status_text = f"[bold green]Processing {len(repos_to_process)} selected repos for {username}"
            if args.vibe:
                status_text += " with Vibe Check enabled..."
            else:
                status_text += "..."

            with console.status(status_text):
                results = process_user_repos(user, repos_to_process, vibe_check_enabled=args.vibe)
            
            if "error" in results: console.print(f"[bold red]Error: {results['error']}[/]"); continue
            display_online_results(console, results, ascii_graph=ascii_graph)
            #console.print("-" * 50)

if __name__ == "__main__":
    main()