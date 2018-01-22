"""
This script reads bond info from a google spreadsheet and calculates their
current values by using the treasury department's online bond calculator.
See https://www.treasurydirect.gov/BC/SBCPrice for more info.
"""
import argparse
import collections
from datetime import datetime
import httplib2
import httplib
import math
import sys
import threading
import urllib

from BeautifulSoup import BeautifulSoup
from apiclient import discovery
from oauth2client import client
from oauth2client import tools
from oauth2client.file import Storage
import plotly


Bond = collections.namedtuple(
    'Bond',
    'denom,issue_date,next_actual,final_maturity,issue_price,gain_amount,'
    'interest_rate,value'
)


def fetch_bond_value(bonds, face_value, date, serial):
  """Given bond description, calculates bond value via treasury dpmt website.

  See https://www.treasurydirect.gov/BC/SBCPrice for more info.
  """
  params = urllib.urlencode({
      'Series': 'EE',
      'btnAdd.x': 'CALCULATE',
      'IssueDate': date,
      'Denomination': face_value,
      'SerialNumber': serial,
  })
  headers = {
      "Content-type": "application/x-www-form-urlencoded",
      "Accept": "text/plain",
  }

  conn = httplib.HTTPSConnection("www.treasurydirect.gov")
  conn.request("POST", "/BC/SBCPrice", params, headers)
  r1 = conn.getresponse()
  data1 = r1.read()

  parsed_html = BeautifulSoup(data1)
  tbl =  parsed_html.find("table", {"class" : "bnddata"})
  row = tbl.find('tr', {"class": "altrow1"})
  cells = row.findAll('td')

  b = Bond(
    int(cells[2].getText()[1:]),
	  cells[3].getText(),
	  cells[4].getText(),
	  cells[5].getText(),
	  float(cells[6].getText()[1:]),
	  cells[7].getText(),
	  float(cells[8].getText()[:-1])/100,
	  float(cells[9].getText()[1:]),
  )
  bonds.append(b)


def get_creds(path_to_token, path_to_creds):
  """Auths with google apis.

  Returns an auth'ed http client."""
  scopes = 'https://www.googleapis.com/auth/spreadsheets.readonly'
  APPLICATION_NAME = 'some app'

  store = Storage(path_to_token)
  credentials = store.get()
  if not credentials or credentials.invalid:
	flow = client.flow_from_clientsecrets(path_to_creds, scopes)
	flow.user_agent = APPLICATION_NAME
	credentials = tools.run_flow(flow, store, None)

  return credentials.authorize(httplib2.Http())


def fetch_spreadsheet(http, sheet_id, worksheet_name):
  """Fetches bond info from a google spreadsheet

  Format: 1st row column headers for face value, issue date, serial num.
          Remaining rows are values.
  """
  discoveryUrl = 'https://sheets.googleapis.com/$discovery/rest?version=v4'
  service = discovery.build(
      'sheets', 'v4', http=http, discoveryServiceUrl=discoveryUrl)
  result = service.spreadsheets().values().get(
      spreadsheetId=sheet_id, range=worksheet_name).execute()
  return result.get('values', [])


def calc_interest(c, r, n, t):
  """Attempts to calculate the interest gained on a bond given:
  Args:
    c: Initial payment.
    r: Interest rate.
    n: How many paymnets per year. (Always 2 for bonds)
    t: How many years.
  """
  return c * math.pow(1 + (r/n), n*t)


def how_many_payments(s_date):
  """How many biannual interest payments between now and the given date."""
  today = datetime.today()
  assert len(s_date) == 7, '%s not right' % s_date
  assert s_date[2:3] == '/',  '%s not right' % s_date
  month = s_date[0:2]
  year = s_date[3:8]
  date_of_purchase = datetime(int(year), int(month), 1)
  months = (
      (12 * (today.year - date_of_purchase.year)) +
      (today.month - date_of_purchase.month))
  return int(math.floor(float(months) / 6.0))


def main():
  parser = argparse.ArgumentParser()
  parser.add_argument(
      'sheet_id', type=str, help='Google sheets id to pull bond info from.')
  parser.add_argument(
      'sheet_name', type=str,
      help='Worksheet name that contains the bond info.')
  parser.add_argument(
      'path_to_token', type=str,
      help='Path to json file containing token for authing with google apis.')
  parser.add_argument(
      'path_to_creds', type=str,
      help='Path to json file containing creds for authing with google apis.')
  args = parser.parse_args()

  http = get_creds(args.path_to_token, args.path_to_creds)
  values = fetch_spreadsheet(http, args.sheet_id, args.sheet_name)

  threads = []
  print 'bonds:'
  for v in values[1:]:
    value = v[0]
    date = v[1]
    serial = v[2]
    print value, date, serial

  bonds = []
  for v in values[1:]:
    value = v[0]
    date = v[1]
    serial = v[2]
    t = threading.Thread(
        target=fetch_bond_value, args=(bonds, value, date, serial))
    t.start()
    threads.append(t)

  for t in threads:
    t.join()

  def _date_to_timestamp(bond):
    s_date = bond.issue_date
    month = s_date[0:2]
    year = s_date[3:8]
    date = datetime(int(year), int(month), 1)
    return (date - datetime(1970,1,1)).total_seconds()
  bonds = sorted(bonds, key=_date_to_timestamp)

  print '\n\nbond values:'
  print '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s' % (
      'denom', 'date of purchase', 'next actual', 'final maturity',
      'issue price', 'interest', 'interest rate', 'value')
  for b in bonds:
    print '%s\t%s\t\t\t%s\t\t%s\t\t%s\t\t%s\t\t%s \t\t%s' % (
        b.denom, b.issue_date, b.next_actual, b.final_maturity, b.issue_price,
        b.gain_amount, b.interest_rate, b.value)

  # Below code doesn't really work. Left it in just in case.
  # print '\n\nresults:'
  # print 'denom\tdate of purchase\tissue price\tinterest rate\tvalue\t\texpected value'
  # for b in bonds:
    # expected_value = calc_interest(b.issue_price, b.interest_rate, 2, how_many_payments(b.issue_date))
    # print '%s\t%s\t\t\t%s\t\t%s\t\t%s\t\t%s' % (b.denom, b.issue_date, b.issue_price, b.interest_rate, b.value, expected_value)


if __name__ == '__main__':
  sys.exit(main())