```
usage: nr jiratime [-h] [--assignee ASSIGNEE] [--closed] [--from FROM_]
                   [--to TO]
                   host auth

positional arguments:
  host                 The JIRA issue tracker hostname.
  auth                 Credentials in the form of <username>:<password>

optional arguments:
  -h, --help           show this help message and exit
  --assignee ASSIGNEE  Filter by assignee.
  --closed             Calculate based only on closed issues.
  --from FROM_         Only include issues resolved from this day or newer.
  --to TO              Only include issues resolved up to this day or older.
```
