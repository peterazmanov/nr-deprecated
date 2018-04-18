# The MIT License (MIT)
#
# Copyright (c) 2018 Niklas Rosenstein
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
"""
Sum up the logged work for a user in JIRA issues.
"""

from __future__ import print_function, division
import argparse
import getpass
import requests
import sys


class JIRA:

  def __init__(self, host, auth):
    self.host = host
    self.session = requests.Session()
    self.session.auth = auth
    self.session.headers['Content-Type'] = 'application/json'

  @property
  def url(self):
     return 'https://{}/rest/api/2/'.format(self.host)

  def search(self, jql, start_at=0, max_results=50):
    params = {'jql': jql, 'maxResults': str(max_results), 'startAt': str(start_at)}
    response = self.session.get(self.url + 'search', params=params)
    response.raise_for_status()
    return response.json()


def main(prog=None, argv=None):
  parser = argparse.ArgumentParser(prog=prog)
  parser.add_argument('host', help='The JIRA issue tracker hostname.')
  parser.add_argument('auth', help='Credentials in the form of <username>:<password>')
  parser.add_argument('--assignee', help='Filter by assignee.')
  parser.add_argument('--closed', action='store_true', help='Calculate based only on closed issues.')
  parser.add_argument('--from', dest='from_', help='Only include issues resolved from this day or newer.')
  parser.add_argument('--to', help='Only include issues resolved up to this day or older.')
  args = parser.parse_args(argv)
  username, password = args.auth.partition(':')[::2]
  if not password:
    password = getpass.getpass()
    if not password: return 0

  jira = JIRA(args.host, (username, password))

  query_parts = []
  if args.assignee:
    query_parts.append('assignee="{}"'.format(args.assignee))
  if args.closed:
    query_parts.append('status=closed')
  if args.from_:
    query_parts.append('resolutiondate >= {}'.format(args.from_))
  if args.to:
    query_parts.append('resolutiondate <= {}'.format(args.to))

  query = ' AND '.join(query_parts)
  print('$ JQL:', query)

  # Retrieve all issues matching the query.
  issues = []
  start_at = 0
  while True:
    response = jira.search(query, start_at=len(issues))
    issues.extend(response['issues'])
    if response['total'] <= response['startAt'] + response['maxResults']:
      break

  print('Found {} matching issues.'.format(len(issues)))

  seconds = 0
  for issue in issues:
    resolution = issue['fields']['resolutiondate'].split('T')[0] \
      if issue['fields']['resolutiondate'] else None
    timespent = issue['fields']['timespent'] or 0
    print('  {} -- {} ({}s, resolution={})'.format(
      issue['key'], issue['fields']['summary'], timespent,
      resolution))
    seconds += timespent

  print('Time spent: {}s (={}h)'.format(seconds, seconds/3600))


if __name__ == '__main__':
  sys.exit(main())
