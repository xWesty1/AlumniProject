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
from selenium.common.exceptions import TimeoutException, StaleElementReferenceException


ALUMNI_CSV_PATH = "/Users/jackson/Desktop/AlumniProject/alumni.csv"
URLS_OUTPUT_CSV_PATH = "/Users/jackson/Desktop/AlumniProject/alumni_urls.csv"


def load_last_n_alumni(file_path: str, n: int = 3) -> List[Dict[str, str]]:
    with open(file_path, newline="", encoding="utf-8") as f:
        reader = list(csv.DictReader(f))
        # take the last n non-empty name rows
        selected: List[Dict[str, str]] = []
        for row in reversed(reader):
            first = (row.get("Preferred First Name") or "").strip()
            last = (row.get("Last Name") or "").strip()
            if first and last:
                selected.append(row)
            if len(selected) == n:
                break
        return list(reversed(selected))  # restore chronological order among the selected


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


def get_top_profile_url(driver: webdriver.Chrome, full_name: str, wait_seconds: int = 15) -> str:
    wait = WebDriverWait(driver, wait_seconds)
    # Prefer exact visible name, else take the first profile link
    name_literal = _to_xpath_literal(full_name)
    exact_xpath = (
        "(//a[contains(@href, '/in/')][.//span[@dir='ltr' and normalize-space()="
        f"{name_literal}"
        "]])[1]"
    )
    fallback_xpath = "(//a[contains(@href, '/in/')])[1]"
    try:
        link = wait.until(EC.presence_of_element_located((By.XPATH, exact_xpath)))
    except TimeoutException:
        link = wait.until(EC.presence_of_element_located((By.XPATH, fallback_xpath)))
    return link.get_attribute("href")


def search_and_get_profile_url(driver: webdriver.Chrome, full_name: str) -> str:
    search_url = (
        "https://www.linkedin.com/search/results/people/?keywords="
        + urllib.parse.quote(full_name)
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

    alumni_rows = load_last_n_alumni(ALUMNI_CSV_PATH, n=3)

    results: List[Dict[str, str]] = []
    try:
        for row in alumni_rows:
            full_name = build_full_name(row)
            profile_url = search_and_get_profile_url(driver, full_name)
            results.append(
                {
                    "Preferred First Name": row.get("Preferred First Name", ""),
                    "Last Name": row.get("Last Name", ""),
                    "LinkedIn URL": profile_url,
                }
            )

    finally:
        # Do not close inside Person; we handle it here
        driver.quit()

    # Write results
    fieldnames = [
        "Preferred First Name",
        "Last Name",
        "LinkedIn URL",
    ]
    with open(URLS_OUTPUT_CSV_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in results:
            writer.writerow(r)

    # Also print to console for quick visibility
    for r in results:
        print(
            f"{r['Preferred First Name']} {r['Last Name']}: {r['LinkedIn URL']}"
        )


if __name__ == "__main__":
    main()