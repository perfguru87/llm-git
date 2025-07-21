import datetime

from .data_collector import DataCollector
from .git_stat_collector import GitStatCollector
from .git_stat_ext_collector import GitStatExtCollector


class GitDataCollector(DataCollector):
    """Collects data from a git repository.
    
    This class serves as an entry point for git statistics collection,
    using both GitStatCollector for essential statistics used by the analyzer
    and GitStatExtCollector for additional statistics.
    """

    def __init__(self, conf):
        DataCollector.__init__(self, conf)
        
        # Initialize the essential statistics collector
        self.stat_collector = GitStatCollector(conf)
        
        # Initialize the extended statistics collector
        self.ext_collector = GitStatExtCollector(conf)
        
        # Initialize attributes to store combined statistics
        self.extensions = {}
        self.total_authors = 0
        self.total_commits = 0
        self.total_files = 0
        self.total_lines = 0
        self.total_size = 0
        self.authors = {}
        self.first_commit_stamp = 0
        self.last_commit_stamp = 0
        self.last_active_day = None
        self.active_days = set()
        self.activity_by_hour_of_day = {}
        self.activity_by_day_of_week = {}
        self.activity_by_month_of_year = {}
        self.activity_by_hour_of_week = {}
        self.activity_by_hour_of_day_busiest = 0
        self.activity_by_hour_of_week_busiest = 0
        self.activity_by_year_week = {}
        self.authors_by_commits = []
        self.files_by_stamp = {}
        self.lines_added_by_month = {}
        self.lines_added_by_year = {}
        self.lines_removed_by_month = {}
        self.lines_removed_by_year = {}
        self.first_active_day = None
        self.last_active_day = None
        self.domains = {}
        self.total_lines_added = 0
        self.total_lines_removed = 0
        self.changes_by_date = {}
        self.changes_by_date_by_author = {}
        self.blob_line_counts = {}
        self.tags = {}
        self.tags_dates = {}
        self.tags_authors = {}
        self.revisions = []
        self.rev_authors = {}
        self.rev_dates = {}
        self.cache = {}
        self.loc = 0

    def collect(self):
        """Collect data from the git repository.
        
        This method delegates the collection of statistics to the specialized collectors
        and then combines their results.
        """
        DataCollector.collect(self)

        # Collect essential statistics used by the analyzer
        self.stat_collector.collect()
        
        # Collect additional statistics only if extended_stats is enabled
        if hasattr(self.config, 'extended_stats') and self.config.extended_stats:
            self.ext_collector.collect()
        
        # Combine statistics from both collectors
        self._combine_statistics()
        
        return True
        
    def _combine_statistics(self):
        """Combine statistics from both collectors."""
        # Basic statistics
        self.total_authors = self.stat_collector.total_authors
        self.total_commits = self.stat_collector.total_commits
        self.total_files = self.stat_collector.total_files
        self.total_lines = self.stat_collector.total_lines
        self.total_size = self.stat_collector.total_size
        self.loc = self.stat_collector.loc
        self.total_lines_added = self.stat_collector.total_lines_added
        self.total_lines_removed = self.stat_collector.total_lines_removed
        
        # Author statistics
        self.authors = self.stat_collector.authors
        self.authors_by_commits = self.stat_collector.authors_by_commits
        
        # Time-based statistics
        self.first_commit_stamp = self.stat_collector.first_commit_stamp
        self.last_commit_stamp = self.stat_collector.last_commit_stamp
        self.active_days = self.stat_collector.active_days
        self.last_active_day = self.stat_collector.last_active_day
        
        # Lines statistics
        self.lines_added_by_month = self.stat_collector.lines_added_by_month
        self.lines_added_by_year = self.stat_collector.lines_added_by_year
        self.lines_removed_by_month = self.stat_collector.lines_removed_by_month
        self.lines_removed_by_year = self.stat_collector.lines_removed_by_year
        self.changes_by_date = self.stat_collector.changes_by_date
        self.changes_by_date_by_author = self.stat_collector.changes_by_date_by_author
        
        # File statistics
        self.extensions = self.stat_collector.extensions
        self.files_by_stamp = self.stat_collector.files_by_stamp
        
        # Domain statistics
        self.domains = self.stat_collector.domains if hasattr(self.stat_collector, 'domains') else {}
        
        # Extended statistics - only copy if extended stats were collected
        if hasattr(self.config, 'extended_stats') and self.config.extended_stats:
            self.tags = self.ext_collector.tags
            self.tags_dates = self.ext_collector.tags_dates
            self.tags_authors = self.ext_collector.tags_authors
            self.revisions = self.ext_collector.revisions
            self.rev_authors = self.ext_collector.rev_authors
            self.rev_dates = self.ext_collector.rev_dates
            self.activity_by_hour_of_day = self.ext_collector.activity_by_hour_of_day
            self.activity_by_day_of_week = self.ext_collector.activity_by_day_of_week
            self.activity_by_month_of_year = self.ext_collector.activity_by_month_of_year
            self.activity_by_hour_of_week = self.ext_collector.activity_by_hour_of_week
            self.activity_by_hour_of_day_busiest = self.ext_collector.activity_by_hour_of_day_busiest
            self.activity_by_hour_of_week_busiest = self.ext_collector.activity_by_hour_of_week_busiest
            self.activity_by_year_week = self.ext_collector.activity_by_year_week
            self.blob_line_counts = self.ext_collector.blob_line_counts
        
    def get_domain_name(self, email):
        """Get domain name from email address."""
        return email.split('@', 1)[1] if '@' in email else ''
        
    def refine(self):
        """Refine collected data for analysis.
        
        This method is called after collection to prepare the data for analysis.
        The actual refinement is now handled by the GitStatCollector.
        """
        # Call refine on the stat collector to ensure data is properly prepared
        self.stat_collector.refine()
        
    # Getter methods for statistics - these delegate to the appropriate collector
    def getActiveDays(self):
        return self.active_days

    def getAuthorInfo(self, author):
        return self.authors[author]

    def getAuthors(self, limit=None):
        return self.stat_collector.getAuthors(limit)

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
        
    # Extended statistics getters
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
