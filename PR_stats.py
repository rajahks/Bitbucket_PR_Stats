import requests
import json
import requests
from datetime import datetime
import pytz
import sys
from datetime import timedelta

def fetch_from_bitbucket(base_url, bearer_token, params=None):
    headers = {'Authorization': f'Bearer {bearer_token}'}
    response = requests.get(base_url, headers=headers, params=params)
    if response.status_code == 200:
        pull_requests = json.loads(response.text)
        return pull_requests
    else:
        print(f"Failed to fetch from bitbucket. Status code: {response.status_code}")
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
    return fetch_from_bitbucket(dashboard_api_url, bearer_token, params)

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
    stats['pr_count'] = 0

    for username in username_list:
        print(f"Fetching pull requests for {username}")
        # setup the query params for the API
        #TODO: Ideally we should paginate and fetch all the pull requests. But for now, 
        # we are fetching only the first 1000 pull requests for the user since we want yearly data
        # and a dev will likely not have more than 1000 PRs in a year.
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
            stats_for_dev['pr_count'] = 0
            stats_for_dev['pr_list'] = []

            for pr in pull_requests['values']:
                prCreatedDate = pr['createdDate']
                # check if the PR was created in the given date range (inclusive)
                if startDateTimestampMilliSec <= prCreatedDate <= endDateTimestampMilliSec:
                    stats_for_dev['pr_count'] = stats_for_dev.get('pr_count', 0) + 1
                    pr_info = {}
                    pr_info['title'] = pr['title']
                    pr_info['author'] = pr['author']['user']['name']
                    pr_info['state'] = pr['state']
                    pr_info['created_date'] = convert_timestamp_to_date(pr['createdDate'])
                    pr_info['dest_branch'] = pr['toRef']['displayId']
                    pr_info['repo'] = pr['toRef']['repository']['name']
                    pr_info['pr_link'] = pr['links']['self'][0]['href']
                    stats_for_dev['pr_list'].append(pr_info)
                    #print(f"Title: {pr['title']}, Author: {pr['author']['user']['name']}  State: {pr['state']}, Created on: {pr['createdDate']}")
            
            stats['pr_count'] += stats_for_dev['pr_count']
            stats[username] = stats_for_dev
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
    output_file = config_data.get('output_file', "pr_stats_output.json")

    print(f"Fetching pull request stats for the period {start_date_str} to {end_date_str}")

    stats = fetch_pull_request_stats(bitbucket_server_fqdn, bearer_token, username_list, start_date_str, end_date_str)
    with open(output_file, 'w') as file:
        json.dump(stats, file, indent=2)



