import subprocess
import os
import re
import sys
import time
import logging
from datetime import datetime, date
from typing import Dict, List, Set, Tuple, Optional, Union, Any

from .constans import FIND_CMD, GREP_CMD, ON_LINUX
from .utils import getstatsummarycounts

def execute_git_command(cmd: str, quiet: bool = False) -> str:
    return getpipeoutput([cmd], quiet)


def getpipeoutput(cmds: List[str], quiet: bool = False) -> str:
    result = ""
    try:
        start = time.time()
        if not quiet and ON_LINUX and os.isatty(1):
            logging.debug(">> " + " | ".join(cmds))
            sys.stdout.flush()
        p = subprocess.Popen(cmds[0], stdout=subprocess.PIPE, shell=True)
        processes = [p]
        for x in cmds[1:]:
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

        result = bytes.decode(output, errors='ignore').rstrip("\n")
    except Exception as e:  
        logging.error(f"Execution error output: {e}")
    return result


def get_total_authors(start_date: str, commit_begin: str, commit_end: str) -> int:
    return int(
        getpipeoutput(["git shortlog -s %s" % getlogrange(start_date, commit_begin, commit_end), FIND_CMD]))


def get_total_loc() -> int:
    return int(getpipeoutput(['git ls-files | xargs cat | wc -l']))


def get_tags_info() -> List[Tuple[str, str]]:
    lines = getpipeoutput(["git show-ref --tags"]).split("\n")
    tags = []
    for line in lines:
        if len(line) == 0:
            continue
        (hash, tag) = line.split(" ")
        tag = tag.replace("refs/tags/", "")
        tags.append((hash, tag))
    return tags


def get_tag_commit_info(hash: str) -> Tuple[int, str]:
    output = getpipeoutput(['git log "%s" --pretty=format:"%%ct %%aN" -n 1' % hash])
    if len(output) > 0:
        parts = output.split(" ")
        stamp = 0
        try:
            stamp = int(parts[0])
        except ValueError:
            stamp = 0
        author = " ".join(parts[1:])
        return (stamp, author)
    return (0, "")


def get_tag_commits(tag: str, prev_tag: Optional[str] = None) -> str:
    cmd = 'git shortlog -s "%s"' % tag
    if prev_tag is not None:
        cmd += ' "^%s"' % prev_tag
    return getpipeoutput([cmd])


def get_revision_history(start_date: str, commit_begin: str, commit_end: str) -> List[str]:
    # Construct the git command more carefully to avoid shell interpretation issues
    log_range = getlogrange(start_date, commit_begin, commit_end, "HEAD")
    logging.debug(f"Using log range: {log_range}")
    
    # Use a simpler format for the git command
    cmd = f"git rev-list --pretty=format:'%ct %ci %aN <%aE>' {log_range}"
    logging.debug(f"Executing git command: {cmd}")
    
    output = getpipeoutput([cmd, GREP_CMD + " -v ^commit"])
    
    # Debug the output
    if not output.strip():
        logging.warning("No revision history found")
        return []
    
    return output.split("\n")


def get_file_revisions(start_date: str, commit_begin: str, commit_end: str) -> List[str]:
    # Construct the git command more carefully to avoid shell interpretation issues
    log_range = getlogrange(start_date, commit_begin, commit_end, "HEAD")
    logging.debug(f"Using log range for file revisions: {log_range}")
    
    # Use a simpler format for the git command
    cmd = f"git rev-list --pretty=format:'%ct %T' {log_range}"
    logging.debug(f"Executing git command for file revisions: {cmd}")
    
    output = getpipeoutput([cmd, GREP_CMD + " -v ^commit"])
    
    # Debug the output
    if not output.strip():
        logging.warning("No file revisions found")
        return []
    
    return output.strip().split("\n")


def get_file_info(commit_begin: str, commit_end: str) -> List[str]:
    return getpipeoutput([
        "git ls-tree -r -l -z %s" % getcommitrange(commit_begin, commit_end, "HEAD", end_only=True)
    ]).split("\000")


def get_line_stats(linear_linestats: bool, start_date: str, commit_begin: str, commit_end: str) -> List[str]:
    extra = "--first-parent -m" if linear_linestats else ""
    return getpipeoutput([
        'git log --shortstat %s --pretty=format:"%%ct %%aN" %s' %
        (extra, getlogrange(start_date, commit_begin, commit_end, "HEAD"))
    ]).split("\n")


def get_author_line_stats(start_date: str, commit_begin: str, commit_end: str) -> List[str]:
    return getpipeoutput([
        'git log --shortstat --date-order --pretty=format:"%%ct %%aN" %s' %
        (getlogrange(start_date, commit_begin, commit_end, "HEAD"))
    ]).split("\n")


def get_tags() -> List[str]:
    lines = getpipeoutput(["git show-ref --tags", "cut -d/ -f3"])
    return lines.split("\n")


def get_rev_date(rev: str) -> int:
    # The rev string might be in the format "1752523997 2025-07-14 16:13:17 -0400 NatalliaBukhtsik <email>"
    # We need to extract just the commit hash or timestamp from it
    try:
        # Try to extract the timestamp directly from the beginning of the string
        parts = rev.split()
        if parts and parts[0].isdigit():
            # If the first part is a timestamp, return it directly
            return int(parts[0])
        
        # If we can't extract the timestamp directly, try to get it from git
        # But first extract just the commit hash if possible
        commit_hash = None
        if len(parts) >= 7 and '@' in parts[6]:  # Email format typically has @ symbol
            # The format might be "timestamp date time timezone name <email>"
            # Try to use the timestamp directly
            if parts[0].isdigit():
                return int(parts[0])
        
        # If we can't determine the format, use the whole string but log a warning
        logging.warning(f"Unusual revision format: {rev[:50]}...")
        output = getpipeoutput([f"git log --pretty=format:%ct -n 1 {rev.split()[0]}"])
        if output.strip().isdigit():
            return int(output.strip())
        return 0
    except Exception as e:
        logging.error(f"Error parsing revision date: {e}, rev: {rev[:50]}...")
        return 0


def getnumoffilesfromrev(time_rev: Tuple[str, str]) -> Tuple[int, str, int]:
    time, rev = time_rev
    return (
        int(time),
        rev,
        int(
            getpipeoutput(['git ls-tree -r --name-only "%s"' % rev,
                           FIND_CMD]).split("\n")[0]),
    )


def getnumoflinesinblob(ext_blob: Tuple[str, str]) -> Tuple[str, str, int]:
    ext, blob_id = ext_blob
    return (
        ext,
        blob_id,
        int(
            getpipeoutput(["git cat-file blob %s" % blob_id,
                           FIND_CMD]).split()[0]),
    )


def getlogrange(start_date: str, commit_begin: str, commit_end: str, defaultrange: str = "HEAD", end_only: bool = True) -> str:
    commit_range = getcommitrange(commit_begin, commit_end, defaultrange, end_only)
    if len(start_date) > 0:
        # Format the date filter properly for shell execution
        # Use a simple format without quotes to avoid shell interpretation issues
        # The date should be in YYYY-MM-DD format
        logging.debug(f"Using date filter with start_date: {start_date}")
        return f"--since={start_date} {commit_range}"
    return commit_range


def getcommitrange(commit_begin: str, commit_end: str, defaultrange: str = "HEAD", end_only: bool = False) -> str:
    if len(commit_end) > 0:
        if end_only or len(commit_begin) == 0:
            return commit_end
        return "%s..%s" % (commit_begin, commit_end)
    return defaultrange

def get_file_extension(filename: str, max_ext_length: int = 10) -> str:
    if filename.find(".") == -1 or filename.rfind(".") == 0:
        return ""
        
    ext = filename[(filename.rfind(".") + 1):]
    if len(ext) > max_ext_length:
        return ""
        
    return ext


def get_domain_name(email: str) -> str:
    return email.split('@', 1)[1] if '@' in email else ''


def format_date(timestamp: int) -> str:
    return datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d")


def update_commit_timestamps(stamp: int, first_stamp: int, last_stamp: int, active_days: Set[str]) -> Tuple[int, int, Set[str], str]:
    if first_stamp == 0 or stamp < first_stamp:
        first_stamp = stamp
        
    if last_stamp == 0 or stamp > last_stamp:
        last_stamp = stamp
        
    # Update active days
    date = datetime.fromtimestamp(stamp)
    yymmdd = date.strftime("%Y-%m-%d")
    active_days.add(yymmdd)
    
    return first_stamp, last_stamp, active_days, yymmdd


def update_lines_by_date(stamp: int, inserted: int, deleted: int, 
                        lines_added_by_month: Dict[str, int], 
                        lines_removed_by_month: Dict[str, int],
                        lines_added_by_year: Dict[int, int], 
                        lines_removed_by_year: Dict[int, int]) -> None:
    # Convert timestamp to date
    date = datetime.fromtimestamp(stamp)
    
    # Update by month
    yymm = date.strftime("%Y-%m")
    lines_added_by_month[yymm] = lines_added_by_month.get(yymm, 0) + inserted
    lines_removed_by_month[yymm] = lines_removed_by_month.get(yymm, 0) + deleted

    # Update by year
    yy = date.year
    lines_added_by_year[yy] = lines_added_by_year.get(yy, 0) + inserted
    lines_removed_by_year[yy] = lines_removed_by_year.get(yy, 0) + deleted


def process_line_stats(lines: List[str]) -> Tuple[Dict[int, Dict[str, int]], int, int, int]:
    changes_by_date = {}  # stamp -> { files, ins, del }
    
    # Reverse lines to process chronologically
    lines.reverse()
    
    files = 0
    inserted = 0
    deleted = 0
    total_lines = 0
    total_lines_added = 0
    total_lines_removed = 0
    author = None
    
    for line in lines:
        if len(line) == 0:
            continue

        # Process commit line (<stamp> <author>)
        if re.search("files? changed", line) is None:
            pos = line.find(" ")
            if pos != -1:
                try:
                    # Extract timestamp and author
                    (stamp, author) = (int(line[:pos]), line[pos + 1:])
                    
                    # Record changes for this timestamp
                    changes_by_date[stamp] = {
                        "files": files,
                        "ins": inserted,
                        "del": deleted,
                        "lines": total_lines,
                    }

                    # Reset counters for next commit
                    files, inserted, deleted = 0, 0, 0
                except ValueError:
                    print('Warning: unexpected line "%s"' % line)
            else:
                print('Warning: unexpected line "%s"' % line)
        else:
            # Process stats line (N files changed, N insertions, N deletions)
            numbers = getstatsummarycounts(line)

            if len(numbers) == 3:
                (files, inserted, deleted) = map(lambda el: int(el), numbers)
                
                # Update total line counts
                total_lines += inserted
                total_lines -= deleted
                total_lines_added += inserted
                total_lines_removed += deleted
            else:
                print('Warning: failed to handle line "%s"' % line)
                (files, inserted, deleted) = (0, 0, 0)
                
    return changes_by_date, total_lines_added, total_lines_removed, total_lines


def update_author_commit_stats(author: str, stamp: int, inserted: int, deleted: int, 
                              authors: Dict[str, Dict[str, Any]]) -> None:
    # Update author's commit count and lines added/removed
    authors[author]["commits"] = authors[author].get("commits", 0) + 1
    authors[author]["lines_added"] = authors[author].get("lines_added", 0) + inserted
    authors[author]["lines_removed"] = authors[author].get("lines_removed", 0) + deleted
    
    # Update first and last commit timestamps
    if authors[author]["first_commit_stamp"] == 0 or stamp < authors[author]["first_commit_stamp"]:
        authors[author]["first_commit_stamp"] = stamp
        
    if authors[author]["last_commit_stamp"] == 0 or stamp > authors[author]["last_commit_stamp"]:
        authors[author]["last_commit_stamp"] = stamp
        
    # Update active days
    date = datetime.fromtimestamp(stamp)
    yymmdd = date.strftime("%Y-%m-%d")
    authors[author]["active_days"].add(yymmdd)


def get_file_revisions_data(start_date: str, commit_begin: str, commit_end: str) -> List[str]:
    return getpipeoutput([
        'git rev-list --pretty=format:"%%ct %%T" %s' %
        getlogrange(start_date, commit_begin, commit_end, "HEAD"),
        GREP_CMD + " -v ^commit",
    ]).strip().split("\n")


def get_file_extension_stats(commit_begin: str, commit_end: str) -> List[str]:
    return getpipeoutput([
        "git ls-tree -r -l -z %s" % getcommitrange(commit_begin, commit_end, "HEAD", end_only=True)
    ]).split("\000")


def get_line_stats_data(linear_linestats: bool, start_date: str, commit_begin: str, commit_end: str) -> List[str]:
    extra = "--first-parent -m" if linear_linestats else ""
    return getpipeoutput([
        'git log --shortstat %s --pretty=format:"%%ct %%aN" %s' %
        (extra, getlogrange(start_date, commit_begin, commit_end, "HEAD"))
    ]).split("\n")


def get_author_stats_data(start_date: str, commit_begin: str, commit_end: str) -> List[str]:
    return getpipeoutput([
        'git log --shortstat --date-order --pretty=format:"%%ct %%aN" %s' %
        (getlogrange(start_date, commit_begin, commit_end, "HEAD"))
    ]).split("\n")


def get_comment_density_data(cutoff_date: datetime = None, end_date: datetime = None, repo_path: str = None) -> Dict[str, Dict]:
    """
    Analyze commit patches to calculate the ratio of comments to code for each author.
    
    Args:
        cutoff_date: Optional datetime object. If provided, only commits after this date will be analyzed.
        end_date: Optional datetime object. If provided, only commits before this date will be analyzed.
        repo_path: Path to the git repository. If None, uses current directory.
        
    Returns:
        Dictionary with authors as keys and comment statistics as values.
    """
    logging.debug("Running get_comment_density_data()")
    author_comment_stats = {}
    
    # Format the date filters for git log
    date_filters = []
    
    # Add start date filter if provided
    if cutoff_date:
        start_date_str = cutoff_date.strftime("%Y-%m-%d")
        date_filters.append(f"--since={start_date_str}")
        logging.debug(f"Using start date filter: --since={start_date_str}")
    
    # Add end date filter if provided
    if end_date:
        end_date_str = end_date.strftime("%Y-%m-%d")
        date_filters.append(f"--until={end_date_str}")
        logging.debug(f"Using end date filter: --until={end_date_str}")
        
    # Join all date filters
    date_filter = " ".join(date_filters)
    
    # Store current directory
    original_dir = os.getcwd()
    
    # Change to repo directory if provided
    if repo_path:
        try:
            os.chdir(repo_path)
            logging.debug(f"Changed directory to: {repo_path}")
        except Exception as e:
            logging.debug(f"Error changing directory: {str(e)}")
            return {}
    
    # Get commit patches with author information
    # Use --patch to get the actual diff content
    if date_filter:
        git_cmd = f"git log {date_filter} --pretty=format:'COMMIT_START %aN' --patch"
    else:
        git_cmd = "git log --pretty=format:'COMMIT_START %aN' --patch"
    
    logging.debug(f"Running git command: {git_cmd}")
    try:
        output = getpipeoutput([git_cmd])
    except Exception as e:
        logging.debug(f"Error running git command: {str(e)}")
        if repo_path:
            os.chdir(original_dir)
        return {}
    
    # Process the output
    current_author = None
    in_diff = False
    comment_lines = 0
    code_lines = 0
    total_comment_lines = 0
    total_code_lines = 0
    
    # Regular expressions to identify comments in different languages
    comment_patterns = {
        # Single line comments
        'single': re.compile(r'^\+\s*(//|#|--|;)'),
        # Multi-line comment starts
        'multi_start': re.compile(r'^\+\s*(/\*|<!--)'),
        # Multi-line comment ends
        'multi_end': re.compile(r'^.*?(\*/|-->).*?$'),
        # Docstrings in Python
        'docstring': re.compile(r'^\+\s*("""|\'\'\')'),
    }
    
    in_multiline_comment = False
    in_docstring = False
    docstring_delimiter = None
    
    for line in output.split("\n"):
        if line.startswith("COMMIT_START"):
            # Save stats for previous author
            if current_author and (code_lines > 0 or comment_lines > 0):
                if current_author not in author_comment_stats:
                    author_comment_stats[current_author] = {
                        "comment_lines": 0,
                        "code_lines": 0,
                        "commits_analyzed": 0
                    }
                
                author_comment_stats[current_author]["comment_lines"] += comment_lines
                author_comment_stats[current_author]["code_lines"] += code_lines
                author_comment_stats[current_author]["commits_analyzed"] += 1
                
                total_comment_lines += comment_lines
                total_code_lines += code_lines
            
            # Reset for new commit
            current_author = line.replace("COMMIT_START ", "").strip()
            in_diff = False
            comment_lines = 0
            code_lines = 0
            in_multiline_comment = False
            in_docstring = False
            docstring_delimiter = None
            
        elif line.startswith("diff --git"):
            in_diff = True
            
        elif in_diff and line.startswith("+") and not line.startswith("++"):
            # This is an added line in the diff
            
            # Check for docstring delimiters (Python)
            if not in_docstring and comment_patterns['docstring'].search(line):
                in_docstring = True
                docstring_delimiter = line.strip("+").strip()[0:3]  # Get """ or '''
                comment_lines += 1
                continue
                
            if in_docstring:
                comment_lines += 1
                # Check if docstring ends
                if docstring_delimiter and docstring_delimiter in line[line.find("+")+1:]:
                    in_docstring = False
                    docstring_delimiter = None
                continue
                
            # Check for single-line comments
            if comment_patterns['single'].search(line):
                comment_lines += 1
                continue
                
            # Check for multi-line comment start
            if not in_multiline_comment and comment_patterns['multi_start'].search(line):
                in_multiline_comment = True
                comment_lines += 1
                # Check if multi-line comment ends on the same line
                if comment_patterns['multi_end'].search(line):
                    in_multiline_comment = False
                continue
                
            # Inside a multi-line comment
            if in_multiline_comment:
                comment_lines += 1
                # Check if multi-line comment ends
                if comment_patterns['multi_end'].search(line):
                    in_multiline_comment = False
                continue
                
            # If we got here, it's a code line
            code_lines += 1
    
    # Don't forget the last author
    if current_author and (code_lines > 0 or comment_lines > 0):
        if current_author not in author_comment_stats:
            author_comment_stats[current_author] = {
                "comment_lines": 0,
                "code_lines": 0,
                "commits_analyzed": 0
            }
        
        author_comment_stats[current_author]["comment_lines"] += comment_lines
        author_comment_stats[current_author]["code_lines"] += code_lines
        author_comment_stats[current_author]["commits_analyzed"] += 1
        
        total_comment_lines += comment_lines
        total_code_lines += code_lines
    
    # Calculate comment density for each author
    for author, stats in author_comment_stats.items():
        if stats["code_lines"] > 0:
            stats["comment_density"] = stats["comment_lines"] / stats["code_lines"]
        else:
            stats["comment_density"] = 0
    
    # Change back to original directory if needed
    if repo_path:
        os.chdir(original_dir)
    
    logging.debug(f"Analyzed comment density for {len(author_comment_stats)} authors")
    logging.debug(f"Total comment lines: {total_comment_lines}, Total code lines: {total_code_lines}")
    
    return author_comment_stats


def get_commit_messages_data(start_date: str, commit_begin: str, commit_end: str) -> Dict[str, List[str]]:
    """Get commit messages by author.
    
    Returns a dictionary with authors as keys and lists of their commit messages as values.
    This includes both subject and body of commit messages.
    """
    author_messages = {}
    
    # Define the log range
    log_range = getlogrange(start_date, commit_begin, commit_end, "HEAD")
    
    # Get all commits with their authors and full messages in a single command
    # Format: <author>|<message>
    git_cmd = f'git log {log_range} --pretty=format:"%aN|%B" --no-merges'
    output = getpipeoutput([git_cmd])
    
    # Process the output
    current_author = None
    current_message = []
    
    for line in output.split("\n"):
        if not line.strip():
            continue
            
        if "|" in line:
            # This is a new commit
            # If we have a previous message, save it
            if current_author and current_message:
                if current_author not in author_messages:
                    author_messages[current_author] = []
                author_messages[current_author].append("\n".join(current_message))
                current_message = []
            
            # Parse the new commit
            parts = line.split("|", 1)
            current_author = parts[0].strip()
            if len(parts) > 1:
                current_message.append(parts[1].strip())
        else:
            # This is a continuation of the current message
            if current_message:  # Only append if we have started a message
                current_message.append(line.strip())
    
    # Don't forget the last message
    if current_author and current_message:
        if current_author not in author_messages:
            author_messages[current_author] = []
        author_messages[current_author].append("\n".join(current_message))
    
    return author_messages


def get_commits_by_date(cutoff_date: datetime = None, end_date: datetime = None, repo_path: str = None) -> Dict[str, Dict]:
    """Get commit counts and other statistics by author within a date range.
    
    Args:
        cutoff_date: Optional datetime object. If provided, only commits after this date will be counted.
        end_date: Optional datetime object. If provided, only commits before this date will be counted.
        repo_path: Path to the git repository. If None, uses current directory.
        
    Returns:
        Dictionary with authors as keys and dictionaries of statistics as values.
    """
    logging.debug("Running get_commits_by_date()")
    author_stats = {}
    
    # Format the date filters for git log
    date_filters = []
    
    # Add start date filter if provided
    if cutoff_date:
        start_date_str = cutoff_date.strftime("%Y-%m-%d")
        date_filters.append(f"--since={start_date_str}")
        logging.debug(f"Using start date filter: --since={start_date_str}")
    else:
        logging.debug("No start date provided")
        
    # Add end date filter if provided
    if end_date:
        end_date_str = end_date.strftime("%Y-%m-%d")
        date_filters.append(f"--until={end_date_str}")
        logging.debug(f"Using end date filter: --until={end_date_str}")
    
    # Join all date filters
    date_filter = " ".join(date_filters)
    
    # Store current directory
    original_dir = os.getcwd()
    logging.debug(f"Current directory: {original_dir}")
    
    # Verify and adjust repo_path if needed
    if repo_path:
        # Check if the path exists
        if not os.path.exists(repo_path):
            logging.debug(f"Repository path does not exist: {repo_path}")
            # Try to find the repository in common locations
            possible_paths = [
                os.path.join(os.getcwd(), 'repos', os.path.basename(repo_path)),
                os.path.join(os.getcwd(), os.path.basename(repo_path)),
                os.path.join(os.path.dirname(os.getcwd()), 'repos', os.path.basename(repo_path))
            ]
            
            for path in possible_paths:
                if os.path.exists(path):
                    repo_path = path
                    logging.debug(f"Found repository at: {repo_path}")
                    break
            else:
                logging.debug("Could not find repository in common locations")
                return {}
    
    # Change to repo directory if provided
    if repo_path:
        try:
            os.chdir(repo_path)
            logging.debug(f"Changed directory to: {repo_path}")
            # Verify we're in a git repository
            if not os.path.exists('.git'):
                logging.debug(f"No .git directory found in {repo_path}")
                # Try to find .git directory in subdirectories
                for root, dirs, _ in os.walk(repo_path):
                    if '.git' in dirs:
                        git_dir_path = os.path.join(root, '.git')
                        logging.debug(f"Found .git directory at: {git_dir_path}")
                        os.chdir(root)
                        logging.debug(f"Changed directory to: {root}")
                        break
                else:
                    logging.debug("No .git directory found in repository")
                    os.chdir(original_dir)
                    return {}
        except Exception as e:
            logging.debug(f"Error changing directory: {str(e)}")
            return {}
    
    # Check if we're in a git repository
    try:
        check_cmd = 'git rev-parse --is-inside-work-tree'
        check_output = getpipeoutput([check_cmd])
        logging.debug(f"Git repo check: {check_output}")
        if check_output.strip() != 'true':
            logging.debug("Not in a git repository")
            if repo_path:
                os.chdir(original_dir)
            return {}
    except Exception as e:
        logging.debug(f"Error checking git repo: {str(e)}")
        if repo_path:
            os.chdir(original_dir)  # Change back to original directory
        return {}
    
    # Get commit counts by author
    # Construct the git command carefully to avoid shell interpretation issues
    if date_filter:
        # Use a simpler format for the git command to avoid shell interpretation issues
        git_cmd = f"git log {date_filter} --pretty=format:'%aN|%at|%H' --numstat"
    else:
        git_cmd = "git log --pretty=format:'%aN|%at|%H' --numstat"
    logging.debug(f"Running git command: {git_cmd}\nIn directory: {os.getcwd()}")
    try:
        output = getpipeoutput([git_cmd])
        logging.debug(f"Git command output length: {len(output)}")
        logging.debug(f"First 100 chars of output: {output[:100] if output else 'EMPTY'}")
    except Exception as e:
        logging.debug(f"Error running git command: {str(e)}")
        if repo_path:
            os.chdir(original_dir)  # Change back to original directory
        return {}
    
    # Process the output
    current_author = None
    current_timestamp = None
    current_commit = None
    lines_added = 0
    lines_removed = 0
    active_days = set()
    
    # Debug the output
    logging.debug(f"Processing git log output with {output.count('\n')} lines")
    if not output.strip():
        logging.debug("Git log output is empty, returning empty result")
        if repo_path:
            os.chdir(original_dir)  # Change back to original directory
        return {}
    
    for line in output.split("\n"):
        if not line.strip():
            continue
            
        if "|" in line and line.count("|") == 2:
            # This is a new commit
            # If we have a previous commit, save its stats
            if current_author and current_commit:
                if current_author not in author_stats:
                    author_stats[current_author] = {
                        "commits": 0,
                        "lines_added": 0,
                        "lines_removed": 0,
                        "active_days": set(),
                        "first_commit_stamp": float('inf'),
                        "last_commit_stamp": 0
                    }
                
                # Update stats
                author_stats[current_author]["commits"] += 1
                author_stats[current_author]["lines_added"] += lines_added
                author_stats[current_author]["lines_removed"] += lines_removed
                
                # Update timestamps
                if current_timestamp:
                    if current_timestamp < author_stats[current_author]["first_commit_stamp"]:
                        author_stats[current_author]["first_commit_stamp"] = current_timestamp
                    if current_timestamp > author_stats[current_author]["last_commit_stamp"]:
                        author_stats[current_author]["last_commit_stamp"] = current_timestamp
                    
                    # Add active day
                    commit_date = datetime.fromtimestamp(current_timestamp).strftime("%Y-%m-%d")
                    author_stats[current_author]["active_days"].add(commit_date)
                
                # Reset counters for the next commit
                lines_added = 0
                lines_removed = 0
            
            # Parse the new commit
            parts = line.split("|", 2)
            current_author = parts[0].strip()
            try:
                # Handle potential empty string or invalid timestamp
                timestamp_str = parts[1].strip()
                current_timestamp = int(timestamp_str) if timestamp_str else 0
            except (ValueError, IndexError) as e:
                logging.debug(f"Error parsing timestamp: {e}, using 0 instead")
                current_timestamp = 0
            
            # Make sure we have a valid commit hash
            if len(parts) > 2:
                current_commit = parts[2].strip()
            else:
                current_commit = "unknown"
            
        elif line.strip() and current_author and current_commit:
            # This is a file change line
            parts = line.split("\t")
            if len(parts) >= 3:
                try:
                    added = int(parts[0]) if parts[0] != "-" else 0
                    removed = int(parts[1]) if parts[1] != "-" else 0
                    lines_added += added
                    lines_removed += removed
                except ValueError:
                    pass
    
    # Don't forget the last commit
    if current_author and current_commit:
        if current_author not in author_stats:
            author_stats[current_author] = {
                "commits": 0,
                "lines_added": 0,
                "lines_removed": 0,
                "active_days": set(),
                "first_commit_stamp": float('inf'),
                "last_commit_stamp": 0
            }
        
        # Update stats
        author_stats[current_author]["commits"] += 1
        author_stats[current_author]["lines_added"] += lines_added
        author_stats[current_author]["lines_removed"] += lines_removed
        
        # Update timestamps
        if current_timestamp:
            if current_timestamp < author_stats[current_author]["first_commit_stamp"]:
                author_stats[current_author]["first_commit_stamp"] = current_timestamp
            if current_timestamp > author_stats[current_author]["last_commit_stamp"]:
                author_stats[current_author]["last_commit_stamp"] = current_timestamp
            
            # Add active day
            commit_date = datetime.fromtimestamp(current_timestamp).strftime("%Y-%m-%d")
            author_stats[current_author]["active_days"].add(commit_date)
    
    # Convert first_commit_stamp from infinity to 0 if no commits were found
    for author in author_stats:
        if author_stats[author]["first_commit_stamp"] == float('inf'):
            author_stats[author]["first_commit_stamp"] = 0
    
    # Change back to original directory if needed
    if repo_path:
        os.chdir(original_dir)
        logging.debug(f"Changed back to original directory: {original_dir}")
    
    return author_stats
