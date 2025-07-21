import datetime
import os

class CollectorConfig:
    def __init__(self):
        self.max_domains = 10
        self.max_ext_length = 10
        self.style = "gitstats.css"
        self.max_authors = 20
        self.authors_top = 5
        self.commit_begin = ""
        self.commit_end = "HEAD"
        self.linear_linestats = 1
        self.repo_id = ""
        self.processes = 8
        self.start_date = datetime.date.today().strftime("%Y-%m-%d")
        self.days_in_period = 0
        self.binary_extensions = [".dat", ".bin", ".exe", ".dll", ".so", ".a", ".o", ".obj", ".lib", ".pyc", ".pyd"]
        self.extended_stats = False

    def calculate_start_date(self, month_to_analyze, months_offset=0):
        today = datetime.date.today()
        
        # Apply the offset first (move back in time)
        if months_offset > 0:
            today = today - datetime.timedelta(days=30 * months_offset)
            
        # Then calculate the start date from the offset point
        start_date = today - datetime.timedelta(days=30 * month_to_analyze)
        self.start_date = start_date.strftime("%Y-%m-%d")
        self.days_in_period = 30 * month_to_analyze
        
    def set_cutoff_date(self, cutoff_date):
        """Set the cutoff date directly from a datetime object.
        
        Args:
            cutoff_date: A datetime object representing the cutoff date
        """
        self.start_date = cutoff_date.strftime("%Y-%m-%d")
        # Calculate days between cutoff date and today
        today = datetime.date.today()
        delta = today - cutoff_date.date()
        self.days_in_period = delta.days


class ToolConfig:
    def __init__(self, cwd):
        self.cwd = cwd
        self.update_git = False
        self.update_github = False
        self.cache_folder = ""
        self.repos_folder = ""
        self.months_to_analyze = 12
        self.months_offset = 0
        self.analyze_performance = 0
        self.do_update = False
        self.url = ""
        self.local_repo = ""
        self.excel_file = ""
        self.text_file = ""
        self.output = ""
        self.git_download_only = False
        self.skip_existing = False
        self.update_github_anon_only = False
        self.extended_stats = False

    def dump(self):
        return f"ToolConfig(cwd={self.cwd}, update_git={self.update_git}, update_github={self.update_github}, cache_folder={self.cache_folder}, repos_folder={self.repos_folder}, months_to_analyze={self.months_to_analyze}, months_offset={self.months_offset}, analyze_performance={self.analyze_performance}, do_update={self.do_update}, url={self.url}, local_repo={self.local_repo}, excel_file={self.excel_file}, output={self.output}, extended_stats={self.extended_stats})"

    def set_url(self, url): 
        self.url = url
        
    def set_local_repo(self, local_repo):
        self.local_repo = local_repo
        # When using local repo, disable GitHub operations
        self.update_github = False
        # By default, don't collect extended stats for local repos
        # This can be overridden with the -E flag

    def set_update_mode(self): 
        self.do_update = True

    
    def set_update_all(self): 
        self.update_github = True
        self.update_git = True

    def set_update_github(self): 
        self.update_github = True
        self.update_git = False

    def set_update_git(self): 
        self.update_github = False
        self.update_git = True

    def set_cache_folder(self, cache_folder):
        self.cache_folder = os.path.join(self.cwd, cache_folder)

    def set_repos_folder(self, repos_folder):
        self.repos_folder = os.path.join(self.cwd, repos_folder)

    def set_months_to_analyze(self, months): 
        self.months_to_analyze = months
        
    def set_months_offset(self, offset):
        self.months_offset = offset
        
    def set_analyze_performance(self, months):
        self.analyze_performance = months
    
    def set_excel_file(self, excel_file):
        self.excel_file = excel_file

    def set_text_file(self, text_file): 
        self.text_file = text_file

    def set_output(self, output): 
        self.output = output
    
    def set_git_download_only(self, git_download_only): 
        self.git_download_only = git_download_only

    def set_skip_existing(self, skip_existing): 
        self.skip_existing = skip_existing

    def set_update_github_anon_only(self, update_github_anon_only): 
        self.update_github_anon_only = update_github_anon_only
