import csv
import requests

def fetch_google_sheet_csv(sheet_url):
    """
    Fetches a public Google Sheet as CSV and returns a list of dicts (rows).
    sheet_url: The 'export?format=csv' URL of the public Google Sheet.
    """
    response = requests.get(sheet_url)
    response.raise_for_status()
    decoded = response.content.decode('utf-8')
    reader = csv.DictReader(decoded.splitlines())
    return list(reader)
