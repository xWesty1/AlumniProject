import sys
import csv
import urllib.parse
from typing import List, Tuple, Dict

sys.path.insert(0, "/Users/jackson/Desktop/AlumniProject/linkedin_scraper")

from linkedin_scraper import Person, actions
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, StaleElementReferenceException, NoSuchElementException


ALUMNI_CSV_PATH = "/Users/jackson/Desktop/AlumniProject/alumni.csv"
URLS_OUTPUT_CSV_PATH = "/Users/jackson/Desktop/AlumniProject/alumni_urls.csv"


def load_last_n_alumni(file_path: str, n: int = None, reverse: bool = False) -> List[Dict[str, str]]:
    with open(file_path, newline="", encoding="utf-8") as f:
        reader = list(csv.DictReader(f))
        # take the last n non-empty name rows (or all if n is None)
        selected: List[Dict[str, str]] = []
        for row in reversed(reader):
            first = (row.get("Preferred First Name") or "").strip()
            last = (row.get("Last Name") or "").strip()
            if first and last:
                selected.append(row)
            if n is not None and len(selected) == n:
                break
        # If reverse=True, keep reversed order; otherwise restore chronological order
        return selected if reverse else list(reversed(selected))


def build_full_name(row: Dict[str, str]) -> str:
    first = (row.get("Preferred First Name") or "").strip()
    last = (row.get("Last Name") or "").strip()
    return f"{first} {last}".strip()


def _to_xpath_literal(value: str) -> str:
    """Return an XPath string literal for the given value, handling quotes safely.
    Uses single or double quotes when possible, otherwise builds a concat().
    """
    if "'" not in value:
        return f"'{value}'"
    if '"' not in value:
        return f'"{value}"'
    parts = value.split("'")
    tokens: List[str] = []
    for i, part in enumerate(parts):
        if i > 0:
            tokens.append("\"'\"")  # literal single quote
        if part:
            tokens.append(f"'{part}'")
    return "concat(" + ", ".join(tokens) + ")"


def get_top_profile_url(driver: webdriver.Chrome, full_name: str, wait_seconds: int = 8) -> str:
    wait = WebDriverWait(driver, wait_seconds)
    # Prefer exact visible name, else take the first profile link
    name_literal = _to_xpath_literal(full_name)
    exact_xpath = (
        "(//a[contains(@href, '/in/')][.//span[@dir='ltr' and normalize-space()="
        f"{name_literal}"
        "]])[1]"
    )
    fallback_xpath = "(//a[contains(@href, '/in/')])[1]"
    
    # Also check for "no results" message
    no_results_xpath = "//*[contains(text(), 'No results found') or contains(text(), 'no results')]"
    
    try:
        link = wait.until(EC.presence_of_element_located((By.XPATH, exact_xpath)))
    except TimeoutException:
        # Check if there are no results at all
        try:
            driver.find_element(By.XPATH, no_results_xpath)
            raise ValueError("No LinkedIn profile found")
        except NoSuchElementException:
            pass
        
        # Try fallback to any profile link
        try:
            link = wait.until(EC.presence_of_element_located((By.XPATH, fallback_xpath)))
        except TimeoutException:
            raise ValueError("No LinkedIn profile found")
    
    return link.get_attribute("href")


def search_and_get_profile_url(driver: webdriver.Chrome, full_name: str) -> str:
    # Include University of Minnesota in search to filter results
    search_query = f"{full_name} University of Minnesota"
    search_url = (
        "https://www.linkedin.com/search/results/people/?keywords="
        + urllib.parse.quote(search_query)
    )
    driver.get(search_url)
    return get_top_profile_url(driver, full_name)


def scrape_profile_from_url(profile_url: str, email: str, password: str) -> Person:
    driver = webdriver.Chrome()
    actions.login(driver, email, password)
    person = Person(profile_url, driver=driver)
    return person


def main():
    driver = webdriver.Chrome()

    # Credentials: if omitted, actions.login will prompt securely in terminal
    email = "jackwesterhaus@gmail.com"
    password = "123abcJgc!"
    actions.login(driver, email, password)

    # Load ALL alumni in reverse order (newest first)
    alumni_rows = load_last_n_alumni(ALUMNI_CSV_PATH, n=None, reverse=True)
    total_count = len(alumni_rows)
    
    # Skip already processed alumni (ended at position 411)
    # Restarting from position 412: Patrick Carroll
    START_POSITION = 411  # Already processed positions 1-411
    alumni_rows = alumni_rows[START_POSITION:]
    print(f"\nLoaded {total_count} total alumni.")
    print(f"Starting from position {START_POSITION + 1} (already processed {START_POSITION}).\n")

    # Load existing results from CSV to preserve them
    results: List[Dict[str, str]] = []
    fieldnames = [
        "Preferred First Name",
        "Last Name",
        "LinkedIn URL",
    ]
    
    try:
        with open(URLS_OUTPUT_CSV_PATH, "r", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                results.append(row)
        print(f"Loaded {len(results)} existing results from CSV.\n")
    except FileNotFoundError:
        print("No existing results file found. Starting fresh.\n")
    
    try:
        for index, row in enumerate(alumni_rows, start=1):
            full_name = build_full_name(row)
            display_index = START_POSITION + index  # Adjust for already processed entries
            print(f"[{display_index}/{total_count}] Searching for {full_name}...", end=" ")
            
            try:
                profile_url = search_and_get_profile_url(driver, full_name)
                print(f"✓ Found")
                results.append(
                    {
                        "Preferred First Name": row.get("Preferred First Name", ""),
                        "Last Name": row.get("Last Name", ""),
                        "LinkedIn URL": profile_url,
                    }
                )
                
                # Save after each profile
                with open(URLS_OUTPUT_CSV_PATH, "w", newline="", encoding="utf-8") as f:
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writeheader()
                    for r in results:
                        writer.writerow(r)
                    
            except ValueError as e:
                if "No LinkedIn profile found" in str(e):
                    print(f"✗ No LinkedIn found")
                    results.append(
                        {
                            "Preferred First Name": row.get("Preferred First Name", ""),
                            "Last Name": row.get("Last Name", ""),
                            "LinkedIn URL": "NO LINKEDIN FOUND",
                        }
                    )
                else:
                    print(f"✗ Error: {str(e)}")
                    results.append(
                        {
                            "Preferred First Name": row.get("Preferred First Name", ""),
                            "Last Name": row.get("Last Name", ""),
                            "LinkedIn URL": f"ERROR: {str(e)}",
                        }
                    )
                
                # Save after each profile (including errors)
                with open(URLS_OUTPUT_CSV_PATH, "w", newline="", encoding="utf-8") as f:
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writeheader()
                    for r in results:
                        writer.writerow(r)
                        
            except Exception as e:
                print(f"✗ Error: {str(e)}")
                # Add entry with error note
                results.append(
                    {
                        "Preferred First Name": row.get("Preferred First Name", ""),
                        "Last Name": row.get("Last Name", ""),
                        "LinkedIn URL": f"ERROR: {str(e)}",
                    }
                )
                
                # Save after each profile (including errors)
                with open(URLS_OUTPUT_CSV_PATH, "w", newline="", encoding="utf-8") as f:
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writeheader()
                    for r in results:
                        writer.writerow(r)

    finally:
        # Do not close inside Person; we handle it here
        driver.quit()

    # Write final results
    with open(URLS_OUTPUT_CSV_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in results:
            writer.writerow(r)

    print(f"\n✓ Completed! Collected {len(results)} profiles.")
    print(f"Results saved to: {URLS_OUTPUT_CSV_PATH}")


if __name__ == "__main__":
    main()

## TODO Split the urls, it's in test.py