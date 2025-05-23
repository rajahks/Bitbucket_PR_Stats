import time
import requests
import json
import requests
from datetime import datetime
import pytz
import sys
from datetime import timedelta
import pandas as pd

# Create a session object to reuse the connection across multiple requests
session = requests.Session()

def fetch_from_bitbucket(session, base_url, bearer_token, params=None, retries=3, delay=5):
    headers = {'Authorization': f'Bearer {bearer_token}'}
    for attempt in range(retries):
        try:
            response = session.get(base_url, headers=headers, params=params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Attempt {attempt + 1} failed. Retrying after {delay}secs: {e}")
            time.sleep(delay)
    print(f"Error: Failed to fetch from bitbucket after {retries} attempts.")
    return None

def fetch_pull_requests_for_a_user(bitbucket_server_fqdn, bearer_token, params=None):
    """ Fetches pull requests for a user using the Dashboard bitbucket api.
        The dashboard API is constructed based on the server fqdn
       Ref: https://developer.atlassian.com/server/bitbucket/rest/v818/api-group-dashboard/#api-api-latest-dashboard-pull-requests-get

    Args:
        bitbucket_server_fqdn (string): The fqdn of the Bitbucket server. Eg: code.myorg.com
        bearer_token (string): The token to authenticate with bitbucket.
        params (json, optional): params which have to be passed to the bitbucket api. Defaults to None.

    Returns:
        json: Contains the pull requests for the user.
    """
    
    dashboard_api_url = f"https://{bitbucket_server_fqdn}/rest/api/latest/dashboard/pull-requests"

    # As of now just calls the fetch_from_bitbucket method. But can be used to add more logic in future.
    return fetch_from_bitbucket(session, dashboard_api_url, bearer_token, params)

def fetch_commits_for_pull_request(bitbucket_server_fqdn, bearer_token, project_key, repository_slug, pull_request_id):
    """Fetches all commits for a specific pull request using the Bitbucket API, handling pagination.

    Args:
        bitbucket_server_fqdn (string): The FQDN of the Bitbucket server. Eg: code.myorg.com
        bearer_token (string): The token to authenticate with Bitbucket.
        project_key (string): The project key of the repository.
        repository_slug (string): The slug of the repository.
        pull_request_id (int): The ID of the pull request.

    Returns:
        list: A list of all commits for the pull request.
    """
    commits_api_url = f"https://{bitbucket_server_fqdn}/rest/api/latest/projects/{project_key}/repos/{repository_slug}/pull-requests/{pull_request_id}/commits"
    all_commits = []
    start = 0
    limit = 25  # Default limit for Bitbucket API

    while True:
        params = {"start": start, "limit": limit}
        response = fetch_from_bitbucket(session, commits_api_url, bearer_token, params)

        if not response or "values" not in response:
            break

        # Add the current page of commits to the list
        all_commits.extend(response["values"])

        # Check if there are more pages
        if response.get("isLastPage", True):
            break

        # Update the start parameter for the next page
        start = response.get("nextPageStart", start + limit)

    return all_commits

def fetch_jira_issues_for_pull_request(bitbucket_server_fqdn, bearer_token, pr_project_key, pr_repo_slug, pr_id):
    """Fetches JIRA issues linked to a specific pull request using the Bitbucket API.

    Args:
        bitbucket_server_fqdn (string): The FQDN of the Bitbucket server. Eg: code.myorg.com
        bearer_token (string): The token to authenticate with Bitbucket.
        pr_project_key (string): The project key of the repository.
        pr_repo_slug (string): The slug of the repository.
        pr_id (int): The ID of the pull request.

    Returns:
        json: Contains the JIRA issues linked to the pull request.
    """
    jira_keys_for_pr_api_url = f"http://{bitbucket_server_fqdn}/rest/jira/latest/projects/{pr_project_key}/repos/{pr_repo_slug}/pull-requests/{pr_id}/issues"
    return fetch_from_bitbucket(session, jira_keys_for_pr_api_url, bearer_token)

def fetch_commit_diff_and_calculate_lines(bitbucket_server_fqdn, bearer_token, project_key, repository_slug, commit_id):
    """Fetches the diff for a specific commit and calculates lines added, deleted, and modified.

    Args:
        bitbucket_server_fqdn (string): The FQDN of the Bitbucket server. Eg: code.myorg.com
        bearer_token (string): The token to authenticate with Bitbucket.
        project_key (string): The project key of the repository.
        repository_slug (string): The slug of the repository.
        commit_id (string): The ID of the commit.

    Returns:
        dict: A dictionary containing the number of lines added, deleted, and modified.
    """
    diff_api_url = f"https://{bitbucket_server_fqdn}/rest/api/latest/projects/{project_key}/repos/{repository_slug}/commits/{commit_id}/diff"
    diff_data = fetch_from_bitbucket(session, diff_api_url, bearer_token)

    if not diff_data:
        print(f"Failed to fetch diff for commit {commit_id}")
        return {"linesAdded": 0, "linesDeleted": 0, "linesModified": 0}

    lines_added = 0
    lines_deleted = 0
    lines_modified = 0
    
    # Iterate through the diffs
    for diff in diff_data.get("diffs", []):
        for hunk in diff.get("hunks", []):
            for segment in hunk.get("segments", []):
                if segment["type"] == "ADDED":
                    lines_added += len(segment.get("lines", []))
                elif segment["type"] == "REMOVED":
                    lines_deleted += len(segment.get("lines", []))

    # Calculate lines modified as the sum of added and deleted lines
    lines_modified = lines_added + lines_deleted

    return {"linesAdded": lines_added, "linesDeleted": lines_deleted, "linesModified": lines_modified}

def calculate_total_lines_for_commits(bitbucket_server_fqdn, bearer_token, pr_project_key, pr_repo_slug, commits_for_pr):
    """Calculates the total lines added, deleted, and modified for all commits in a pull request.

    Args:
        bitbucket_server_fqdn (string): The FQDN of the Bitbucket server.
        bearer_token (string): The token to authenticate with Bitbucket.
        pr_project_key (string): The project key of the repository.
        pr_repo_slug (string): The slug of the repository.
        commits_for_pr (list): List of commits in the pull request.

    Returns:
        dict: A dictionary containing the total lines added, deleted, and modified.
    """
    total_lines_added = 0
    total_lines_deleted = 0
    total_lines_modified = 0

    for commit in commits_for_pr:
        commit_id = commit['id']
        # Fetch diff stats for the commit
        diff_stats = fetch_commit_diff_and_calculate_lines(bitbucket_server_fqdn, bearer_token, pr_project_key, pr_repo_slug, commit_id)
        # Update total stats
        total_lines_added += diff_stats['linesAdded']
        total_lines_deleted += diff_stats['linesDeleted']
        total_lines_modified += diff_stats['linesModified']

    return {
        "total_lines_added": total_lines_added,
        "total_lines_deleted": total_lines_deleted,
        "total_lines_modified": total_lines_modified,
    }

def convert_timestamp_to_date(timestamp_millis, timezone='Asia/Kolkata'):
    """Converts a timestamp to a date string in the timezone specified.

    Args:
        timestamp_millis (int): The timestamp in milliseconds.

    Returns:
        str: The date as a string in the 'YYYY-MM-DD HH:MM:SS' format.
    """
    # Convert the timestamp to seconds
    timestamp_seconds = timestamp_millis / 1000
    # Create a datetime object in UTC using fromtimestamp method
    date_utc = datetime.fromtimestamp(timestamp_seconds, pytz.UTC)
    # Convert the datetime object to the timezone specified. 
    # Defaults to 'Asia/Kolkata' timezone
    date_india = date_utc.astimezone(pytz.timezone(timezone))
    # Format the date as a string
    date_str = date_india.strftime('%Y-%m-%d %H:%M:%S')
    return date_str


def fetch_pull_request_stats(bitbucket_server_fqdn, bearer_token, username_list, start_date_str, end_date_str):
    # initialize stats
    stats = {}
    stats['start_date'] = start_date_str
    stats['end_date'] = end_date_str
    stats['total_pr_count'] = 0
    stats['total_pr_list'] = []

    for username in username_list:
        print(f"Fetching pull requests for {username}")
        # setup the query params for the API
        #TODO: Ideally we should paginate and fetch all the pull requests. But for now, 
        # we are fetching only the first 1000 pull requests for the user since we want yearly data
        # and a dev will likely not have more than 1000 PRs in a year.
        #
        # BUGALERT: If we are fetching PRs for older years, we might miss some PRs as we fetch
        # only the first 1000 newest PRs.
        #
        params = {'role':'AUTHOR','user':username, 'limit':1000, 'order':'NEWEST' }
        pull_requests = fetch_pull_requests_for_a_user(bitbucket_server_fqdn, bearer_token, params)
        
        if pull_requests: 
            # convert the start and end date to timestamp in milliseconds as that
            # is the format in which the createdDate is returned by the Bitbucket API
            startDateObject = datetime.strptime(start_date_str, "%Y-%m-%d")
            # Need to consider PRs created till the end of the day. So, add 1 day and subtract 1 second
            endDateObject = datetime.strptime(end_date_str, "%Y-%m-%d") + timedelta(days=1) - timedelta(seconds=1)
            startDateTimestampMilliSec = int(startDateObject.timestamp()*1000)
            endDateTimestampMilliSec = int(endDateObject.timestamp()*1000)

            stats_for_dev = {}
            stats_for_dev['username'] = username
            stats_for_dev['pr_count'] = 0
            stats_for_dev['pr_list'] = []

            for pr in pull_requests['values']:
                prCreatedDate = pr['createdDate']
                # Check if the PR was created in the given date range (inclusive)
                if startDateTimestampMilliSec <= prCreatedDate <= endDateTimestampMilliSec:
                    stats_for_dev['pr_count'] = stats_for_dev.get('pr_count', 0) + 1
                    pr_info = {}
                    pr_info['title'] = pr['title']
                    pr_info['author'] = pr['author']['user']['name']
                    pr_info['author_full_name'] = pr['author']['user']['displayName']
                    pr_info['state'] = pr['state']
                    pr_info['created_date'] = convert_timestamp_to_date(pr['createdDate'])
                    pr_info['dest_branch'] = pr['toRef']['displayId']
                    pr_info['repo'] = pr['toRef']['repository']['name']
                    pr_info['pr_link'] = pr['links']['self'][0]['href']

                    # Extract identifiers of the PR
                    pr_id = pr['id']
                    pr_project_key = pr['toRef']['repository']['project']['key']
                    pr_repo_slug = pr['toRef']['repository']['slug']

                    print(f"\tProcessing PR ID: {pr_id} in repo {pr_repo_slug}")

                    # Print before fetching commits for the PR
                    print(f"\t\tFetching commits for PR ID: {pr_id}")
                    commits_for_pr = fetch_commits_for_pull_request(bitbucket_server_fqdn, bearer_token, pr_project_key, pr_repo_slug, pr_id)

                    # Add commit count and list of commit IDs to pr_info
                    pr_info['commit_count'] = len(commits_for_pr)
                    pr_info['commit_ids'] = [commit['id'] for commit in commits_for_pr]

                    # Print before calculating total lines for the PR
                    print(f"\t\tCalculating total lines for PR ID: {pr_id}")
                    total_lines_stats = calculate_total_lines_for_commits(bitbucket_server_fqdn, bearer_token, pr_project_key, pr_repo_slug, commits_for_pr)

                    # Add the total stats to pr_info
                    pr_info.update(total_lines_stats)

                    # Print before fetching Jira issues for the PR
                    print(f"\t\tFetching Jira issues for PR ID: {pr_id}")
                    jira_issues_for_pr = fetch_jira_issues_for_pull_request(bitbucket_server_fqdn, bearer_token, pr_project_key, pr_repo_slug, pr_id)
                    pr_jira_urls = [jira_key['key'] for jira_key in jira_issues_for_pr]

                    # Update the pr_info with the Jira keys pertaining to this PR
                    pr_info['jira'] = pr_jira_urls

                    # Append the PR info to the stats
                    stats_for_dev['pr_list'].append(pr_info)
            
            stats['total_pr_count'] += stats_for_dev['pr_count']
            stats['total_pr_list'].append(stats_for_dev)

    return stats

def read_config_file():
    with open('config.json', 'r') as file:
        config_data = json.load(file)
    return config_data

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Please provide start date and end date as command line arguments.")
        print("Usage: python PR_stats.py <start_date> <end_date>")
        print("Example: python PR_stats.py 2024-03-06 2024-03-13")
        print("The dates should be in the format YYYY-MM-DD")
        sys.exit(1)

    start_date_str = sys.argv[1]
    end_date_str = sys.argv[2]

    config_data = read_config_file()
    
    bitbucket_server_fqdn = config_data.get('bitbucket_server_fqdn')
    if not bitbucket_server_fqdn:
        raise ValueError("bitbucket_server_fqdn is missing or empty in the config.json file")

    bearer_token = config_data.get('bearer_token')
    if not bearer_token:
        raise ValueError("bearer_token is missing or empty in the config.json file")
    
    username_list = config_data.get('username_list', [])
    output_json_file = config_data.get('output_json_file', "pr_stats_output.json")

    print(f"Fetching pull request stats for the period {start_date_str} to {end_date_str}")

    stats = fetch_pull_request_stats(bitbucket_server_fqdn, bearer_token, username_list, start_date_str, end_date_str)

    # Write the stats in json format to a file    
    with open(output_json_file, 'w') as file:
        json.dump(stats, file, indent=2)

    
    # Write the stats to an excel file
    # Collect the data in a list
    data = []
    for user_stats in stats['total_pr_list']:
        for pr in user_stats['pr_list']:
            data.append({
                #'Author': pr['author'],
                'Author Full Name': pr['author_full_name'],
                'Repository': pr['repo'],
                'PR Title': pr['title'],
                'State': pr['state'],
                'Created Date': pr['created_date'],
                'Destination Branch': pr['dest_branch'],
                'PR Link': pr['pr_link'],
                'JIRA Links': ', '.join(pr['jira']),
                'Total Lines Added': pr.get('total_lines_added', 0),
                'Total Lines Deleted': pr.get('total_lines_deleted', 0),
                'Total Lines Modified': pr.get('total_lines_modified', 0),
                'Commit Count': pr.get('commit_count', 0),
                'Commit IDs': ', '.join(pr.get('commit_ids', []))
            })
    
    # Convert the list of data to a DataFrame
    df = pd.DataFrame(data, columns=[
        # 'Author', 
        'Author Full Name', 
        'Repository', 
        'PR Title', 
        'State', 
        'Created Date', 
        'Destination Branch', 
        'PR Link', 
        'JIRA Links',
        'Total Lines Added',
        'Total Lines Deleted',
        'Total Lines Modified',
        'Commit Count',
        'Commit IDs'
    ])

    # Write the DataFrame to an Excel file
    output_excel_file = config_data.get('output_excel_file', "pr_stats_output.xlsx")
    df.to_excel(output_excel_file, index=False)
    
    # Close the session when done
    session.close()
