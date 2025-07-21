import json
import logging
import time
import requests

import os

GITHUB_API = "https://api.github.com/"
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
if not GITHUB_TOKEN:
    logging.warning("GITHUB_TOKEN environment variable is not set. GitHub API rate limits will be restricted.")
    GITHUB_TOKEN = ""

def get_rate_limit_info(response):
    """Safely extract rate limit information from response headers"""
    limit = response.headers.get('X-RateLimit-Limit', '0')
    remaining = response.headers.get('X-RateLimit-Remaining', '0')
    wait_till = response.headers.get('X-RateLimit-Reset', str(int(time.time()) + 3600))
    return limit, remaining, wait_till

def github_get_repo(owner, name):
    result = {}
    url = f"{GITHUB_API}repos/{owner}/{name}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"} if GITHUB_TOKEN else {}
    response = requests.get(url, headers=headers)
    
    limit = response.headers['X-RateLimit-Limit']
    remaining = response.headers['X-RateLimit-Remaining']
    wait_till = response.headers['X-RateLimit-Reset']
    logging.info(f"Fetching data from GitHub: {url}, rate limit: {remaining}/{limit}, response: {response}")
    if response.status_code == 200:
        result = response.json()
    elif response.status_code == 404:
        logging.error(f"Repository not found: {owner}/{name}")
        return None
    elif response.status_code == 403:
        logging.warning(f"[repo] Rate limit exceeded. Waiting for reset till {wait_till} ({int(wait_till) - int(time.time())}s)")
        time.sleep(int(wait_till) - int(time.time()) + 5)
        logging.warning("Retrying...")
    else:
        logging.error(f"Failed to fetch data: {response.status_code}: {response}")
    return result


def github_get_repo_contributors(owner, name):
    url = f"{GITHUB_API}repos/{owner}/{name}/contributors"
    contributors = []

    p = 1
    while True:
        headers = {"Authorization": f"token {GITHUB_TOKEN}"} if GITHUB_TOKEN else {}
        response = requests.get(url, params={"per_page": 100, "page":p, "anon": "true"}, headers=headers)
        limit = response.headers['X-RateLimit-Limit']
        remaining = response.headers['X-RateLimit-Remaining']
        wait_till = response.headers['X-RateLimit-Reset']
        logging.info(f"Fetching data from GitHub: {url}, rate limit: {remaining}/{limit}, response: {response}")
        if response.status_code == 200:
            part = response.json()
            contributors.extend(part)
            if len(part) < 100:
                break
            p += 1
        elif response.status_code == 403:
            logging.warning(f"[repos contributors]Rate limit exceeded. Waiting for reset till {wait_till} ({int(wait_till) - int(time.time())}s)")
            time.sleep(int(wait_till) - int(time.time()) + 5)
            logging.warning("Retrying...")
        else:
            logging.error(f"Failed to fetch data: {response.status_code}: {response}")
            return []

    return contributors


def github_get_user(login):
    result = {}
    url = f"{GITHUB_API}users/{login}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"} if GITHUB_TOKEN else {}
    response = requests.get(url, headers=headers)
    
    limit = response.headers['X-RateLimit-Limit']
    remaining = response.headers['X-RateLimit-Remaining']
    wait_till = response.headers['X-RateLimit-Reset']
    logging.info(f"Fetching data from GitHub: {url}, rate limit: {remaining}/{limit}, response: {response}")
    if response.status_code == 200:
        result = response.json()
    elif response.status_code == 403:
        logging.warning(f"[users] Rate limit exceeded. Waiting for reset till {wait_till} ({int(wait_till) - int(time.time())}s)")
        time.sleep(int(wait_till) - int(time.time()) + 5)
        logging.warning("Retrying...")
    else:
        logging.error(f"Failed to fetch data: {response.status_code}: {response}")
    return result


def github_get_user_orgs(login):
    result = {}
    url = f"{GITHUB_API}users/{login}/orgs"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"} if GITHUB_TOKEN else {}
    response = requests.get(url, headers=headers)
    limit = response.headers['X-RateLimit-Limit']
    remaining = response.headers['X-RateLimit-Remaining']
    wait_till = response.headers['X-RateLimit-Reset']
    logging.info(f"Fetching data from GitHub: {url}, rate limit: {remaining}/{limit}, response: {response}")
    if response.status_code == 200:
        result = response.json()
    elif response.status_code == 403:
        logging.warning(f"[user orgs] Rate limit exceeded. Waiting for reset till {wait_till} ({int(wait_till) - int(time.time())}s)")
        time.sleep(int(wait_till) - int(time.time()) + 5)
        logging.warning("Retrying...")
    else:
        logging.error(f"Failed to fetch data: {response.status_code}: {response}")
    return result
