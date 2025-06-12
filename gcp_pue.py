import requests
from bs4 import BeautifulSoup

def fetch_google_html_pue(facility_name: str) -> float:
    """
    Scrapes Google's Data Center Efficiency page to get the
    trailing twelve-month PUE for the given facility name,
    e.g. "The Dalles, Oregon (2nd facility)" → 1.06.
    Returns 1.0 if the facility is not found or on any error.
    """
    URL = "https://www.google.com/about/datacenters/efficiency/"
    try:
        resp = requests.get(URL, timeout=10)
        resp.raise_for_status()
    except Exception as e:
        print(f"[WARN] Could not fetch Google efficiency page: {e}")
        return 1.0

    soup = BeautifulSoup(resp.text, "html.parser")

    # NOTE: Google’s HTML structure can change; verify selectors if this breaks.
    # Look for a <table> whose rows look like: <td>Facility Name</td><td>Quarterly</td><td>TTM</td>
    table = soup.find("table")
    if table is None:
        print("[WARN] No <table> found on Google efficiency page.")
        return 1.0

    for row in table.find_all("tr"):
        cols = row.find_all("td")
        if len(cols) < 3:
            continue
        name = cols[0].get_text(strip=True)
        if facility_name in name:
            ttm_pue_str = cols[2].get_text(strip=True)
            try:
                return float(ttm_pue_str)
            except ValueError:
                print(f"[WARN] Unable to parse PUE '{ttm_pue_str}' for {facility_name}")
                return 1.0

    print(f"[WARN] Facility '{facility_name}' not found; defaulting to PUE=1.0")
    return 1.0