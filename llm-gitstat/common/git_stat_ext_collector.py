import re
import os
import json
import logging
from multiprocessing import Pool

from .utils import getkeyssortedbyvaluekey, getnumoflinesinblob
from .git_utils import (
    get_tags_info, get_tag_commit_info, get_tag_commits, get_revision_history,
    getpipeoutput, getlogrange, getcommitrange, get_rev_date, get_file_extension,
    get_domain_name, format_date, update_commit_timestamps
)
from .constans import FIND_CMD, GREP_CMD


class GitStatExtCollector:
    """Collects additional git statistics not heavily used by the analyzer."""
    
    def __init__(self, config):
        """Initialize the collector with the given configuration."""
        self.config = config
        self.cache = {}
        
        # File extension statistics
        self.extensions = {}
        
        # Tags statistics
        self.tags = {}
        self.tags_dates = {}
        self.tags_authors = {}
        
        # Revision statistics
        self.revisions = []
        self.rev_authors = {}
        self.rev_dates = {}
        
        # Activity statistics
        self.activity_by_hour_of_day = {}
        self.activity_by_day_of_week = {}
        self.activity_by_month_of_year = {}
        self.activity_by_hour_of_week = {}
        self.activity_by_hour_of_day_busiest = 0
        self.activity_by_hour_of_week_busiest = 0
        self.activity_by_year_week = {}
        
        # Blob line counts
        self.blob_line_counts = {}
        
    def collect(self):
        """Collect additional git statistics."""
        # Collect tags data
        self._collect_tags_data()
        
        # Collect revision statistics
        self._collect_revision_stats()
        
        # Collect activity statistics
        self._collect_activity_stats()
        
        # Collect blob line counts
        self._collect_blob_line_counts()
        
        return True
        
    def _collect_tags_data(self):
        """Collect tag information from the git repository."""
        # Get tags information
        tags_info = get_tags_info()
        
        # Process each tag
        for (hash, tag) in tags_info:
            # Get tag commit info
            tag_info = get_tag_commit_info(hash)
            if tag_info is None:
                continue
                
            # Extract tag date and author
            tag_date, tag_author = tag_info
            self.tags_dates[tag] = tag_date
            self.tags_authors[tag] = tag_author
            
            # Get commits for this tag
            commits = get_tag_commits(tag)
            self.tags[tag] = commits
            
    def _collect_revision_stats(self):
        """Collect revision statistics from the git repository."""
        # Get revision history
        revs = get_revision_history(self.config.start_date, self.config.commit_begin, self.config.commit_end)
        
        # Process each revision
        for rev in revs:
            # Skip empty revisions
            if rev == "":
                continue
                
            # Get revision date
            rev_date = get_rev_date(rev)
            if rev_date is None:
                continue
                
            # Extract author from revision
            # The rev string might be in the format "1752523997 2025-07-14 16:13:17 -0400 Author <email>"
            # We need to extract just the commit hash or use the timestamp
            try:
                parts = rev.split()
                if parts and parts[0].isdigit():
                    # If we have a timestamp, we can extract the author from the same string
                    if len(parts) >= 5:
                        author = ' '.join(parts[4:]).split('<')[0].strip()
                    else:
                        author = "Unknown"
                else:
                    # If we don't have a timestamp, try to use the first part as a commit hash
                    commit_hash = parts[0] if parts else rev
                    cmd = f"git log --pretty=format:'%an' -n 1 {commit_hash}"
                    author = getpipeoutput([cmd]).rstrip('\n')
                    if not author:
                        author = "Unknown"
            except Exception as e:
                logging.error(f"Error extracting author: {e}, rev: {rev[:50]}...")
                author = "Unknown"
            
            # Store revision information
            self.revisions.append(rev)
            self.rev_dates[rev] = rev_date
            self.rev_authors[rev] = author
            
    def _collect_activity_stats(self):
        """Collect activity statistics by time periods."""
        # Get commit timestamps and authors
        # Construct the git command more carefully to avoid format string issues
        log_range = getlogrange(self.config.start_date, self.config.commit_begin, self.config.commit_end, "HEAD")
        cmd = f"git log --pretty=format:'%ct %aN' {log_range}"
        logging.debug(f"Executing git command for activity stats: {cmd}")
        
        lines = getpipeoutput([cmd]).split('\n')
        
        # Process each commit
        for line in lines:
            if len(line) == 0:
                continue
                
            parts = line.split(' ', 1)
            if len(parts) != 2:
                continue
                
            try:
                # Extract timestamp and author
                (stamp, author) = (int(parts[0]), parts[1])
                
                # Update activity statistics
                self._update_activity_stats(stamp, author)
            except ValueError:
                print('Warning: unexpected line "%s"' % line)
                
    def _update_activity_stats(self, stamp, author):
        """Update activity statistics by time periods."""
        # Convert timestamp to date
        from datetime import datetime
        date = datetime.fromtimestamp(stamp)
        
        # Update activity by hour of day
        hour = date.hour
        self.activity_by_hour_of_day[hour] = self.activity_by_hour_of_day.get(hour, 0) + 1
        if self.activity_by_hour_of_day[hour] > self.activity_by_hour_of_day_busiest:
            self.activity_by_hour_of_day_busiest = self.activity_by_hour_of_day[hour]
            
        # Update activity by day of week
        weekday = date.weekday()
        self.activity_by_day_of_week[weekday] = self.activity_by_day_of_week.get(weekday, 0) + 1
        
        # Update activity by month of year
        month = date.month
        self.activity_by_month_of_year[month] = self.activity_by_month_of_year.get(month, 0) + 1
        
        # Update activity by hour of week
        hour_of_week = weekday * 24 + hour
        self.activity_by_hour_of_week[hour_of_week] = self.activity_by_hour_of_week.get(hour_of_week, 0) + 1
        if self.activity_by_hour_of_week[hour_of_week] > self.activity_by_hour_of_week_busiest:
            self.activity_by_hour_of_week_busiest = self.activity_by_hour_of_week[hour_of_week]
            
        # Update activity by year and week
        yyw = date.strftime("%Y-%W")
        self.activity_by_year_week[yyw] = self.activity_by_year_week.get(yyw, 0) + 1
        
        # Update author time statistics
        self._update_author_time_stats(author, date, hour, weekday, hour_of_week)
        
    def _update_author_time_stats(self, author, date, hour, weekday, hour_of_week):
        """Update author-specific time statistics."""
        # Skip if author is not in the authors dictionary
        if not hasattr(self, 'authors') or author not in self.authors:
            return
            
        # Initialize author time statistics if not present
        if "hour_of_day" not in self.authors[author]:
            self.authors[author]["hour_of_day"] = {}
        if "day_of_week" not in self.authors[author]:
            self.authors[author]["day_of_week"] = {}
        if "month_of_year" not in self.authors[author]:
            self.authors[author]["month_of_year"] = {}
        if "hour_of_week" not in self.authors[author]:
            self.authors[author]["hour_of_week"] = {}
            
        # Update author time statistics
        self.authors[author]["hour_of_day"][hour] = self.authors[author]["hour_of_day"].get(hour, 0) + 1
        self.authors[author]["day_of_week"][weekday] = self.authors[author]["day_of_week"].get(weekday, 0) + 1
        self.authors[author]["month_of_year"][date.month] = self.authors[author]["month_of_year"].get(date.month, 0) + 1
        self.authors[author]["hour_of_week"][hour_of_week] = self.authors[author]["hour_of_week"].get(hour_of_week, 0) + 1
        
    def _update_domain_stats(self, author, email):
        """Update domain statistics."""
        # Extract domain from email
        domain = self.get_domain_name(email)
        if domain == "":
            return
            
        # Initialize domain if not present
        if domain not in self.domains:
            self.domains[domain] = {}
            self.domains[domain]["commits"] = 0
            self.domains[domain]["authors"] = set()
            
        # Update domain statistics
        self.domains[domain]["commits"] += self.authors[author]["commits"]
        self.domains[domain]["authors"].add(author)
        
    def _collect_blob_line_counts(self):
        """Collect line counts for each blob in the repository."""
        # Get file information
        lines = getpipeoutput([
            "git ls-tree -r -z %s" % getcommitrange(self.config.commit_begin, self.config.commit_end, "HEAD", end_only=True)
        ]).split("\000")
        
        # Process files in parallel
        blobs_to_read = []
        for line in lines:
            if len(line) == 0:
                continue
                
            parts = re.split(r"\s+", line, 4)
            if len(parts) < 5:
                continue
                
            # Skip submodules
            if parts[0] == "160000" and parts[3] == "-":
                continue
                
            blob_id = parts[2]
            fullpath = parts[4]
            
            # Skip binary files
            filename = fullpath.split("/")[-1]  # strip directories
            if filename.find(".") == -1 or filename.rfind(".") == 0:
                ext = ""
            else:
                ext = filename[(filename.rfind(".") + 1):]
                
            if ext in self.config.binary_extensions:
                continue
                
            # Add blob to processing list
            blobs_to_read.append((blob_id, fullpath))
            
        # Process blobs in parallel
        if blobs_to_read:
            pool = Pool(processes=self.config.processes)
            blob_line_counts = pool.map(getnumoflinesinblob, blobs_to_read)
            pool.terminate()
            pool.join()
            
            # Update blob line counts
            for (blob_id, fullpath, count) in blob_line_counts:
                self._process_blob_line_counts(blob_id, fullpath, count)
                
    def _process_blob_line_counts(self, blob_id, fullpath, count):
        """Process blob line counts."""
        # Store blob line count
        self.blob_line_counts[blob_id] = count
        
        # Extract file extension
        filename = fullpath.split("/")[-1]  # strip directories
        ext = self._get_file_extension(filename)
        
        # Update extension line count
        if ext in self.extensions:
            self.extensions[ext]["lines"] += count
            
    def _get_file_extension(self, filename):
        """Extract file extension from filename."""
        return get_file_extension(filename, self.config.max_ext_length)
        
    def get_domain_name(self, email):
        """Get domain name from email address."""
        return get_domain_name(email)
        
    # Getter methods for statistics
    def getActivityByDayOfWeek(self):
        return self.activity_by_day_of_week

    def getActivityByHourOfDay(self):
        return self.activity_by_hour_of_day

    def getActivityByHourOfWeekBusiest(self):
        return self.activity_by_hour_of_week_busiest

    def getActivityByHourOfDayBusiest(self):
        return self.activity_by_hour_of_day_busiest

    def getActivityByHourOfWeek(self):
        return self.activity_by_hour_of_week

    def getActivityByMonthOfYear(self):
        return self.activity_by_month_of_year

    def getActivityByYearWeek(self):
        return self.activity_by_year_week

    def getBlobs(self):
        return self.blob_line_counts.keys()

    def getBlobInfo(self, blob_id):
        return self.blob_line_counts[blob_id]

    def getRevDate(self, rev):
        return self.rev_dates[rev]

    def getRevisionChangeset(self, rev):
        return None  # Placeholder for future implementation

    def getRevisions(self):
        return self.revisions

    def getTagDate(self, tag):
        return self.tags_dates[tag]

    def getTags(self):
        return self.tags.keys()

    def getTagInfo(self, tag):
        return self.tags[tag]
