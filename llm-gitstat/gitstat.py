import sys
import os
import time
import argparse
import logging


from common.analyzer import do_update, generate_output
from common.tool_config import ToolConfig

os.environ["LC_ALL"] = "C"

exectime_internal = 0.0
exectime_external = 0.0
time_start = time.time()


def parseOpts(opts):
    config = ToolConfig(cwd=os.getcwd())
    if opts.update_git:
        config.set_update_git()
    if opts.update_github:
        config.set_update_github()
    if opts.update_all:
        config.set_update_all()
    if opts.update: 
        config.set_update_mode()
    if opts.cache_folder:
        config.set_cache_folder(opts.cache_folder)
    if opts.repos_folder:
        config.set_repos_folder(opts.repos_folder)
    if opts.months_to_analyze:
        try:
            config.set_months_to_analyze(int(opts.months_to_analyze))
        except ValueError:
            print(f"Invalid months-to-analyze value: {opts.months_to_analyze}")
            return None
    if opts.months_offset:
        try:
            config.set_months_offset(int(opts.months_offset))
        except ValueError:
            print(f"Invalid months-offset value: {opts.months_offset}")
            return None
    if opts.analyze_performance:
        try:
            config.set_analyze_performance(int(opts.analyze_performance))
        except ValueError:
            print(f"Invalid analyze-performance value: {opts.analyze_performance}")
            return None
    if opts.github_url:
        config.set_url(opts.github_url)
    if opts.local_repo:
        config.set_local_repo(opts.local_repo)
    if opts.excel_file:
        config.set_excel_file(opts.excel_file)
    if opts.text_file:
        config.set_text_file(opts.text_file)
    if opts.output: 
        config.set_output(opts.output)
    if opts.git_download_only:
        config.set_git_download_only(opts.git_download_only)
    if opts.skip_existing: 
        config.set_skip_existing(opts.skip_existing)
    if opts.update_github_anon_only:
        config.set_update_github_anon_only(opts.update_github_anon_only)

    return config

def check_github_token(config):
    """Check if GITHUB_TOKEN is set when GitHub operations are requested"""
    if (config.update_github or config.update_all) and not os.environ.get("GITHUB_TOKEN"):
        logging.error("\033[91mWARNING: GITHUB_TOKEN environment variable is not set!\033[0m")
        logging.error("GitHub API operations will be severely rate-limited.")
        logging.error("Please set the GITHUB_TOKEN environment variable:")
        logging.error("  export GITHUB_TOKEN=\"your_github_token\"")
        logging.error("\nContinuing without token, but GitHub operations may fail...\n")

def main():
    parser = argparse.ArgumentParser(description='Git Analyzer Tool')

    g = parser.add_argument_group('Generic options')
    g.add_argument('-v', '--verbose', action='count', help='enable verbose mode (use -vv for max verbosity)')
    g.add_argument('-l', '--logfile', action='store', help='log filename')

    g = parser.add_argument_group('Fetch options')
    g.add_argument('--cache-folder', action='store', default="_cache", help='cache folder')
    g.add_argument('--repos-folder', action='store', default="_repos", help='repos folder')
    g.add_argument('--update-all', action='store_true', help='update cache')
    g.add_argument('--update-git', action='store_true', help='update cache with git-based info only')
    g.add_argument('--git-download-only', action='store_true', help='clone repos only')
    g.add_argument('--skip-existing', action='store_true', help='skip colecting from github if exists in the cache')
    g.add_argument('--update-github', action='store_true', help='update cache with github-based info only')
    g.add_argument('--update-github-anon-only', action='store_true', help='update cache with github-based info about anon users only')

    g = parser.add_argument_group('Analyzer options')
    g.add_argument('-u', '--update', action='store_true', help='run in update mode - downloads all GitHub information and fetches repos')

    

    g = parser.add_argument_group('Stats options')
    g.add_argument('-m', '--months-to-analyze', action='store', default="12", help='the number of months to analyze (stats mode only)')
    g.add_argument('-o', '--months-offset', action='store', default="0", help='how many months back to start the analysis (e.g., 12 means start from a year ago)')
    g.add_argument('-a', '--analyze-performance', action='store', default="0", help='analyze performance over time for the specified number of months')
    g.add_argument('-E', '--extended-stats', action='store_true', help='collect extended statistics including tags and revisions')

    g = parser.add_argument_group('Input options')
    g.add_argument('-g', '--github-url', action='store', help='git repo URL to analyze')
    g.add_argument('-L', '--local-repo', action='store', help='local repository name to analyze (skips GitHub operations)')
    g.add_argument('-e', '--excel-file', action='store', help='Update excel file')
    g.add_argument('-f', '--text-file', action='store', help='Update excel file')

    g = parser.add_argument_group('Output options')
    g.add_argument('--output', action='store', default='console', help='Output options: excel, console, etc')

    opts = parser.parse_args()

    if opts.verbose is None:
        level = logging.WARNING
    else:
        level = logging.DEBUG if opts.verbose > 1 else logging.INFO
    if opts.logfile != "":
        logging.basicConfig(level=level, filename=opts.logfile, format="%(message)s")
    else:
        logging.basicConfig(level=level, format="%(asctime)s - %(levelname)6s - %(message)s")

    config = parseOpts(opts)
    # Set extended_stats flag from command line argument
    config.extended_stats = opts.extended_stats
    
    time_start = time.time()
    if opts.update:
        # In update mode, always set update_all to true if no specific update flags are set
        if not (config.update_git or config.update_github):
            config.set_update_all()
        # Check if GITHUB_TOKEN is set when GitHub operations are requested
        check_github_token(config)
        do_update(config)
    # Stats mode - use months_to_analyze for filtering
    generate_output(config)

    time_end = time.time()
    logging.info(f"Execution time: {time_end - time_start:.2f} seconds")

if __name__ == "__main__":
    main()
