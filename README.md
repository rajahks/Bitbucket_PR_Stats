# Bitbucket_PR_Stats
Scripts to fetch PR stats using Bitbucket APIs

**Setup:**
1) Install Python 3.
2) (Optional) Create a virtual environment:
   ```python
   python -m venv venv
   ```
3) (Optional) Activate the virtual environment:
   ```python
   .\venv\Scripts\activate
   ```
4) Install the required packages:
   ```python
   python -m pip install -r requirements.txt
   ```
5) Update the value of `bitbucket_server_fqdn` in `config.json`. For example: `code.myorg.net`.
6) Update `bearer_token` with your HTTP access tokens created on Bitbucket.
7) Update `username_list` with the list of usernames you want to fetch PR stats for.
8) Optionally, update `output_json_file` and `output_excel_file` to specify the output file names.

**Usage:**
```python
python PR_stats.py <start_date> <end_date>
```
The dates should be in the format `YYYY-MM-DD`.
Example: `python PR_stats.py 2024-03-06 2024-03-13`

**Output:**
- `output_json_file`: The JSON file where the PR stats will be saved. Default is `pr_stats_output.json`.
- `output_excel_file`: The Excel file where the PR stats will be saved. Default is `pr_stats_output.xlsx`.

**Note:**
The script is used to get PR stats made by a dev. The script hardcodes max PRs to fetch to be around 1000 latest PRs. This is assuming that the script will be usually used to fetch details for a timeframe of week, month or max about a year.
1000 is still a huge number and should mostly suffice. It can be overcome by refining the code.