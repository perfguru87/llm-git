import logging
from difflib import SequenceMatcher

def normalize_name(name):
    """Normalize a name for comparison by converting to lowercase and removing extra spaces."""
    if not name:
        return ""
    # Convert to lowercase, remove extra spaces, and strip common prefixes/suffixes
    return ' '.join(part for part in name.lower().split() if part)

def fuzzy_match(str1, str2, threshold=0.8):
    """
    Check if two strings are a fuzzy match based on a similarity threshold.
    Returns True if the similarity ratio is above the threshold.
    """
    if not str1 or not str2:
        return False
        
    # Normalize both strings
    str1 = normalize_name(str1)
    str2 = normalize_name(str2)
    
    if not str1 or not str2:
        return False
    
    # Check for direct match after normalization
    if str1 == str2:
        return True
        
    # Check for partial matches (e.g., "Robert" in "Robert Isaacs")
    words1 = str1.split()
    words2 = str2.split()
    
    # If one name is part of the other
    if any(w1 == w2 for w1 in words1 for w2 in words2):
        return True
        
    # Check for initial matches (e.g., "R. Isaacs" vs "Robert Isaacs")
    if len(words1) > 1 and len(words2) > 1:
        if (words1[0][0] == words2[0][0] and 
            words1[-1] == words2[-1] and 
            (len(words1) == 1 or len(words2) == 1 or 
             (words1[0] == words2[0] or words1[-1] == words2[-1]))):
            return True
    
    # Fall back to sequence matching
    return SequenceMatcher(None, str1, str2).ratio() >= threshold

def extract_company_name(company_string):
    """Extract and clean company name from a string."""
    if company_string is None:  # Check for None
        return ""
    # Remove common suffixes
    suffixes = ["Inc.", "Corp.", "Ltd.", "LLC", "PLC", "SA"]
    for suffix in suffixes:
        company_string = company_string.replace(suffix, "").strip()
    # Remove trailing periods or commas
    company_string = company_string.rstrip(",.@")
    company_string = company_string.strip(",.@")
    return company_string

def extract_domain(email):
    """Extract domain from email address."""
    if not email or '@' not in email:
        return None
    return email.split('@')[-1].lower()

def generate_contributors_report(repo):
    """
    Generate a detailed report about repository contributors and their organizational affiliations.
    
    Args:
        repo: Repository object containing contributor information
        
    Returns:
        Dictionary containing detailed contributor statistics and commercial involvement
    """
    print(f"\n=== Contributor Analysis for {repo.organization_login}/{repo.name} ===")
    
    # Get contributor data
    contributors_data = repo.get_contributors()
    total_contributors = len(contributors_data) if contributors_data else 0
    print(f"Found {total_contributors} total contributors")
    
    # Print detailed contributor information
    if total_contributors > 0:
        print("\n=== Detailed Contributor Information ===")
        print(f"{'GitHub':<15} {'Name':<25} {'Email':<30} {'Company':<25} {'Contributions':<12} {'Org Member'}")
        print("-" * 115)
        
        # Sort contributors by number of contributions (descending)
        sorted_contributors = sorted(repo.contributors.values(), 
                                  key=lambda x: x.contributions, 
                                  reverse=True)
        
        for contributor in sorted_contributors:
            # Truncate long strings for better formatting
            login = (contributor.login or '')[:14]
            name = (contributor.name or '')[:24]
            email = (contributor.email or '')[:29]
            company = (contributor.company or 'Unknown')[:24]
            org_member = '✓' if contributor.within_repo_org else '✗'
            
            print(f"{login:<15} {name:<25} {email:<30} {company:<25} "
                  f"{contributor.contributions:<12,} {org_member}")
    
    print()  # Add an extra newline for better separation
    
    # Initialize tracking dictionaries
    domain_with_organization = {}
    companies_with_organization = {}
    users_domains = {}
    users_companies = {}
    contributors_by_company = {}
    commercial_contributors = 0
    org_contributors = 0
    
    # Analyze each contributor
    for c in repo.contributors:
        cont = repo.contributors[c]
        
        # Track email domains
        user_domain = extract_domain(cont.email) if cont.email else None
        company = extract_company_name(cont.company) if cont.company else 'Unknown'
        
        # Process domain information
        if user_domain: 
            users_domains[user_domain] = users_domains.get(user_domain, 0) + 1
            
            # Check if domain indicates commercial entity
            if any(domain in user_domain.lower() for domain in ['gmail.com', 'yahoo.com', 'outlook.com', 'icloud.com']):
                domain_type = 'Personal'
            else:
                domain_type = 'Corporate/Organization'
                commercial_contributors += 1
        
        # Track company information
        if company and company.lower() != 'none':
            users_companies[company] = users_companies.get(company, 0) + 1
            
            # Track contributors by company
            if company not in contributors_by_company:
                contributors_by_company[company] = []
            contributors_by_company[company].append({
                'login': cont.login,
                'contributions': cont.contributions,
                'email': cont.email
            })

        # Track organization members
        if cont.within_repo_org:
            org_contributors += 1
            if company:
                companies_with_organization[company] = companies_with_organization.get(company, 0) + 1
            if user_domain:
                domain_with_organization[user_domain] = domain_with_organization.get(user_domain, 0) + 1

    # Sort the dictionaries by count (descending)
    companies_with_organization = sorted(companies_with_organization.items(), key=lambda x: x[1], reverse=True)
    domain_with_organization = sorted(domain_with_organization.items(), key=lambda x: x[1], reverse=True)
    users_domains = sorted(users_domains.items(), key=lambda x: x[1], reverse=True)
    users_companies = sorted(users_companies.items(), key=lambda x: x[1], reverse=True)
    
    # Print historical git authors information
    if hasattr(repo, 'stat') and hasattr(repo.stat, 'authors'):
        total_authors = len(repo.stat.authors) if repo.stat.authors else 0
        authors_with_email = sum(1 for a in repo.stat.authors.values() if a.get('email')) if repo.stat.authors else 0
        email_percentage = (authors_with_email / total_authors * 100) if total_authors > 0 else 0
        
        # Get current contributor emails and names for matching
        current_contributor_emails = set()
        current_contributor_names = set()
        
        for c in repo.contributors.values():
            if c.email:
                current_contributor_emails.add(c.email.lower())
            if c.login:
                current_contributor_names.add(c.login.lower())
        
        # Track matches with details and avoid duplicate matches
        email_matches = []
        name_matches = []
        fuzzy_matches = []
        matched_authors = set()
        
        if total_authors > 0:
            # First pass: Exact email matches (highest confidence)
            for author_email, author_data in repo.stat.authors.items():
                email = (author_data.get('email') or '').lower()
                name = author_data.get('name', '')
                
                if not email:
                    continue
                    
                for c in repo.contributors.values():
                    if not c.email:
                        continue
                        
                    if email == c.email.lower():
                        display = f"{name} <{email}> (as {c.login})"
                        email_matches.append(display)
                        matched_authors.add(author_email)
                        break
                        
            # Second pass: More flexible name matching
            for author_email, author_data in repo.stat.authors.items():
                if author_email in matched_authors:
                    continue
                    
                # Try to get author name, use the key as fallback if it looks like a name
                author_name = author_data.get('name', '').strip()
                
                # If no name in data, try to derive it from the email or use the key as name
                if not author_name:
                    if '@' in author_email:
                        # If the key looks like an email, extract the name part
                        author_name = author_email.split('@')[0].replace('.', ' ').strip()
                    elif ' ' in author_email or author_email.replace(' ', '').isalpha():
                        # If the key looks like a name (has spaces or is alphabetic), use it as is
                        author_name = author_email.strip()
                    else:
                        # If we can't determine a name, skip this author
                        continue
                
                # Try to extract a clean name from the author string
                clean_author_name = author_name.split('(')[0].strip()
                author_name_variations = {
                    'original': author_name.lower(),
                    'clean': clean_author_name.lower(),
                    'no_spaces': author_name.replace(' ', '').lower(),
                    'clean_no_spaces': clean_author_name.replace(' ', '').lower()
                }
                
                # Add first name variations if applicable
                if ' ' in clean_author_name:
                    first_name = clean_author_name.split()[0].lower()
                    author_name_variations['first_name'] = first_name
                    
                    last_name = clean_author_name.split(' ', 1)[1].lower() if ' ' in clean_author_name else ''
                    if last_name:
                        author_name_variations['last_name'] = last_name
                
                for c_login, c in repo.contributors.items():
                    # Skip if we have nothing to compare
                    if not c.login and not c.name:
                        continue
                    
                    # Create variations of contributor's name and login
                    contrib_variations = {}
                    if c.name:
                        contrib_variations['name_original'] = c.name.lower()
                        contrib_variations['name_no_spaces'] = c.name.lower().replace(' ', '')
                        
                        # Add name parts if it has multiple words
                        name_parts = c.name.lower().split()
                        if len(name_parts) > 1:
                            contrib_variations['first_name'] = name_parts[0]
                            contrib_variations['last_name'] = ' '.join(name_parts[1:])
                    
                    if c.login:
                        contrib_variations['login_original'] = c.login.lower()
                        contrib_variations['login_no_hyphens'] = c.login.lower().replace('-', '')
                        contrib_variations['login_no_underscores'] = c.login.lower().replace('_', '')
                    
                    # Check for any matching variations
                    matched = False
                    for auth_var_name, auth_var in author_name_variations.items():
                        for contrib_var_name, contrib_var in contrib_variations.items():
                            if auth_var and contrib_var and auth_var == contrib_var:
                                email = author_data.get('email', 'no-email')
                                display = f"{author_name} <{email}> (matched {auth_var_name} '{auth_var}' with {contrib_var_name} '{contrib_var}')"
                                name_matches.append(display)
                                matched_authors.add(author_email)
                                matched = True
                                break
                        if matched:
                            break
                    if matched:
                        break
            
            # Second pass: More flexible name matching
            for author_email, author_data in repo.stat.authors.items():
                if author_email in matched_authors:
                    continue
                    
                # Try to get author name, use the key as fallback if it looks like a name
                author_name = author_data.get('name', '').strip()
                
                # If no name in data, try to derive it from the email or use the key as name
                if not author_name:
                    if '@' in author_email:
                        # If the key looks like an email, extract the name part
                        author_name = author_email.split('@')[0].replace('.', ' ').strip()
                    elif ' ' in author_email or author_email.replace(' ', '').isalpha():
                        # If the key looks like a name (has spaces or is alphabetic), use it as is
                        author_name = author_email.strip()
                    else:
                        # If we can't determine a name, skip this author
                        continue
                
                matched = False
                
                # Try to extract a clean name from the author string
                clean_author_name = author_name.split('(')[0].strip()
                author_name_variations = {
                    'original': author_name.lower(),
                    'clean': clean_author_name.lower(),
                    'no_spaces': author_name.replace(' ', '').lower(),
                    'clean_no_spaces': clean_author_name.replace(' ', '').lower()
                }
                
                # Add first name variations if applicable
                if ' ' in clean_author_name:
                    first_name = clean_author_name.split()[0].lower()
                    author_name_variations['first_name'] = first_name
                    
                    last_name = clean_author_name.split(' ', 1)[1].lower() if ' ' in clean_author_name else ''
                    if last_name:
                        author_name_variations['last_name'] = last_name
                
                for c_login, c in repo.contributors.items():
                    
                    # Skip if we have nothing to compare
                    if not c.login and not c.name:
                        continue
                    
                    # Create variations of contributor's name and login
                    contrib_variations = {}
                    if c.name:
                        contrib_variations['name_original'] = c.name.lower()
                        contrib_variations['name_no_spaces'] = c.name.lower().replace(' ', '')
                        
                        # Add name parts if it has multiple words
                        name_parts = c.name.lower().split()
                        if len(name_parts) > 1:
                            contrib_variations['first_name'] = name_parts[0]
                            contrib_variations['last_name'] = ' '.join(name_parts[1:])
                    
                    if c.login:
                        contrib_variations['login_original'] = c.login.lower()
                        contrib_variations['login_no_hyphens'] = c.login.lower().replace('-', '')
                        contrib_variations['login_no_underscores'] = c.login.lower().replace('_', '')
                    
                    # Check for any matching variations
                    for auth_var_name, auth_var in author_name_variations.items():
                        for contrib_var_name, contrib_var in contrib_variations.items():
                            if auth_var and contrib_var and auth_var == contrib_var:
                                email = author_data.get('email', 'no-email')
                                display = f"{author_name} <{email}> (matched {auth_var_name} '{auth_var}' with {contrib_var_name} '{contrib_var}')"
                                name_matches.append(display)
                                matched_authors.add(author_email)
                                matched = True
                                break
                        if matched:
                            break
                        break
                
                if matched:
                    break
                
                # Try matching parts of names
                # Only attempt this if we're inside the contributor loop and c is defined
                if not matched and 'c' in locals() and c.name and ' ' in c.name and ' ' in clean_author_name:
                    author_parts = set(clean_author_name.lower().split())
                    contrib_parts = set(c.name.lower().split())
                    common = author_parts.intersection(contrib_parts)
                    if common:
                        email = author_data.get('email', 'no-email')
                        display = f"{author_name} <{email}> (matched by name parts: {', '.join(common)})"
                        name_matches.append(display)
                        matched_authors.add(author_email)
                        logging.debug(f"MATCH BY NAME PARTS: {display}")
                        matched = True
                        break
            
            if not matched:
                logging.debug(f"NO MATCHES FOUND for author: '{author_name}'")
        
        # Third pass: More flexible matching (lower confidence)
        for author_email, author_data in repo.stat.authors.items():
            if author_email in matched_authors:
                continue
                
            author_name = author_data.get('name', '')
            if not author_name:
                continue
                
            for c in repo.contributors.values():
                if not c.login and not c.name:
                    continue
                
                # Get normalized versions for comparison
                norm_author = normalize_name(author_name)
                norm_contrib_name = normalize_name(c.name or '')
                norm_contrib_login = normalize_name(c.login or '')
                
                # Skip if we have nothing to compare
                if not norm_author or (not norm_contrib_name and not norm_contrib_login):
                    continue
                
                # Check for common patterns
                match_found = False
                match_type = ''
                
                # 1. Check if login is part of author name or vice versa
                if (c.login and 
                    (c.login.lower() in author_name.lower() or 
                     any(part.lower() == c.login.lower() for part in author_name.split()))):
                    match_type = f"contains GitHub: {c.login}"
                    match_found = True
                
                # 2. Check if names share common parts
                elif norm_contrib_name and norm_author:
                    # Split into parts and check for any matching parts
                    author_parts = set(norm_author.split())
                    contrib_parts = set(norm_contrib_name.split())
                    common = author_parts.intersection(contrib_parts)
                    
                    if len(common) >= 1 and (len(common) >= min(len(author_parts), len(contrib_parts)) / 2):
                        match_type = f"shared parts: {', '.join(common)}"
                        match_found = True
                
                # 3. Fall back to fuzzy matching
                elif ((c.login and fuzzy_match(author_name, c.login)) or 
                      (c.name and fuzzy_match(author_name, c.name))):
                    match_type = f"fuzzy match with {c.login or c.name}"
                    match_found = True
                
                if match_found:
                    email = author_data.get('email', 'no-email')
                    display = f"{author_name} <{email}> ({match_type})"
                    fuzzy_matches.append(display)
                    matched_authors.add(author_email)
                    break
        
        # Calculate statistics
        total_matched = len(matched_authors)
        match_percentage = (total_matched / total_authors * 100) if total_authors > 0 else 0
        
        print("\nHistorical Git Authors (includes all commit authors):")
        print(f"  • Total unique authors in git history: {total_authors}")
        print(f"  • Authors with identifiable emails: {authors_with_email} ({email_percentage:.1f}%)")
        
        if total_authors > 0:
            print(f"  • Matched with current contributors: {total_matched} ({match_percentage:.1f}%)")
            
            # Show exact email matches (highest confidence)
            if email_matches:
                print(f"\n  • Exact email matches ({len(email_matches)}):")
                for match in sorted(email_matches):
                    print(f"    • {match}")
            
            # Show exact name matches (medium confidence)
            if name_matches:
                print(f"\n  • Exact name matches ({len(name_matches)}):")
                for match in sorted(name_matches):
                    print(f"    • {match}")
            
            # Show fuzzy matches (lower confidence)
            if fuzzy_matches:
                print(f"\n  • Fuzzy matches ({len(fuzzy_matches)}):")
                for match in sorted(fuzzy_matches):
                    print(f"    • {match}")
            
    # Print top domains and companies
    print("\n=== Top Contributor Email Domains ===")
    print("These are the most common email domains used by contributors:")
    for i, (domain, count) in enumerate(users_domains[:10], 1):
        print(f"  {i}. {domain} ({count} contributor{'s' if count > 1 else ''})")
    
    print("\n=== Top Contributor Companies ===")
    if users_companies:
        print("Companies associated with contributors:")
        for i, (company, count) in enumerate(users_companies[:10], 1):
            print(f"  {i}. {company} ({count} contributor{'s' if count > 1 else ''})")
    else:
        print("No company information available from GitHub profiles.")
    
    # Print organization information
    if companies_with_organization:
        print("\n=== Organization Members ===")
        print("These companies have members who are part of the repository's organization:")
        for i, (company, count) in enumerate(companies_with_organization[:10], 1):
            print(f"  {i}. {company} ({count} member{'s' if count > 1 else ''})")

    # Print summary statistics
    print("\n=== Contribution Metrics ===")
    print("Current GitHub Contributors:")
    print(f"  • Total unique contributors listed: {total_contributors}")
    
    # Print commercial involvement assessment
    commercial_ratio = (commercial_contributors / total_contributors * 100) if total_contributors > 0 else 0
    print("\n=== Commercial Involvement Assessment ===")
    print("Email Domain Analysis:")
    print(f"  • Contributors with corporate/organization emails: {commercial_contributors} of {total_contributors} ({commercial_ratio:.1f}%)")
    
    print("\nAssessment:")
    if commercial_ratio > 50:
        print("  🔍 Strong commercial involvement - The majority of contributors use corporate email addresses.")
    elif commercial_ratio > 20:
        print("  🔍 Moderate commercial involvement - A significant portion of contributors use corporate email addresses.")
    else:
        print("  🔍 Limited commercial involvement - Most contributors use personal email addresses.")
    
    print("\nNote: This analysis is based on email domains and may not reflect actual employment status.")

    # Prepare return data
    contributors_data = {
        "n_total_contributors": total_contributors,
        "n_total_contributors_matched_users": 0,  # Kept for backward compatibility
        "n_total_contributors_matched_users_p": 0,  # Kept for backward compatibility
        "n_total_active_users": 0,  # Will be populated by other functions
        "n_total_active_users_matched": 0,  # Will be populated by other functions
        "n_total_active_users_matched_p": 0,  # Will be populated by other functions
        "top_users_domains": f"{users_domains[:10]}",
        "top_users_companies": f"{users_companies[:10]}",
        "top_companies_with_organization": f"{companies_with_organization[:10]}",
        "top_domains_with_organization": f"{domain_with_organization[:10]}",
        "top_active_users_domains": ""  # Will be populated by other functions
    }

    logging.info(f"=FILL==>>>>             \"{repo.id}\"\n")
    return contributors_data
