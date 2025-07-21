import logging
import time
import sys
import subprocess
import os
import re
from typing import Iterator

import urllib

from common.constans import FIND_CMD, ON_LINUX


def parse_url(url):
    parsed_url = urllib.parse.urlparse(url)
    # Remove any trailing slashes from the path
    path = parsed_url.path.rstrip('/')

    repo = ""
    owner = ""
    parts = path.split('/')
    if len(parts) > 1:
        repo = parts[-1]
    if len(parts) > 2:
        owner = parts[-2]

    return repo, owner


def getpipeoutput(cmds, quiet=False):
    result = ""
    try:
        # global exectime_external
        start = time.time()
        if not quiet and ON_LINUX and os.isatty(1):
            logging.debug(">> " + " | ".join(cmds))
            sys.stdout.flush()
            
        # Print the command for debugging
        logging.debug(f"Executing command: {cmds[0]}")
        
        # Use shell=True but be careful with command formatting
        p = subprocess.Popen(cmds[0], stdout=subprocess.PIPE, shell=True)
        processes = [p]
        
        for x in cmds[1:]:
            logging.debug(f"Piping to command: {x}")
            p = subprocess.Popen(x,
                                stdin=p.stdout,
                                stdout=subprocess.PIPE,
                                shell=True)
            processes.append(p)
            
        output = p.communicate()[0]
        for p in processes:
            p.wait()
        end = time.time()
        if not quiet:
            if ON_LINUX and os.isatty(1):
                logging.debug("\r"),
            logging.debug("[%.5f] >> %s" % (end - start, " | ".join(cmds)))
        # exectime_external += end - start

        result = bytes.decode(output, errors='ignore').rstrip("\n")
    except Exception as e:  
        logging.error(f"Execution error output: {e}")
    return result


def getlogrange(start_date, commit_begin, commit_end, defaultrange="HEAD", end_only=True):
    commit_range = getcommitrange(commit_begin, commit_end, defaultrange, end_only)
    if len(start_date) > 0:
        return '--since="%s" "%s"' % (start_date, commit_range)
    return commit_range


def getcommitrange(commit_begin, commit_end, defaultrange="HEAD", end_only=False):
    if len(commit_end) > 0:
        if end_only or len(commit_begin) == 0:
            return commit_end
        return "%s..%s" % (commit_begin, commit_end)
    return defaultrange


def getkeyssortedbyvalues(dict):
    return map(lambda el: el[1],
        sorted(map(lambda el: (el[1], el[0]), dict.items())))


# dict['author'] = { 'commits': 512 } - ...key(dict, 'commits')
def getkeyssortedbyvaluekey(d, key, rev=False):
    return list(map(lambda el: el[1],
        sorted(map(lambda el: (d[el][key], el), d.keys()), reverse=rev)))


def getstatsummarycounts(line):
    numbers = re.findall(r"\d+", line)
    if len(numbers) == 1:
        # neither insertions nor deletions:
        # may probably only happen for "0 files changed"
        numbers.append(0)
        numbers.append(0)
    elif len(numbers) == 2 and line.find("(+)") != -1:
        numbers.append(0)
        # only insertions were printed on line
    elif len(numbers) == 2 and line.find("(-)") != -1:
        numbers.insert(1, 0)
        # only deletions were printed on line
    return numbers


VERSION = 0


def getversion():
    global VERSION
    if VERSION == 0:
        gitstats_repo = os.path.dirname(os.path.abspath(__file__))
        VERSION = getpipeoutput([
            "git --git-dir=%s/.git --work-tree=%s rev-parse --short %s" %
            (gitstats_repo, gitstats_repo,
             getcommitrange("HEAD").split("\n")[0])
        ])
    return VERSION


def getgitversion():
    return getpipeoutput(["git --version"]).split("\n")[0]


def getnumoffilesfromrev(time_rev):
    """
    Get number of files changed in commit
    """
    time, rev = time_rev
    return (
        int(time),
        rev,
        int(
            getpipeoutput(['git ls-tree -r --name-only "%s"' % rev,
                           FIND_CMD]).split("\n")[0]),
    )


def getnumoflinesinblob(ext_blob):
    """
	Get number of lines in blob
	"""
    ext, blob_id = ext_blob
    return (
        ext,
        blob_id,
        int(
            getpipeoutput(["git cat-file blob %s" % blob_id,
                           FIND_CMD]).split()[0]),
    )

