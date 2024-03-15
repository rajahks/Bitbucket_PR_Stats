# Bitbucket_PR_Stats
Scripts to fetch PR stats using bitbucket APIs

**Setup:**
1) Install Python3
2) python -m pip install -r requirements.txt
3) Update dashboard_api_url in config.json. Replace "bitbucketdomain" with the FQDN of your bitbucket instance. Eg: code.myorg.net
4) Update bearer_token_list with the HTTP access tokens for each user you want to fetch data for.

**Usage:**
```python
python PR_stats.py <start_date> <end_date>
```
The dates should be in the format YYYY-MM-DD
Example: python PR_stats.py 2024-03-06 2024-03-13

The json output will be dumped into pr_stats_output.json or the file you specify in config.json

**Note:**

The `PR_stats.py` is written targetting Bitbucket instances which does not support the "user" param on the Dashboard API. 
Without it, the API only returns PRs for logged in user.
To get stats for multipler users, we are using tokens from multiple users.

To target Bitbucket instances which support the "user" param, we would just need one user's token
and can query the PR stats of any user. To do this the script will need to be modified to pass the
username of the target user in params to `fetch_pull_requests_for_a_user`
Refer: https://developer.atlassian.com/server/bitbucket/rest/v818/api-group-dashboard/#api-api-latest-dashboard-pull-requests-get
