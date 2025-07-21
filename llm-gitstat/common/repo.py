import logging
import requests

from common.utils import getkeyssortedbyvaluekey

class Organization:
    def __init__(self, id, login, description):
        self.id = id
        self.login = login
        self.description = description


class Contributor:
    def __init__(self, id, login):
        self.login = login
        self.id = id
        self.type = ""
        self.contributions = 0
        self.company = ""
        self.location = ""
        self.organizations = {}
        self.name = ""
        self.bio = ""
        self.email = ""
        self.public_repos = 0
        self.followers = 0
        self.following = 0
        self.created_at = ""
        self.within_repo_org = False


class RepoInformation:
    def __init__(self, owner, name, url):
        self.id = f"{owner}_{name}"
        self.owner = owner
        self.name = name
        self.url = url
        self.stat = {}
        self.owner_login = ""
        self.private = False
        self.fork = False
        self.forks_count = 0
        self.stargazers_count = 0
        self.watchers_count = 0
        self.subscribers_count = 0
        self.default_branch = ""
        self.open_issues_count = 0
        self.topics = []
        self.license_key = ""
        self.license_name = ""
        self.license_spdx_id = ""
        self.organization_login = ""
        self.description = ""
        self.created_at = ""
        self.updated_at = ""
        self.size = 0
        self.language = ""
        self.network_count = 0
        self.has_issues = False
        self.has_projects = False
        self.has_downloads = False
        self.has_wiki = False
        self.has_pages = False
        self.has_discussions = False
        self.contributors = {}
        

    def set_stat_data(self, stat):
        self.stat = stat

    def get_license_id(self):
        if hasattr(self, 'license_spdx_id'):
            if self.license_spdx_id == "NOASSERTION":
                return self.license_name
            return self.license_spdx_id
        return self.license_name

    def get_contributors(self):
        total_contributors = len(self.contributors)
        total_users = 0
        total_contributions = 0
        org_contributors_count = 0

        active_users_emails = []
        for author in self.stat.authors:
            if 'email' in self.stat.authors[author]:
                active_users_emails.append(self.stat.authors[author]['email'])

        authors_in_contributors = 0
        authors_in_users = 0
        authors_in_users_within_org = 0
        for c in self.contributors:
            cont = self.contributors[c]
            total_contributions += cont.contributions
            if cont.within_repo_org:
                    org_contributors_count += 1

            if cont.type == 'User':
                total_users += 1
            
            if cont.email in active_users_emails:
                authors_in_contributors += 1
                if cont.type == 'User':
                    authors_in_users += 1
                    if cont.within_repo_org:
                        authors_in_users_within_org += 1    

        sorted_by_contributions = sorted(self.contributors.items(), key=lambda item: item[1].contributions, reverse=True)

        top1_contributor = "N/A"
        top2_contributor = "N/A"
        top3_contributor = "N/A"
        if len(sorted_by_contributions) >= 3 and total_contributions > 0:
            count0 = 100*sorted_by_contributions[0][1].contributions / total_contributions
            count1 = 100*sorted_by_contributions[1][1].contributions / total_contributions
            count2 = 100*sorted_by_contributions[2][1].contributions / total_contributions
            top1_contributor = f"{sorted_by_contributions[0][0]}({count0:.2f})"
            top2_contributor = f"{sorted_by_contributions[1][0]}({count1:.2f})"
            top3_contributor = f"{sorted_by_contributions[2][0]}({count2:.2f})"

        return {"total_contributors": total_contributors,
                "total_users": total_users, 
                "total_anon": total_contributors- total_users, 
                "authors_in_contributors": authors_in_contributors, 
                "authors_in_users": authors_in_users, 
                "total_contributions": total_contributions,
                "top1_contributor": top1_contributor,
                "top2_contributor": top2_contributor,
                "top3_contributor": top3_contributor}

    def get_active_score(self):
        if not hasattr(self.stat, 'active_days'):
            return "0"
        active_days = len(self.stat.active_days)
        days_in_period = 12 * 30
        #logging.warning(f" days_in_period : {days_in_period}")
        if hasattr(self.stat.config, 'days_in_period'):
            days_in_period = self.stat.config.days_in_period
            #logging.warning(f"Using days_in_period from config: {days_in_period}")
        active_days_rate_per_period = "0"
        if days_in_period > 0:
            active_days_rate_per_period = f"{(active_days / days_in_period):.2f}"

        if active_days > days_in_period + 10: 
            sorted_list = sorted(self.stat.active_days)
            unique_set = set(sorted_list)
            logging.warning(f"Active days: {active_days} is greater than days in period: {days_in_period}, uniquest: {len(unique_set)}")
            logging.warning(f"Check the configuration of the repo: {self.id}")
            logging.warning(f"Active days: {sorted_list}")
            raise ValueError("Active days greater than days in period")
        return active_days_rate_per_period

    
    def get_contributors_companies(self):
        companies = {}
        total_contributors = 0
        for c in self.contributors:
            if self.contributors[c].type == 'User':
                total_contributors += 1
                if self.contributors[c].company not in companies:
                    companies[self.contributors[c].company] = 1
                else:
                    companies[self.contributors[c].company] = companies[self.contributors[c].company] + 1

        if total_contributors > 0:
            for key, value in companies.items():
                companies[key] = 100 * value / total_contributors
        
        sorted_companies = sorted(companies.items(), key=lambda x: x[1], reverse=True)
        top_3 = sorted_companies[:3]
        return ', '.join([f"{company}({percent:.2f}%)" for company, percent in top_3])
    

    def get_top3_domains(self):
        if not hasattr(self.stat, 'domains'):
            return "N/A", "N/A", "N/A"
        sorted = getkeyssortedbyvaluekey(self.stat.domains, "commits", True)
        if len(sorted) >= 3 and self.stat.total_commits > 0:
            count0 = self.stat.domains[sorted[0]]["commits"] / self.stat.total_commits
            count1 = self.stat.domains[sorted[1]]["commits"] / self.stat.total_commits
            count2 = self.stat.domains[sorted[2]]["commits"] / self.stat.total_commits
            return f"{sorted[0]}({count0:.2f})", f"{sorted[1]}({count1:.2f})", f"{sorted[2]}({count2:.2f})"

        return "N/A", "N/A", "N/A"
    
    def get_top3_files(self):
        if not hasattr(self.stat, 'extensions'):
            return "N/A", "N/A", "N/A"
        sorted = getkeyssortedbyvaluekey(self.stat.extensions, "files", True)
        if len(sorted) >= 3 and self.stat.total_files > 0:
            count0 = self.stat.extensions[sorted[0]]["files"] / self.stat.total_files
            count1 = self.stat.extensions[sorted[1]]["files"] / self.stat.total_files
            count2 = self.stat.extensions[sorted[2]]["files"] / self.stat.total_files
            return f"{sorted[0]}({count0:.2f})", f"{sorted[1]}({count1:.2f})", f"{sorted[2]}({count2:.2f})"

        return "N/A", "N/A", "N/A"

    def populate_info(self, info):
        #self.info = info
        self.owner_login = info.get('owner', {}).get('login', '')
        self.private = info.get('private', False)
        self.fork = info.get('fork', False)
        self.forks_count = info.get('forks_count', 0)
        self.stargazers_count = info.get('stargazers_count', 0)
        self.watchers_count = info.get('watchers_count', 0)
        self.default_branch = info.get('default_branch', '')
        self.open_issues_count = info.get('open_issues_count', 0)
        self.topics = info.get('topics', [])
        self.subscribers_count = info.get('subscribers_count', 0)
        self.license_key = "N/A"
        self.license_name = "N/A"
        self.license_spdx_id = "N/A"
        if info.get('license'):
            self.license_key = info.get('license', {}).get('key', '')
            self.license_name = info.get('license', {}).get('name', '')        
            self.license_spdx_id = info.get('license', {}).get('spdx_id', '')
        self.organization_login = info.get('organization', {}).get('login', '')
        self.description = info.get('description', '')
        self.created_at = info.get('created_at', '')
        self.updated_at = info.get('updated_at', '')
        self.size = info.get('size', 0)
        self.language = info.get('language', '')
        self.network_count = info.get('network_count', 0)
        self.has_issues = info.get('has_issues', False)
        self.has_projects = info.get('has_projects', False)
        self.has_downloads = info.get('has_downloads', False)
        self.has_wiki = info.get('has_wiki', False)
        self.has_pages = info.get('has_pages', False)
        self.has_discussions = info.get('has_discussions', False)

    
    def populate_user_info(self, user_info, orgs):
        if user_info.get('login'):
            contributor = self.contributors.get(user_info['login'], None)
            if contributor is None:
                contributor = Contributor(user_info['id'], user_info['login'])
            contributor.name = user_info.get('name', '')
            contributor.bio = user_info.get('bio', '')
            contributor.company = user_info.get('company', '')
            contributor.location = user_info.get('location', '')
            contributor.email = user_info.get('email', '')
            contributor.public_repos = user_info.get('public_repos', 0)
            contributor.followers = user_info.get('followers', 0)
            contributor.following = user_info.get('following', 0)
            contributor.created_at = user_info.get('created_at', '')
            contributor.organizations = [Organization(org['id'], org['login'], org['description']) for org in orgs]

            if self.organization_login in [org.login for org in contributor.organizations]: 
                contributor.within_repo_org = True
            self.contributors[contributor.login] = contributor

    def populate_contributors(self, contributors, anon_only=False):
        if anon_only:
            logging.info("Resetting info about anonymous contributors ")
            users_only = {}
            for contributor in self.contributors:
                if not hasattr(self.contributors[contributor], 'type'):
                    old_contributor = self.contributors[contributor]
                    new_contributor = Contributor(self.contributors[contributor].id, self.contributors[contributor].login)
                    new_contributor.type = "User"
                    new_contributor.contributions = old_contributor.contributions
                    new_contributor.company = old_contributor.company
                    new_contributor.location = old_contributor.location
                    new_contributor.organizations = old_contributor.organizations
                    new_contributor.name = old_contributor.name
                    new_contributor.bio = old_contributor.bio
                    new_contributor.email = old_contributor.email
                    new_contributor.public_repos = old_contributor.public_repos
                    new_contributor.followers = old_contributor.followers
                    new_contributor.following = old_contributor.following
                    new_contributor.created_at = old_contributor.created_at
                    new_contributor.within_repo_org = old_contributor.within_repo_org
                    users_only[contributor] = new_contributor  
                elif self.contributors[contributor].type == "User":
                    users_only[contributor] = self.contributors[contributor]
            logging.info(f"Total was: {len(self.contributors)}, Users only: {len(users_only)}")
            self.contributors = users_only


        for contributor in contributors:
            type = contributor.get('type', '')
            if type == 'User' and not anon_only:
                contributor_obj = Contributor(contributor['id'], contributor['login'])
                contributor_obj.contributions = contributor['contributions']
                contributor_obj.type = type
                self.contributors[contributor['login']] = contributor_obj
            elif type == 'Anonymous':
                contributor_obj = Contributor(contributor['email'], contributor['name'])
                contributor_obj.contributions = contributor['contributions']
                contributor_obj.type = type
                contributor_obj.name = contributor['name']
                contributor_obj.email = contributor['email']
                self.contributors[contributor_obj.email] = contributor_obj
        logging.info(f"Total contributors: {len(self.contributors)}")

    def dump_info(self):
        return f"Repo: {self.name}, Owner: {self.owner}, URL: {self.url}, Private: {self.private}, Fork: {self.fork}, " \
                f"Forks: {self.forks_count}, Stargazers: {self.stargazers_count}, Watchers: {self.watchers_count}, " \
                f"Subscribers: {self.subscribers_count}, Default Branch: {self.default_branch}, " \
                f"Open Issues: {self.open_issues_count}, Topics: {self.topics}, License: {self.license_name} ({self.license_key}), " \
                f"Organization: {self.organization_login} - {self.description}, Created At: {self.created_at}, " \
                f"Updated At: {self.updated_at}, Size: {self.size}, Language: {self.language}, " \
                f"Network Count: {self.network_count}, Has Issues: {self.has_issues}, Has Projects: {self.has_projects}, " \
                f"Has Downloads: {self.has_downloads}, Has Wiki: {self.has_wiki}, Has Pages: {self.has_pages}, " \
                f"Has Discussions: {self.has_discussions}"\
                f"Contributors: {self.contributors}" \
                f"Stat: {self.stat.dumpJson() if self.stat else 'No stats available'}"  
    
    def print_summary(self):
        logging.info(f"total_loc_for_period: {self.stat.getTotalLOC()}")
        logging.info(f"total_loc: {self.stat.loc}")
        logging.info(self.stat.domains)
        logging.info(f"first_commit_date: {self.stat.getFirstCommitDate()}")
        logging.info(f"last_commit_date: {self.stat.getLastCommitDate()}")
        logging.info(f"total_commits: {self.stat.getTotalCommits()}")
        logging.info(f"total_authors: {self.stat.getTotalAuthors()}")
        logging.info(f"extensions: {self.stat.extensions}")
        

