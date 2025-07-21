import re
import os
import json
import datetime

from multiprocessing import Pool

from .data_collector import DataCollector
from .utils import getkeyssortedbyvaluekey, getnumoffilesfromrev, getnumoflinesinblob, getstatsummarycounts
from .git_utils import (
    get_total_authors, get_total_loc, get_author_line_stats,
    getpipeoutput, getlogrange, getcommitrange, get_file_extension,
    get_domain_name, format_date, update_commit_timestamps,
    update_lines_by_date, process_line_stats, update_author_commit_stats,
    get_file_revisions_data, get_file_extension_stats, get_line_stats_data,
    get_author_stats_data, get_commit_messages_data
)
from .constans import FIND_CMD, GREP_CMD


class GitStatCollector:
    """Collects essential git statistics used by the analyzer."""
    
    def __init__(self, config):
        """Initialize the collector with the given configuration."""
        self.config = config
        self.cache = {}
        
        # Basic statistics
        self.total_authors = 0
        self.total_commits = 0
        self.total_files = 0
        self.total_lines = 0
        self.total_size = 0
        self.total_lines_added = 0
        self.total_lines_removed = 0
        
        # Author statistics
        self.authors = {}
        self.authors_by_commits = []
        
        # Time-based statistics
        self.first_commit_stamp = 0
        self.last_commit_stamp = 0
        self.active_days = set()
        self.last_active_day = None
        
        # Lines statistics
        self.lines_added_by_month = {}
        self.lines_added_by_year = {}
        self.lines_removed_by_month = {}
        self.lines_removed_by_year = {}
        self.changes_by_date = {}
        self.changes_by_date_by_author = {}
        
        # File statistics
        self.extensions = {}
        
        # Domain statistics
        self.domains = {}
        
    def collect(self):
        """Collect essential git statistics."""
        # Collect basic statistics
        self._collect_basic_stats()
        
        # Collect file statistics
        self._collect_file_stats()
        
        # Collect extension statistics
        self._collect_extension_stats()
        
        # Collect line statistics
        self._collect_line_stats()
        
        # Collect author statistics
        self._collect_author_stats()
        
        # Refine collected data
        self.refine()
        
        return True
        
    def _collect_basic_stats(self):
        """Collect basic repository statistics."""
        self.total_authors += get_total_authors(self.config.start_date, self.config.commit_begin, self.config.commit_end)
        self.loc = get_total_loc()
        
    def _collect_file_stats(self):
        """Collect file statistics from the git repository."""
        # Get file revisions
        revlines = get_file_revisions_data(
            self.config.start_date, 
            self.config.commit_begin, 
            self.config.commit_end
        )
        
        lines = []
        revs_to_read = []
        
        # Process each revision
        for revline in revlines:
            if revline == "":
                continue
                
            time, rev = revline.split(" ")
            
            # Check cache for existing data
            if "files_in_tree" not in self.cache.keys():
                revs_to_read.append((time, rev))
                continue
                
            if rev in self.cache["files_in_tree"].keys():
                lines.append("%d %d" % (int(time), self.cache["files_in_tree"][rev]))
            else:
                revs_to_read.append((time, rev))

        # Process revisions not in cache using parallel processing
        if revs_to_read:
            pool = Pool(processes=self.config.processes)
            time_rev_count = pool.map(getnumoffilesfromrev, revs_to_read)
            pool.terminate()
            pool.join()

            # Update cache with new revision data
            for (time, rev, count) in time_rev_count:
                if "files_in_tree" not in self.cache:
                    self.cache["files_in_tree"] = {}
                self.cache["files_in_tree"][rev] = count
                lines.append("%d %d" % (int(time), count))

        # Update total commits and process file counts by timestamp
        self.total_commits += len(lines)
        self._process_file_counts(lines)
        
    def _process_file_counts(self, lines):
        """Process file counts from revision data."""
        self.files_by_stamp = {}
        for line in lines:
            parts = line.split(" ")
            if len(parts) != 2:
                continue
                
            (stamp, files) = parts[0:2]
            try:
                self.files_by_stamp[int(stamp)] = int(files)
            except ValueError:
                print('Warning: failed to parse line "%s"' % line)
                
    def _collect_extension_stats(self):
        """Collect extension and file size statistics from the git repository."""
        # Get file information
        lines = get_file_extension_stats(
            self.config.commit_begin, 
            self.config.commit_end
        )
        
        # Process files to collect extension and size statistics
        for line in lines:
            if len(line) == 0:
                continue
                
            parts = re.split(r"\s+", line, 4)
            if len(parts) < 5:
                continue
                
            # Skip submodules
            if parts[0] == "160000" and parts[3] == "-":
                continue
                
            size = int(parts[3])
            fullpath = parts[4]

            # Update total size and file count
            self.total_size += size
            self.total_files += 1

            # Extract file extension
            filename = fullpath.split("/")[-1]  # strip directories
            ext = self._get_file_extension(filename)
            
            # Update extension statistics
            if ext not in self.extensions:
                self.extensions[ext] = {"files": 0, "lines": 0}
            self.extensions[ext]["files"] += 1
                
    def _get_file_extension(self, filename):
        """Extract file extension from filename."""
        return get_file_extension(filename, self.config.max_ext_length)
        
    def _collect_line_stats(self):
        """Collect line statistics from the git repository."""
        # Get line statistics
        lines = get_line_stats_data(
            self.config.linear_linestats,
            self.config.start_date, 
            self.config.commit_begin, 
            self.config.commit_end
        )
        
        # Process line statistics
        self._process_line_stats(lines)
        
    def _process_line_stats(self, lines):
        """Process line statistics from git log output."""
        changes_by_date, total_lines_added, total_lines_removed, total_lines = process_line_stats(lines)
        
        # Update class attributes with processed data
        self.changes_by_date = changes_by_date
        self.total_lines_added += total_lines_added
        self.total_lines_removed += total_lines_removed
        self.total_lines += total_lines
        
        # Update lines by date and commit timestamps for each change
        for stamp, change in self.changes_by_date.items():
            # Update lines added/removed by month and year
            update_lines_by_date(
                stamp, 
                change.get('ins', 0), 
                change.get('del', 0),
                self.lines_added_by_month,
                self.lines_removed_by_month,
                self.lines_added_by_year,
                self.lines_removed_by_year
            )
            
            # Update commit timestamps
            self.first_commit_stamp, self.last_commit_stamp, self.active_days, self.last_active_day = update_commit_timestamps(
                stamp,
                self.first_commit_stamp,
                self.last_commit_stamp,
                self.active_days
            )
        
    def _update_lines_by_date(self, stamp, inserted, deleted):
        """Update lines added/removed statistics by month and year."""
        update_lines_by_date(
            stamp, 
            inserted, 
            deleted,
            self.lines_added_by_month,
            self.lines_removed_by_month,
            self.lines_added_by_year,
            self.lines_removed_by_year
        )
            
    def _update_commit_timestamps(self, stamp):
        """Update first and last commit timestamps."""
        self.first_commit_stamp, self.last_commit_stamp, self.active_days, self.last_active_day = update_commit_timestamps(
            stamp,
            self.first_commit_stamp,
            self.last_commit_stamp,
            self.active_days
        )
        
    def _collect_author_stats(self):
        """Collect author statistics from the git repository."""
        # Initialize author changes by date dictionary
        self.changes_by_date_by_author = {}  # stamp -> author -> lines_added

        # Get author commit data with line statistics
        # We need to walk through every commit to know who committed what
        lines = get_author_stats_data(
            self.config.start_date, 
            self.config.commit_begin, 
            self.config.commit_end
        )
        
        # Process lines in chronological order
        lines.reverse()
        files = 0
        inserted = 0
        deleted = 0
        author = None
        stamp = 0
        
        # Get commit messages by author to calculate average message size
        author_messages = get_commit_messages_data(
            self.config.start_date,
            self.config.commit_begin,
            self.config.commit_end
        )
        
        # Calculate message size statistics for each author
        for author, messages in author_messages.items():
            if author not in self.authors:
                self.authors[author] = {
                    "lines_added": 0,
                    "lines_removed": 0,
                    "commits": 0,
                    "first_commit_stamp": 0,
                    "last_commit_stamp": 0,
                    "active_days": set()
                }
            # Calculate total message size
            if messages:
                total_size = sum(len(msg) for msg in messages)
                avg_size = total_size / len(messages)
                
                # Store the message size statistics
                if author in self.authors:
                    self.authors[author]["total_message_size"] = total_size
                    self.authors[author]["avg_message_size"] = avg_size
        
        # Make sure all authors have an avg_message_size value
        # (in case some authors don't have any commit messages)
        for author in self.authors:
            if "avg_message_size" not in self.authors[author]:
                self.authors[author]["avg_message_size"] = 0
        
        for line in lines:
            if len(line) == 0:
                continue

            # Process commit line (<stamp> <author>)
            if re.search("files? changed", line) is None:
                pos = line.find(" ")
                if pos != -1:
                    try:
                        # Extract timestamp and author
                        oldstamp = stamp
                        (stamp, author) = (int(line[:pos]), line[pos + 1:])
                        
                        # Handle clock skew
                        if oldstamp > stamp:
                            # Keep old timestamp to avoid having ugly graph
                            stamp = oldstamp
                            
                        # Initialize author data if not present
                        if author not in self.authors:
                            self.authors[author] = {
                                "lines_added": 0,
                                "lines_removed": 0,
                                "commits": 0,
                                "first_commit_stamp": 0,
                                "last_commit_stamp": 0,
                                "active_days": set(),
                                "total_message_size": 0,
                                "avg_message_size": 0
                            }
                            
                        # Update author statistics
                        self._update_author_commit_stats(author, stamp, inserted, deleted)
                        
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
                else:
                    print('Warning: failed to handle line "%s"' % line)
                    (files, inserted, deleted) = (0, 0, 0)
                    
    def _update_author_commit_stats(self, author, stamp, inserted, deleted):
        """Update author commit statistics."""
        # Update author stats using common utility function
        update_author_commit_stats(author, stamp, inserted, deleted, self.authors)
        
        # Update changes by date by author (specific to this class)
        if stamp not in self.changes_by_date_by_author:
            self.changes_by_date_by_author[stamp] = {}
            
        if author not in self.changes_by_date_by_author[stamp]:
            self.changes_by_date_by_author[stamp][author] = {}
            
        self.changes_by_date_by_author[stamp][author]["lines_added"] = self.authors[author]["lines_added"]
        self.changes_by_date_by_author[stamp][author]["commits"] = self.authors[author]["commits"]
        
        # Include average message size in the changes by date
        if "avg_message_size" in self.authors[author]:
            self.changes_by_date_by_author[stamp][author]["avg_message_size"] = self.authors[author]["avg_message_size"]
        
    def get_domain_name(self, email):
        """Get domain name from email address."""
        return get_domain_name(email)
        
    def refine(self):
        """Refine collected data for analysis."""
        # Sort authors by commits
        self.authors_by_commits = getkeyssortedbyvaluekey(
            self.authors, "commits")
        self.authors_by_commits.reverse()  # most first
        
        # Add additional author information
        for i, name in enumerate(self.authors_by_commits):
            self.authors[name]["place_by_commits"] = i + 1

        for name in self.authors.keys():
            a = self.authors[name]
            a["commits_frac"] = (100 * float(a["commits"])) / self.getTotalCommits() if self.getTotalCommits() > 0 else 0
            
            # Convert timestamps to dates
            if "first_commit_stamp" in a and a["first_commit_stamp"] > 0:
                date_first = datetime.datetime.fromtimestamp(a["first_commit_stamp"])
                a["date_first"] = date_first.strftime("%Y-%m-%d")
            else:
                a["date_first"] = "N/A"
                
            if "last_commit_stamp" in a and a["last_commit_stamp"] > 0:
                date_last = datetime.datetime.fromtimestamp(a["last_commit_stamp"])
                a["date_last"] = date_last.strftime("%Y-%m-%d")
                
                # Calculate time delta
                if "date_first" in a and a["date_first"] != "N/A":
                    date_first = datetime.datetime.fromtimestamp(a["first_commit_stamp"])
                    delta = date_last - date_first
                    a["timedelta"] = delta
            else:
                a["date_last"] = "N/A"
                
            # Ensure lines added/removed are present
            if "lines_added" not in a:
                a["lines_added"] = 0
            if "lines_removed" not in a:
                a["lines_removed"] = 0
                
    # Getter methods for statistics
    def getActiveDays(self):
        return self.active_days

    def getAuthorInfo(self, author):
        info = self.authors[author]
        # Ensure avg_message_size is included in the returned info
        if "avg_message_size" not in info:
            info["avg_message_size"] = 0
        return info

    def getAuthors(self, limit=None):
        res = getkeyssortedbyvaluekey(self.authors, "commits")
        res.reverse()
        return res[:limit]

    def getCommitDeltaDays(self):
        return (self.last_commit_stamp / 86400 - self.first_commit_stamp / 86400) + 1

    def getDomainInfo(self, domain):
        return self.domains[domain]

    def getDomains(self):
        return self.domains.keys()

    def getFirstCommitDate(self):
        return datetime.datetime.fromtimestamp(self.first_commit_stamp)

    def getLastCommitDate(self):
        return datetime.datetime.fromtimestamp(self.last_commit_stamp)

    def getTotalAuthors(self):
        return self.total_authors

    def getTotalCommits(self):
        return self.total_commits

    def getTotalFiles(self):
        return self.total_files

    def getTotalLOC(self):
        return self.total_lines

    def getTotalSize(self):
        return self.total_size
