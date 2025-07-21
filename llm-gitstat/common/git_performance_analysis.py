#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import logging
import subprocess
from datetime import datetime, timedelta
import math
from collections import defaultdict
import re

from common.git_utils import get_commits_by_date, get_comment_density_data
from common.stat_authors import calculate_ai_probability

def analyze_performance_over_time(repo, months_to_analyze=12, config=None):
    """
    Analyze author performance over time, showing monthly statistics.
    
    Args:
        repo: Repository object containing author statistics
        months_to_analyze: Number of months to analyze (default: 12)
        config: Optional configuration object containing repos_folder
    """
    if not hasattr(repo, 'stat') or not hasattr(repo.stat, 'authors') or not repo.stat.authors:
        print("\nNo author contribution data available.")
        return
    
    print(f"\n=== Performance Analysis Over Time (Last {months_to_analyze} Months) ===")
    
    # Get the repository path
    repo_path = None
    
    # Try to get repo path from environment variable
    if 'GITSTAT_REPOS_FOLDER' in os.environ and hasattr(repo, 'id'):
        repo_path = os.path.join(os.environ['GITSTAT_REPOS_FOLDER'], repo.id)
        logging.debug(f"Using repo path from environment variable: {repo_path}")
    # Try to get repo path from config
    elif config and hasattr(config, 'repos_folder') and hasattr(repo, 'id'):
        # For local repositories, use the repo name directly without any prefix
        if hasattr(config, 'local_repo') and config.local_repo:
            repo_path = os.path.join(config.repos_folder, config.local_repo)
            logging.debug(f"Using local repo path from config: {repo_path}")
        else:
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
    
    # Get current date
    current_date = datetime.now()
    
    # Dictionary to store monthly stats for each author
    author_monthly_stats = {}
    
    # Analyze each month
    for month_offset in range(months_to_analyze, 0, -1):
        # Calculate start and end dates for this month
        end_date = current_date - timedelta(days=30 * (month_offset - 1))
        start_date = current_date - timedelta(days=30 * month_offset)
        
        month_label = start_date.strftime("%Y-%m")
        logging.debug(f"Analyzing month: {month_label} ({start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')})")
        
        # Get commit stats for this month
        monthly_stats = get_commits_by_date(start_date, end_date, repo_path)
        
        # Get comment density data for this month
        comment_stats = get_comment_density_data(start_date, end_date, repo_path)
        
        # Process each author's stats for this month
        for author_name, stats in monthly_stats.items():
            if author_name not in author_monthly_stats:
                author_monthly_stats[author_name] = {}
            
            # Calculate days in this period
            days_in_period = (end_date - start_date).days
            if days_in_period <= 0:
                days_in_period = 1
            
            # Calculate commits per day
            commits = stats.get('commits', 0)
            commits_per_day = commits / days_in_period
            
            # Calculate lines changed per day
            lines_added = stats.get('lines_added', 0)
            lines_removed = stats.get('lines_removed', 0)
            lines_changed = lines_added + lines_removed
            lines_changed_per_day = lines_changed / days_in_period
            
            # Get comment density
            comment_density = 0
            if author_name in comment_stats:
                comment_density = comment_stats[author_name].get('comment_density', 0)
            
            # Calculate average message size
            avg_message_size = 0
            if 'message_sizes' in stats and stats['message_sizes'] and commits > 0:
                avg_message_size = sum(stats['message_sizes']) / commits
            
            # Calculate AI probability with adjusted parameters for monthly data
            # For monthly data, we need to adjust some thresholds since the time period is shorter
            # This helps align monthly probabilities with the overall probability
            
            # For monthly analysis, commits_per_day is naturally higher (concentrated activity)
            # and days_active is naturally lower (fewer days in a month)
            adjusted_commits_per_day = commits_per_day * 0.7  # Scale down to match overall pattern
            
            # For short periods, even a few active days is significant
            adjusted_days_active = min(days_in_period, stats.get('days_active', 0) * 3)
            
            ai_probability = calculate_ai_probability(
                commits_per_day=adjusted_commits_per_day,
                avg_lines_per_commit=lines_changed / commits if commits > 0 else 0,
                avg_message_size=avg_message_size,
                days_active=adjusted_days_active,
                comment_density=comment_density
            )
            
            # Store monthly stats
            author_monthly_stats[author_name][month_label] = {
                'commits': commits,
                'commits_per_day': commits_per_day,
                'lines_changed': lines_changed,
                'lines_changed_per_day': lines_changed_per_day,
                'ai_probability': ai_probability,
                'comment_density': comment_density
            }
    
    # Display performance charts for top authors
    display_performance_charts(author_monthly_stats, months_to_analyze)

def display_performance_charts(author_monthly_stats, months_to_analyze):
    """
    Display performance charts for top authors.
    
    Args:
        author_monthly_stats: Dictionary with author stats by month
        months_to_analyze: Number of months analyzed
    """   
    # Print legend once at the beginning
    print("Legend:")
    print("  * = Very low AI probability (<25%)")
    print("  o = Low AI probability (25-49%)")
    print("  a = Medium AI probability (50-74%)")
    print("  A = High AI probability (≥75%)")
    print("  Y-axis: Combined performance score (40% commits/day + 60% lines/day)")
    print("  X-axis: Months (last two digits)")
    print()
    # Calculate average AI probability and total commits for each author
    author_stats = {}
    for author, monthly_data in author_monthly_stats.items():
        total_commits = sum(data.get('commits', 0) for data in monthly_data.values())
        
        # Calculate weighted average AI probability based on commits in each month
        total_weighted_prob = 0
        total_weight = 0
        for month, data in monthly_data.items():
            commits = data.get('commits', 0)
            if commits > 0:
                total_weighted_prob += data.get('ai_probability', 0) * commits
                total_weight += commits
        
        avg_ai_prob = total_weighted_prob / total_weight if total_weight > 0 else 0
        
        author_stats[author] = {
            'total_commits': total_commits,
            'avg_ai_prob': avg_ai_prob
        }
    
    # Get authors to display: include all with at least 1 commit, prioritizing those with higher AI probability
    # First, get authors with at least 1 commit
    active_authors = [(author, stats) for author, stats in author_stats.items() if stats['total_commits'] > 0]
    
    # Sort by AI probability (primary) and total commits (secondary)
    authors_by_ai_prob = sorted(active_authors, key=lambda x: (x[1]['avg_ai_prob'], x[1]['total_commits']), reverse=True)
    
    # Sort by total commits
    authors_by_commits = sorted(active_authors, key=lambda x: x[1]['total_commits'], reverse=True)
    
    # Combine the lists, prioritizing top authors by commits but ensuring high AI probability authors are included
    top_by_commits = authors_by_commits[:7]  # Top 7 by commits
    top_by_ai_prob = authors_by_ai_prob[:5]  # Top 5 by AI probability
    
    # Combine and deduplicate
    selected_authors = []
    seen = set()
    
    for author, stats in top_by_commits + top_by_ai_prob:
        if author not in seen:
            selected_authors.append((author, stats['total_commits']))
            seen.add(author)
    
    # Get all month labels sorted chronologically
    all_months = set()
    for author, monthly_data in author_monthly_stats.items():
        all_months.update(monthly_data.keys())
    all_months = sorted(list(all_months))
    
    # Chart constants
    CHART_WIDTH = 60  # Width of the chart in characters
    CHART_HEIGHT = 15  # Height of the chart in characters
    Y_AXIS_WIDTH = 10  # Width of the Y-axis labels
    
    # Display charts for each selected author
    for author, total_commits in selected_authors:
        # No minimum commit threshold - show all selected authors
            
        print(f"\n{author} (Total Commits: {total_commits})")
        print("Performance Chart (Commits/Day + Lines Changed/Day)")
        print("─" * (CHART_WIDTH + Y_AXIS_WIDTH + 5))
        
        # Find max values for scaling
        max_commits_per_day = max(
            (data.get('commits_per_day', 0) for data in author_monthly_stats[author].values()),
            default=1
        )
        # Ensure max_commits_per_day is never zero to avoid division by zero
        max_commits_per_day = max(max_commits_per_day, 0.001)
        
        max_lines_per_day = max(
            (data.get('lines_changed_per_day', 0) for data in author_monthly_stats[author].values()),
            default=1
        )
        # Ensure max_lines_per_day is never zero to avoid division by zero
        max_lines_per_day = max(max_lines_per_day, 0.001)
        
        # Normalize both metrics to a combined performance score
        # We'll use a weighted average: 40% commits, 60% lines changed
        combined_scores = {}
        for month in all_months:
            if month in author_monthly_stats[author]:
                commits_score = author_monthly_stats[author][month].get('commits_per_day', 0) / max_commits_per_day
                lines_score = author_monthly_stats[author][month].get('lines_changed_per_day', 0) / max_lines_per_day
                combined_scores[month] = (0.4 * commits_score + 0.6 * lines_score) * CHART_HEIGHT
        
        # Create the chart
        for y in range(CHART_HEIGHT, 0, -1):
            # Y-axis labels (show at 0%, 25%, 50%, 75%, 100%)
            if y == CHART_HEIGHT:
                y_label = "100%"
            elif y == CHART_HEIGHT * 3 // 4:
                y_label = "75% "
            elif y == CHART_HEIGHT // 2:
                y_label = "50% "
            elif y == CHART_HEIGHT // 4:
                y_label = "25% "
            elif y == 1:
                y_label = "0%  "
            else:
                y_label = "    "
                
            line = f"{y_label} │"
            
            # Plot points with spacing between months
            for month in all_months:
                if month in combined_scores:
                    score = combined_scores[month]
                    if score >= y:
                        # Show AI probability as a character
                        ai_prob = author_monthly_stats[author][month].get('ai_probability', 0)
                        if ai_prob >= 75:
                            line += "A   "  # High AI probability
                        elif ai_prob >= 50:
                            line += "a   "  # Medium AI probability
                        elif ai_prob >= 25:
                            line += "o   "  # Low AI probability
                        else:
                            line += "*   "  # Very low AI probability
                    else:
                        line += "    "  # 4 spaces for empty point
                else:
                    line += "    "  # 4 spaces for missing month
            print(line)
        
        # X-axis with spacing
        x_axis = "     └"
        for _ in all_months:
            x_axis += "───"  # 3 underscores per month
        print(x_axis)
        
        # Month labels with spacing
        month_labels = "       "
        for month in all_months:
            month_labels += month[-2:] + "  "  # 2 spaces after month label
        print(month_labels)
        
        # No legend here - it's printed once at the beginning
        
        # Print detailed monthly stats
        print("\nDetailed Monthly Stats:")
        header = f"{'Month':<8} {'Commits/Day':>12} {'Lines/Day':>12} {'AI Prob %':>10}"
        print(header)
        print("─" * len(header))
        
        for month in all_months:
            if month in author_monthly_stats[author]:
                data = author_monthly_stats[author][month]
                commits_per_day = data.get('commits_per_day', 0)
                lines_per_day = data.get('lines_changed_per_day', 0)
                ai_prob = data.get('ai_probability', 0)
                print(f"{month:<8} {commits_per_day:>12.2f} {lines_per_day:>12.2f} {ai_prob:>10.1f}")
        print()
