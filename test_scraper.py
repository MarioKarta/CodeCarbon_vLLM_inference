# test_gcp_pue_scraper.py

"""
Test script for the Google‐HTML PUE scraper (fetch_google_html_pue).

Usage:
    python test_gcp_pue_scraper.py

Make sure you have installed the required dependencies:
    pip install requests beautifulsoup4

You should have a file named gcp_pue.py in the same folder, containing:
    def fetch_google_html_pue(facility_name: str) -> float
"""

from gcp_pue import fetch_google_html_pue

def main():
    # List of sample GCP facility names to test. You can adjust these to match
    # whatever Google Data Center facility you want to verify.
    #
    # Note: On Google’s page, facility names often appear exactly as:
    #   "The Dalles, Oregon (2nd facility)"
    #   "Eemshaven, Netherlands"
    #   "Council Bluffs, Iowa"
    #   "St. Ghislain, Belgium"
    #   "Douglas County, Georgia"
    #   "Hong Kong, Asia"
    #
    # You can run `fetch_google_html_pue(...)` on any of these or partial matches
    # (e.g., "The Dalles" will match "The Dalles, Oregon (2nd facility)").
    sample_facilities = [
        "The Dalles, Oregon",
        "Eemshaven, Netherlands",
        "St. Ghislain, Belgium",
        "Nonexistent Facility Name"  # to test the fallback behavior
    ]

    print("=== Testing Google‐HTML PUE Scraper ===\n")

    for name in sample_facilities:
        pue = fetch_google_html_pue(facility_name=name)
        if pue == 1.0:
            # We treat 1.0 as the default fallback (either no match or error)
            print(f"[Result] Facility '{name}' → PUE not found or error; defaulted to PUE = 1.0")
        else:
            print(f"[Result] Facility '{name}' → PUE = {pue:.3f}")

    print("\n=== End of Test ===")


if __name__ == "__main__":
    main()
