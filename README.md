# Bitbucket_PR_Stats
Scripts to fetch PR stats using bitbucket APIs

**Setup:**
1) Install Python3
2) python -m pip install requirements.txt
3) Update dashboard_api_url in config.json. Replace "bitbucketdomain" with the FQDN of your bitbucket instance. Eg: code.myorg.net
4) Update bearer_token_list with the HTTP access tokens for each user you want to fetch data for.

**Usage:**
```python
python PR_stats.py <start_date> <end_date>
```
The dates should be in the format YYYY-MM-DD

Example: python PR_stats.py 2024-03-06 2024-03-13


