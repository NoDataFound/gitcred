
```
▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄
███ ▄▄█▄ ▄█ ▄▄▀█ ▄▄▀██▄███ ▄▄▄█ ████▄ ▄██
███▄▄▀██ ██ ▀▀▄█ ▀▀ ██ ▄██ █▄▀█ ▄▄ ██ ███
███▄▄▄██▄██▄█▄▄█▄██▄█▄▄▄██▄▄▄▄█▄██▄██▄███
█▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀█
█░▄▀▀▄    ░█░▒█░   ▀█▀░    ▀█▀░    █▀▀▄ █
█░█░░█    ░█░▒█░   ░█░░    ░█░░    █▄▄█ █
█░░▀▀░    ░░▀▀▀░   ░▀░░    ░▀░░    ▀░░▀ █
█▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄█
██▀▄▀█▀▄▄▀█░▄▀▄░█░▄▀▄░█░▄▀▄░██▄██▄░▄█░▄▄█
██░█▀█░██░█░█▄█░█░█▄█░█░█▄█░██░▄██░██▄▄▀█
███▄███▄▄██▄███▄█▄███▄█▄███▄█▄▄▄██▄██▄▄▄█
▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀
                           gitCred v0.2.3
```
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-WebUI-brightgreen)](https://streamlit.io/)
[![Modular](https://img.shields.io/badge/Architecture-Modular-informational)](#)
[![Security First](https://img.shields.io/badge/Security-First-critical)](#)
[![Commit Proof](https://img.shields.io/badge/Proof-Commits-black)](#)
[![Version](https://img.shields.io/badge/GitCred-v0.2.3-orange)](#)

# GitCred - Straight outta commits.

GitCred analyzes a GitHub user's profile to generate a comprehensive skills and impact summary by inspecting original repositories. 

## **Resume Builder Use Cases**

* **Automated, Evidence-Based Resume Generation**

  * Instantly produces a skills matrix based on your actual code commits, not just buzzwords or self-assessment.
  * Surfaces *demonstrated* proficiency in frameworks, languages, and paradigms by parsing your real repositories and identifying libraries, patterns, and toolchains.
  * Generates impact summaries like "Led original React microservice migration" or "Contributed to three security-focused Python projects," providing verifiable proof for your claims.

* **Skill Gap Identification and Growth Tracking**

  * Highlights which languages and frameworks you have genuinely mastered versus those where your exposure is minimal or superficial.
  * Visualizes the evolution of your coding portfolio, letting you show tangible progression, such as "Moved from procedural scripting to OOP Python over two years."

* **Showcasing Breadth and Depth for Recruiters**

  * Produces a portfolio map showing not only what you know, but how you use it, such as "Built Flask APIs," "Unit-tested with pytest," "Deployed with Docker Compose."
  * Enables quick portfolio export for job applications. Recruiters get a real skills dossier, not just a laundry list of claims.

## **Analytical Use Cases**

* **Threat Hunter or CTI Validation**

  * Profile open source contributors for red team or blue team skillsets by examining their code artifacts, not just their self-promotion.
  * Quickly triage potential new hires, contributors, or threat actors by their actual technical work in public repositories.
  * Map contributors’ expertise to threat vectors. For example, "This candidate has written several kernel drivers and fuzzers, indicating low-level system exploit development experience."

* **Due Diligence and Mergers & Acquisitions Technical Vetting**

  * Assess the true technical depth of engineering teams before acquisition or partnership by scanning their public repo histories.
  * Identify star contributors or key experts whose work is crucial to business or project continuity.

* **Technical Risk Assessment**

  * Map out dependencies and stack choices across all repos. This is vital for identifying outdated libraries, deprecated tools, or supply chain risks lurking in an organization's codebase.
  * Generate an exposure matrix. For example, "Organization X has five production apps on Python 3.6 with unpatched Flask versions."

* **Red Team Social Engineering and Recon**

  * Target open source contributors with specific weaknesses or strengths. For example, "Their JavaScript is all vanilla; no modern framework experience," allowing for tailored engagement or lures.
  * Map the real skills graph of a developer community to plan infiltration or knowledge transfer operations.

## **Summary**

GitCred’s modular analysis pipeline validates skills, pinpoints strengths, exposes weaknesses, and helps you or your team make data-driven talent, security, or business decisions. For a hacker, threat hunter, or recruiter, it is like scanning a target’s badge and getting their *actual* clearance level, not just the one written in marker.

If you want receipts, GitCred brings receipts.

## Extensible Architecture

This tool is built with a highly modular architecture. The core logic in `main_analyzer.py` dispatches tasks to language-specific modules.

### Extending GitCred

**1. Adding a New Language Analyzer:**
-   Go to the `analyzers/` directory.
-   Copy `template_analyzer.py` to `newlanguage_analyzer.py`.
-   Implement the methods in your new class using tools specific to that language (e.g., linters, dependency parsers).
-   Open `main_analyzer.py` and register your new class in the `ANALYZER_MAP` dictionary.

**2. Adding a New Concept Map:**
-   Go to the `concept_maps/` directory.
-   Create a new file named `newlanguage_map.json`. The filename must match the lowercase language name from GitHub (e.g., `javascript_map.json`).
-   Populate the file with key-value pairs, where the key is the library name (as found by your analyzer) and the value is the concept to display.

## Setup

The installer script handles the complete setup.
```bash
chmod +x installer.sh
./installer.sh
```
# Usage
Navigate into the project directory (cd gitcred) and activate the virtual environment (source gitcredvenv/bin/activate).
Web UI:

```bash
streamlit run app.py
```

```bash
python cli.py <github_username>
```

