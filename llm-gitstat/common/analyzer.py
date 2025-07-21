import os
import logging
import subprocess
import shutil
from time import sleep
import urllib.parse
import pickle
import zlib

from common.git_data_collector import GitDataCollector
from common.analyze_excel import extract_text_urls, extract_urls, generate_exec_report
from common.githib_gateway import github_get_repo, github_get_repo_contributors, github_get_user, github_get_user_orgs
from common.stat_contributors import generate_contributors_report
from common.stat_authors import analyze_author_contributions
from common.git_performance_analysis import analyze_performance_over_time
from common.tool_config import CollectorConfig
from common.repo import RepoInformation
from common.utils import getpipeoutput, parse_url

import threading


CACHE_GIT_EXT= "git"
CACHE_GITHUB_EXT= "github"

GIT_THREAD_LIMIT = 1
GITHUB_THREAD_LIMIT = 1


GITHUB_SKIP_LIST = ["https://github.com/torvalds/linux"]
GIT_SKIP_LIST = ["https://github.com/chromium/chromium",
                 "https://github.com/torvalds/linux"]

def load_from_cache(cache_folder, cache_file, ext):
    cache_file_path = os.path.join(cache_folder, cache_file)
    cache_file_path = f"{cache_file_path}.{ext}"
    if not os.path.exists(cache_file_path):
        logging.warning(f"Cache file {cache_file_path} does not exist.")
        return None

    cache = None
    # Load the pickled object
    with open(cache_file_path, "rb") as f:
        try:
            cache = pickle.loads(zlib.decompress(f.read()))
        except:
            # temporary hack to upgrade non-compressed caches
            f.seek(0)
            cache = pickle.load(f)    

    return cache

def save_to_cache(cache_folder, cache_file, data, ext):
    if not os.path.exists(cache_folder):
        os.makedirs(cache_folder)
    cache_file_path = os.path.join(cache_folder, cache_file)
    cache_file_path = f"{cache_file_path}.{ext}"
    logging.debug(f"Saving data to cache: {cache_file_path}")
    with open(cache_file_path, "wb") as f:
        bdata = zlib.compress(pickle.dumps(data))
        f.write(bdata)


def is_git_repo(directory):
    try:
        subprocess.check_call(['git', 'status'], cwd=directory)
        return True
    except Exception as e:
        return False

def clone_git_repo(repo_url, local_folder):
    valid_git_repo = is_git_repo(local_folder)
    logging.debug(f"clone_git_repo: {repo_url} to {local_folder} (valid git repo: {valid_git_repo}), cwd: {os.getcwd()}")
    if os.path.exists(local_folder) and not valid_git_repo:
        logging.warning(f"{local_folder} exists but is not a git repo. Removing...")
        shutil.rmtree(local_folder)
    
    if not os.path.exists(local_folder):
        os.makedirs(local_folder)
        logging.debug(f"Cloning repo: {repo_url} to {local_folder}, cwd: {os.getcwd()}")
        my_env = {"export GIT_ASKPASS": "echo", "SSH_ASKPASS": "echo"}
        #subprocess.call(['git', 'clone', repo_url, local_folder], env=my_env)
        result = subprocess.run(['git', 'clone', repo_url, local_folder], env=my_env, capture_output=True, text=True)  # Capture output as text

        if result.returncode == 0:
            return True
        return False
        
    else:
        prevdir = os.getcwd()
        os.chdir(local_folder)
        getpipeoutput(["git reset --hard"])
        getpipeoutput(["git pull --rebase"])
        os.chdir(prevdir)
    return True


def create_collectors_config(tool_config):
    conf = CollectorConfig()
    
    # Calculate start date based on months_to_analyze and months_offset
    conf.calculate_start_date(tool_config.months_to_analyze, tool_config.months_offset)
    
    # Pass extended_stats flag to collector config
    if hasattr(tool_config, 'extended_stats'):
        conf.extended_stats = tool_config.extended_stats
    else:
        conf.extended_stats = False
    
    return conf

def upgrade_cache(config, url):
    logging.debug(f"Upgrade cache {url}: {config.dump()}")
    repo_name, owner = parse_url(url)

    conf = create_collectors_config(config)
    git_data = GitDataCollector(conf)

    repo = RepoInformation(owner, repo_name, url)

    #upgrade from .bin format
    data_old = load_from_cache(config.cache_folder, repo.id, "bin")
    if data_old is not None:
        save_to_cache(config.cache_folder, repo.id, data_old.stat, CACHE_GIT_EXT)
        data_old.stat = None
        save_to_cache(config.cache_folder, repo.id, data_old, CACHE_GITHUB_EXT)


def get_github_info(repo, config):
    data_loaded_from_cache = False
    github_data_from_cache = load_from_cache(config.cache_folder, repo.id, CACHE_GITHUB_EXT)
    data_loaded_from_cache = github_data_from_cache is not None
    logging.info(f"GitHib data for {repo.id} was loaded from cache ({config.cache_folder}/{repo.id}.{CACHE_GITHUB_EXT}): {data_loaded_from_cache}")
    return github_data_from_cache



def update_github_info(url, config):
    try:
        repo_name, owner = parse_url(url)
        repo = RepoInformation(owner, repo_name, url)
    
        exists_in_cache = False
        if config.skip_existing:
            logging.info(f"Getting GitHub data from cache for: {repo.id}")
            cache = get_github_info(repo, config)
            exists_in_cache = cache is not None
            if exists_in_cache and not config.update_github_anon_only:
                logging.info(f"Skipping GitHub update for {repo.id} as it exists in the cache and no need to update anon users.")
                return
            repo = cache
        
        info = github_get_repo(repo.owner, repo.name)
        if info is None: 
            logging.warning(f"Repo not found: {repo.id}")
            return
        repo.populate_info(info)
        contributors = github_get_repo_contributors(repo.owner, repo.name)

        
        repo.populate_contributors(contributors, config.update_github_anon_only)
        if not exists_in_cache and not config.skip_existing:
            for login in repo.contributors:
                contr = repo.contributors[login]
                if contr.type == "User":
                    user = github_get_user(login)
                    orgs = github_get_user_orgs(login)
                    repo.populate_user_info(user, orgs)

        logging.info(f"Saving GitHub data for {repo.id} into the cache: {config.cache_folder}/{repo.id}.{CACHE_GITHUB_EXT}")
        repo.stat = None
        save_to_cache(config.cache_folder, repo.id, repo, CACHE_GITHUB_EXT)
    except Exception as e: 
        logging.error(f"Failed to update GitHub info for {url}: {e}")


def get_git_info(repo_id, config):
    logging.info(f"Getting GIT data from cache for: {repo_id}")
    git_data_from_cache = load_from_cache(config.cache_folder, repo_id, CACHE_GIT_EXT)
    data_loaded_from_cache = git_data_from_cache is not None
    logging.info(f"GIT data for {repo_id} in cache ({config.cache_folder}/{repo_id}.{CACHE_GIT_EXT}): {data_loaded_from_cache}")
    return git_data_from_cache


def update_git_info(repo_url, config):
    try:
        repo_name, owner = parse_url(repo_url)
        repo = RepoInformation(owner, repo_name, repo_url)
        conf = create_collectors_config(config)
        git_data = GitDataCollector(conf)

        exists_in_cache = False
        if config.skip_existing:
            logging.info(f"Getting Git data from cache for: {repo.id}")
            cache = get_git_info(repo.id, config)
            exists_in_cache = cache is not None
            if exists_in_cache :
                logging.info(f"Skipping Git update for {repo.id} as it exists in the cache.")
                return

        logging.info(f"Getting GIT data for: {repo.id}")
        
        temp_folder_name = os.path.join(config.repos_folder, repo.id)
        logging.info(f"Updating git repo for {repo.id} in {temp_folder_name}")
        
        clone_done = False
        # Call the function with the directory path
        try:
            clone_done = clone_git_repo(repo_url, temp_folder_name)
        except Exception as e:
            logging.error(f"Failed to clone repo: {e}")
            return

        if not clone_done: 
            logging.error(f"Failed to clone repo: {repo_url}")
            return

        if config.git_download_only:
            logging.info(f"Git download only flag is set. Skipping data collection for {repo.id}.")
            return

        prevdir = os.getcwd()
        os.chdir(temp_folder_name)
        logging.debug(f"Collecting data from {repo.id}...")
        try:
            git_data.collect()
        except Exception as e:
            logging.error(f"Failed to collect data from {repo.id}: {e}")
        os.chdir(prevdir)

        try:
            git_data.refine()
        except Exception as e:
            logging.error(f"Failed to refine data from {repo.id}: {e}")
        
        logging.info(f"Saving GIT data for {repo.id} into the cache: {config.cache_folder}/{repo.id}.{CACHE_GIT_EXT}")
        save_to_cache(config.cache_folder, repo.id, git_data, CACHE_GIT_EXT)
        logging.info(f"DONE getting GIT data for: {repo.id}")
    except Exception as e:
        logging.error(f"Failed to update GIT info for {repo_url}: {e}")  


def do_update(config):
    logging.info("Starting data update...")
    urls = []
    if config.url:
        urls.append(config.url)
    if config.excel_file:
        urls.extend(extract_urls(config.excel_file))
    if config.text_file:
        urls.extend(extract_text_urls(config.text_file))
    
    logging.info(f"Starting data update (urls count: {len(urls)})...")
    
    #for url in urls:
    #    upgrade_cache(config, url)
    #return
    thread_git = threading.Thread(target=do_update_git, args=(urls, config))
    thread_github = threading.Thread(target=do_update_github, args=(urls, config))
    thread_git.start()
    thread_github.start()
    thread_git.join()
    thread_github.join()
    
    logging.info("Data update completed.")


def do_update_git(urls, config):
    threads = []
        
    for repo_url in urls:
        if repo_url in GIT_SKIP_LIST:
            logging.warning(f"Skipping URL: {repo_url}")
            continue
        logging.info(f"GIT: Processing URL: {repo_url}")
        if len(threads) < GIT_THREAD_LIMIT and config.update_git:
            logging.info(f"Starting thread for GIT update: {repo_url}")
            t2 = threading.Thread(target=update_git_info, args=(repo_url, config))
            threads.append(t2)
            t2.start()

        if len(threads) >= GIT_THREAD_LIMIT:
            logging.info("Thread limit reached, waiting for threads to finish...")
            for thread in threads:
                logging.info(f"Joining git thread {thread.name}...")
                thread.join()
            threads = []
            logging.info("Continuing with the next batch of URLs...")
    
    for thread in threads:
        thread.join()
    
    logging.info("GIT Data update completed.")



def do_update_github(urls, config):
    threads = []
        
    for repo_url in urls:
        if repo_url in GITHUB_SKIP_LIST:
            logging.warning(f"Skipping URL: {repo_url}")
            continue

        logging.info(f"GITHUB: Processing URL: {repo_url}")

        if len(threads) < GITHUB_THREAD_LIMIT and config.update_github:
            t1 = threading.Thread(target=update_github_info, args=(repo_url, config))
            threads.append(t1)
            t1.start()

        if len(threads) >= GITHUB_THREAD_LIMIT:
            logging.info("Thread limit reached, waiting for threads to finish...")
            for thread in threads:
                logging.info(f"Joining github thread {thread.name}...")
                thread.join()
            threads = []
            logging.info("Continuing with the next batch of URLs...")
    
    for thread in threads:
        thread.join()
    
    logging.info("GITHUB Data update completed.")



def generate_output(config):
    if config.output == "excel" and config.excel_file:
        logging.info(f"Updating {config.excel_file}...")
        urls = extract_urls(config.excel_file)
        repo_data = {}
        for url in urls:
            repo_name, owner = parse_url(url)
            repo = RepoInformation(owner, repo_name, url)
            git_data = get_git_info(repo.id, config)
            if git_data is None:
                logging.warning(f"No git data found for {url}. Skipping...")
                continue
            github_data = get_github_info(repo, config)
            if github_data is None:
                logging.warning(f"No github data found for {url}. Skipping...")
                continue
            repo = github_data
            repo.stat = git_data
            repo_data[url] = repo
            logging.info(f"Data added for {url}.")
        generate_exec_report(repo_data, config.excel_file)
    if config.output == "console":
        logging.info("console")
        urls = []
        repos_data = {}
        
        # Handle local repository mode
        if config.local_repo:
            logging.info(f"Using local repository: {config.local_repo}")
            repo_path = os.path.join(config.repos_folder, config.local_repo)
            
            if not os.path.exists(repo_path) or not is_git_repo(repo_path):
                logging.error(f"Local repository not found or not a valid git repo: {repo_path}")
                return
                
            # Create a minimal repo object for local mode
            repo = RepoInformation("", config.local_repo, "")
            repo.id = config.local_repo
            # Set the path for the repository to help performance analysis find it
            repo.path = repo_path
            
            # Get git data from cache or collect it if not available
            cache_id = config.local_repo  # Use the local repo name directly for cache files
            git_data = get_git_info(cache_id, config)
            if git_data is None:
                logging.info(f"No git data found in cache for {config.local_repo}. Collecting...")
                
                # Create collector config
                conf = create_collectors_config(config)
                # For local repo mode, disable extended stats collection by default
                # unless explicitly enabled with -E flag
                conf.extended_stats = config.extended_stats
                git_data = GitDataCollector(conf)
                
                # Collect git data
                prevdir = os.getcwd()
                os.chdir(repo_path)
                try:
                    logging.debug(f"Collecting data from {repo.id}...")
                    git_data.collect()
                    git_data.refine()
                    # Save to cache using the local repo name directly
                    save_to_cache(config.cache_folder, cache_id, git_data, CACHE_GIT_EXT)
                except Exception as e:
                    logging.error(f"Failed to collect data from {repo.id}: {e}")
                os.chdir(prevdir)
            
            # Skip GitHub data for local mode
            repo.stat = git_data
            repos_data[config.local_repo] = repo
            
        # Handle URL mode (original functionality)
        elif config.url or config.excel_file:
            if config.url:
                urls.append(config.url)
            elif config.excel_file:
                logging.info(f"Updating {config.excel_file}...")
                urls = extract_urls(config.excel_file)
            
            for url in urls:
                repo_name, owner = parse_url(url)
                repo = RepoInformation(owner, repo_name, url)
                logging.info(f"Collecting data for {url}...")
                git_data = get_git_info(repo.id, config)
                if git_data is None:
                    logging.warning(f"No git data found for {url}. Skipping...")
                    continue
                github_data = get_github_info(repo, config)
                if github_data is None:
                    logging.warning(f"No github data found for {url}. Skipping...")
                    continue
                repo = github_data
                repo.stat = git_data
                repos_data[url] = repo
        for repo in repos_data.values():
            # Skip contributors report for local repo mode
            if not config.local_repo:
                generate_contributors_report(repo)
                
            # Use months_to_analyze for filtering stats in stats mode
            months = int(config.months_to_analyze) if hasattr(config, 'months_to_analyze') and config.months_to_analyze else None
            analyze_author_contributions(repo, months_to_analyze=months, config=config)
            
            # Run performance analysis if requested
            if hasattr(config, 'analyze_performance') and config.analyze_performance > 0:
                analyze_performance_over_time(repo, months_to_analyze=config.analyze_performance, config=config)
