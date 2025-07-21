import logging
import os
import math
from datetime import datetime, timedelta
from .git_utils import get_commits_by_date, get_comment_density_data


def calculate_ai_probability(commits_per_day, avg_lines_per_commit, avg_message_size, days_active, comment_density=None):
    """
    Calculate the probability of AI involvement based on various metrics.
    
    Args:
        commits_per_day: Average number of commits per day
        avg_lines_per_commit: Average lines changed per commit
        avg_message_size: Average commit message size in characters
        days_active: Number of active days
        comment_density: Optional. Ratio of comment lines to code lines (comments/code)
        
    Returns:
        Float between 0 and 100 representing the probability of AI involvement
    """
    # Initialize probability score
    probability = 0
    
    # 1. High commits per day suggests potential AI involvement
    # Typical human developers rarely exceed 5-6 commits per day consistently
    if commits_per_day > 8:
        probability += 35  # Very high commits per day is a strong indicator
    elif commits_per_day > 5:
        probability += 25  # Moderately high commits per day
    elif commits_per_day > 3:
        probability += 15  # Slightly elevated commits per day
    
    # 2. Very large commits (many lines changed) can indicate AI-generated code
    # But this is less important than other factors
    if avg_lines_per_commit > 500:
        probability += 15  # Very large commits
    elif avg_lines_per_commit > 200:
        probability += 10  # Moderately large commits
    elif avg_lines_per_commit > 100:
        probability += 3   # Slightly large commits
    
    # 3. AI often generates longer, more detailed commit messages
    if avg_message_size > 150:
        probability += 20  # Very detailed commit messages
    elif avg_message_size > 100:
        probability += 10  # Moderately detailed messages
    elif avg_message_size > 70:
        probability += 5   # Slightly detailed messages
    
    # 4. Consistency factor (high commits per day with few active days)
    # AI tends to generate many commits in short bursts
    if commits_per_day > 5 and days_active < 5:
        probability += 15  # High intensity in short periods
        
    # 5. High comment density can indicate AI-generated code
    # AI often generates code with more comments than human developers
    if comment_density is not None:
        if comment_density > 0.3:  # Many comments relative to code
            probability += 30
        elif comment_density > 0.2:
            probability += 20
        elif comment_density > 0.15:
            probability += 10
        elif comment_density > 0.1:
            probability += 5
    
    # 6. Apply a sigmoid function to smooth the probability between 0 and 100
    # This creates a more natural distribution and avoids extreme values
    normalized_prob = 100 / (1 + math.exp(-0.05 * (probability - 50)))
    
    # Ensure the probability is between 0 and 100
    return max(0, min(100, normalized_prob))

def analyze_author_contributions(repo, months_to_analyze=None, config=None):
    """
    Analyze and display author contribution statistics including lines added/removed.
    
    Args:
        repo: Repository object containing author statistics
        months_to_analyze: Optional number of months to analyze (None for all time)
        config: Optional configuration object containing repos_folder
    """
    if not hasattr(repo, 'stat') or not hasattr(repo.stat, 'authors') or not repo.stat.authors:
        print("\nNo author contribution data available.")
        return
    
    
    # Calculate cutoff date if months_to_analyze is specified
    cutoff_date = None
    if months_to_analyze is not None and months_to_analyze > 0:
        # Get the current date
        current_date = datetime.now()
        
        # Apply months offset if specified in config
        months_offset = 0
        if config and hasattr(config, 'months_offset'):
            months_offset = config.months_offset
            
        if months_offset > 0:
            # Move the reference point back by the offset
            current_date = current_date - timedelta(days=30 * months_offset)
            print(f"\nUsing reference point from {months_offset} months ago: {current_date.strftime('%Y-%m-%d')}")
        
        # Calculate the cutoff date from the reference point
        cutoff_date = current_date - timedelta(days=30 * months_to_analyze)
        
        if months_offset > 0:
            print(f"Analyzing contributions from {months_to_analyze} months before the reference point (from {cutoff_date.strftime('%Y-%m-%d')} to {current_date.strftime('%Y-%m-%d')})")
        else:
            print(f"\nAnalyzing contributions from the last {months_to_analyze} months (since {cutoff_date.strftime('%Y-%m-%d')})")

        
        # Get accurate commit statistics for the specified time period
        if months_offset > 0:
            logging.debug(f"Getting commit statistics from {cutoff_date.strftime('%Y-%m-%d')} to {current_date.strftime('%Y-%m-%d')}")
        else:
            logging.debug(f"Getting commit statistics since {cutoff_date.strftime('%Y-%m-%d')}")
        
        # Get the repository path
        repo_path = None
        
        # Try to get repo path from environment variable
        if 'GITSTAT_REPOS_FOLDER' in os.environ and hasattr(repo, 'id'):
            repo_path = os.path.join(os.environ['GITSTAT_REPOS_FOLDER'], repo.id)
            logging.debug(f"Using repo path from environment variable: {repo_path}")
        # Try to get repo path from config
        elif config and hasattr(config, 'repos_folder') and hasattr(repo, 'id'):
            repo_path = os.path.join(config.repos_folder, repo.id)
            logging.debug(f"Using repo path from config: {repo_path}")
        # Try to get repo path from repo object
        elif hasattr(repo, 'path'):
            repo_path = repo.path
            logging.debug(f"Using repo path from repo object: {repo_path}")
        # Try to get repo path from repo.stat
        elif hasattr(repo, 'stat') and hasattr(repo.stat, 'path'):
            repo_path = repo.stat.path
            logging.debug(f"Using repo path from repo.stat: {repo_path}")
        else:
            logging.debug("No repo path found. Using current directory.")
            repo_path = os.getcwd()
        
        # If we have an offset, we need to pass both start and end dates
        end_date = current_date if months_offset > 0 else None
        filtered_stats = get_commits_by_date(cutoff_date, end_date, repo_path)
        logging.debug(f"Found {len(filtered_stats)} authors with commits in the filtered period")
        
        # Get comment density data for the same period
        # If we have an offset, we need to pass both start and end dates
        comment_stats = get_comment_density_data(cutoff_date, end_date, repo_path)
        logging.debug(f"Found comment density data for {len(comment_stats)} authors")
        if filtered_stats:
            logging.debug("Authors in filtered stats:")
            for author in filtered_stats.keys():
                print(f"  - '{author}': {filtered_stats[author]['commits']} commits")
        else:
            logging.debug("No authors found in filtered stats")

    
    print("\n=== Author Contribution Statistics ===")
    
    # Get all authors and sort by total commits
    authors = []
    
    # If we have filtered stats from the cutoff date, use those directly
    if cutoff_date and filtered_stats:
        logging.debug(f"Using filtered stats for {len(filtered_stats)} authors")
        
        # Create author entries from filtered stats
        for author_name, filtered_data in filtered_stats.items():
            # Skip authors with no commits in the filtered period
            if filtered_data['commits'] == 0:
                continue
                
            # Get email from repo.stat.authors if available
            email = ''
            if author_name in repo.stat.authors and 'email' in repo.stat.authors[author_name]:
                email = repo.stat.authors[author_name]['email']
            
            # Use the filtered statistics
            commits = filtered_data['commits']
            lines_added = filtered_data['lines_added']
            lines_removed = filtered_data['lines_removed']
            
            # Format dates
            first_commit = datetime.fromtimestamp(filtered_data['first_commit_stamp']).strftime('%Y-%m-%d')
            last_commit = datetime.fromtimestamp(filtered_data['last_commit_stamp']).strftime('%Y-%m-%d')
            
            # Get message size if available
            avg_message_size = 0
            if author_name in repo.stat.authors:
                avg_message_size = repo.stat.authors[author_name].get('avg_message_size', 0)
            
            # Create author entry
            author_entry = {
                'name': author_name,
                'email': email,
                'commits': commits,
                'lines_added': lines_added,
                'lines_removed': lines_removed,
                'avg_lines_per_commit': (lines_added + lines_removed) / commits if commits > 0 else 0,
                'days_active': len(filtered_data['active_days']),
                'avg_commits_per_day': commits / len(filtered_data['active_days']) if filtered_data['active_days'] else 0,
                'first_commit': first_commit,
                'last_commit': last_commit,
                'avg_message_size': avg_message_size,
                'comment_density': 0  # Default value
            }
            
            # Add comment density if available
            if author_name in comment_stats:
                author_entry['comment_density'] = comment_stats[author_name]['comment_density']
                logging.debug(f"Comment density for {author_name}: {author_entry['comment_density']:.4f}")
            
            authors.append(author_entry)
    else:
        # No filtered stats, use original statistics from repo.stat.authors
        for author_name, author_data in repo.stat.authors.items():
            if 'email' not in author_data:
                continue
                
            # Use original statistics
            commits = author_data.get('commits', 0)
            lines_added = author_data.get('lines_added', 0)
            lines_removed = author_data.get('lines_removed', 0)
            avg_message_size = author_data.get('avg_message_size', 0)
            
            # Calculate metrics
            avg_lines_per_commit = (lines_added + lines_removed) / commits if commits > 0 else 0
            days_active = len(author_data.get('active_days', set()))
            days_active = max(days_active, 1)  # Ensure at least 1 day active
            avg_commits_per_day = commits / days_active if days_active > 0 else 0
            
            # Get dates
            first_commit = author_data.get('date_first', 'N/A')
            last_commit = author_data.get('date_last', 'N/A')
            
            # Create author entry
            author_entry = {
                'name': author_name,
                'email': author_data.get('email', ''),
                'commits': commits,
                'lines_added': lines_added,
                'lines_removed': lines_removed,
                'avg_lines_per_commit': avg_lines_per_commit,
                'days_active': days_active,
                'avg_commits_per_day': avg_commits_per_day,
                'first_commit': first_commit,
                'last_commit': last_commit,
                'avg_message_size': avg_message_size,
                'comment_density': 0  # Default value
            }
            
            authors.append(author_entry)
        
    # Sort authors by total commits (descending)
    authors.sort(key=lambda x: x['commits'], reverse=True)
    
    # Get comment density data if not already fetched
    if not cutoff_date or not comment_stats:
        # If we have an offset, we need to pass both start and end dates
        end_date = current_date if months_offset > 0 else None
        comment_stats = get_comment_density_data(cutoff_date, end_date, repo_path)
        logging.debug(f"Found comment density data for {len(comment_stats)} authors")
    
    # Update comment density for all authors
    for author_entry in authors:
        if author_entry['name'] in comment_stats:
            author_entry['comment_density'] = comment_stats[author_entry['name']]['comment_density']
            logging.debug(f"Comment density for {author_entry['name']}: {author_entry['comment_density']:.4f}")
    
    # Calculate AI probability for each author
    for author_entry in authors:
        author_entry['ai_probability'] = calculate_ai_probability(
            commits_per_day=author_entry['avg_commits_per_day'],
            avg_lines_per_commit=author_entry['avg_lines_per_commit'],
            avg_message_size=author_entry['avg_message_size'],
            days_active=author_entry['days_active'],
            comment_density=author_entry.get('comment_density', None)
        )
    
    # Sort authors by total commits (descending)
    authors.sort(key=lambda x: x['commits'], reverse=True)
    
    # Print summary
    print(f"\nTotal authors with commit history: {len(authors)}")
    
    if not authors:
        return
    
    # Calculate total project duration in days
    if authors:
        first_date = min(a['first_commit'] for a in authors if a['first_commit'] != 'N/A')
        last_date = max(a['last_commit'] for a in authors if a['last_commit'] != 'N/A')
        
        try:
            # Use the imported datetime directly, not through the module
            first_date = datetime.strptime(first_date, '%Y-%m-%d')
            last_date = datetime.strptime(last_date, '%Y-%m-%d')
            total_days = (last_date - first_date).days + 1  # +1 to include both dates
        except (ValueError, TypeError):
            total_days = 1  # Fallback to avoid division by zero
    else:
        total_days = 1  # Fallback to avoid division by zero
    
    # Calculate column widths based on data
    max_name_len = max(len(author['name']) for author in authors[:20])
    max_name_len = min(max(max_name_len, len("Author")), 30)  # Cap at 30 chars
    
    print("\nDetailed Author Statistics:")
    print("-" * 160)
    header = (
        f"{'Author':<{max_name_len}} "
        f"{'Commits':>7} "
        f"{'Lines +':>10} "
        f"{'Lines -':>10} "
        f"{'Avg Lines':>10} "
        f"{'Days':>5} "
        f"{'Days %':>7} "
        f"{'Commits/Day':>12} "
        f"{'Msg Size':>9} "
        f"{'Comments/Code':>14} "
        f"{'AI Prob':>12}"
    )
    print(header)
    print("-" * 160)
    
    # Print each author's stats
    for author in authors[:20]:  # Limit to top 20 authors
        days_active = author['days_active']
        days_percent = (days_active / total_days * 100) if total_days > 0 else 0
        days_display = f"{days_active} ({days_percent:.1f}%)"
        
        # Truncate name if needed
        name_display = author['name'][:max_name_len]
        
        # Format numbers with thousands separators
        commits = f"{author['commits']:,}"
        lines_added = f"{author['lines_added']:,}"
        lines_removed = f"{author['lines_removed']:,}"
        
        # Calculate days percentage
        days_percentage = (author['days_active'] / total_days) * 100 if total_days > 0 else 0
        
        # Format the row
        row = (
            f"{name_display:<{max_name_len}} "
            f"{commits:>7} "
            f"{lines_added:>10} "
            f"{lines_removed:>10} "
            f"{author['avg_lines_per_commit']:>10,.1f} "
            f"{author['days_active']:>5} "
            f"{days_percentage:>7.1f}% "
            f"{author['avg_commits_per_day']:>12.2f} "
            f"{author['avg_message_size']:>9.1f} "
            f"{author['comment_density']:>14.3f} "
            f"{author['ai_probability']:>12.1f}% "
        )
        
        print(row)
    
    if len(authors) > 20:
        print(f"\n... and {len(authors) - 20} more authors (total: {len(authors)})")
    
    # Print summary statistics
    total_commits = sum(a['commits'] for a in authors)
    total_lines_added = sum(a['lines_added'] for a in authors)
    total_lines_removed = sum(a['lines_removed'] for a in authors)
    
    # Note: We're using the project duration calculated earlier, not just max active days
    # This ensures 'Days %' is correctly calculated as percentage of the whole analysis period
    
    print("\n=== Summary ===")
    print(f"Total commits: {total_commits:,}")
    print(f"Total lines added: {total_lines_added:,}")
    print(f"Total lines removed: {total_lines_removed:,}")
    print(f"Net lines changed: {total_lines_added - total_lines_removed:,}")
    print(f"Project duration: {total_days} days")
    
    # Calculate and print busiest authors
    if authors:
        print("\nTop contributors by commits:")
        for i, author in enumerate(authors[:5]):
            print(f"  {i+1}. {author['name']} ({author['commits']:,} commits, {author['lines_added']:,} lines added)")
        
        # Calculate a productivity score based on both commits per day and lines changed per day
        for author in authors:
            lines_changed = author['lines_added'] + author['lines_removed']
            lines_per_day = lines_changed / author['days_active'] if author['days_active'] > 0 else 0
            # Normalize both metrics to avoid one dominating the other
            # Use a weighted combination of commits per day and lines changed per day
            author['productivity_score'] = (author['avg_commits_per_day'] * 0.5) + (lines_per_day / 100 * 0.5)
        
        print("\nMost productive authors (commits and code changes per day):")
        productive = sorted(authors, key=lambda x: x['productivity_score'], reverse=True)[:3]
        for i, author in enumerate(productive):
            lines_changed = author['lines_added'] + author['lines_removed']
            lines_per_day = lines_changed / author['days_active'] if author['days_active'] > 0 else 0
            print(f"  {i+1}. {author['name']} ({author['avg_commits_per_day']:.2f} commits/day, {lines_per_day:.1f} lines/day)")

        
        # Add section for authors with highest AI involvement probability
        print("\n=== AI Involvement Analysis ===")
        print("Authors with highest probability of AI assistance:")
        ai_authors = sorted(authors, key=lambda x: x['ai_probability'], reverse=True)
        
        # Print table header for AI analysis
        print("\n" + "-" * 120)
        ai_header = (
            f"{'Author':<{max_name_len}} "
            f"{'AI Prob':>12} "
            f"{'Commits':>7} "
            f"{'Lines +':>10} "
            f"{'Lines -':>10} "
            f"{'Avg Lines':>10} "
            f"{'Days':>5} "
            f"{'Days %':>7} "
            f"{'Commits/Day':>12} "
            f"{'Msg Size':>9} "
            f"{'Comments/Code':>14}"
        )
        print(ai_header)
        print("-" * 120)
        
        # Print top 5 authors with highest AI probability
        for author in ai_authors[:5]:
            name_display = author['name'][:25]  # Truncate name if needed
            commits = f"{author['commits']:,}"  # Format numbers with thousands separators
            total_lines = author['lines_added'] + author['lines_removed']
            
            # Calculate days percentage
            days_percentage = (author['days_active'] / total_days) * 100 if total_days > 0 else 0
            
            # Format the row for AI analysis
            ai_row = (
                f"{name_display:<{max_name_len}} "
                f"{author['ai_probability']:>12.1f}% "
                f"{commits:>7} "
                f"{author['lines_added']:>10,} "
                f"{author['lines_removed']:>10,} "
                f"{author['avg_lines_per_commit']:>10.1f} "
                f"{author['days_active']:>5} "
                f"{days_percentage:>7.1f}% "
                f"{author['avg_commits_per_day']:>12.2f} "
                f"{author['avg_message_size']:>9.1f} "
                f"{author['comment_density']:>14.3f}"
            )
            print(ai_row)
        
        print("-" * 120)
        print("\nAI Probability Factors:")
        print("  - High commits per day (>8 commits/day is unusual for manual coding)")
        print("  - Very large commits (>500 lines/commit suggests automated code generation)")
        print("  - Detailed commit messages (>150 chars suggests AI-generated descriptions)")
        print("  - High activity in short periods (many commits in few days)")
        print("  - Higher comment density (AI tends to write more comments per line of code)")
        print("\nNote: This analysis is based on statistical patterns and may not be 100% accurate.")
