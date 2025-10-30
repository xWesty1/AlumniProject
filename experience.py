from linkedin_scraper import Person, actions
from selenium import webdriver

driver = webdriver.Chrome()
email = "jackwesterhaus@gmail.com"
password = "123abcJgc!"
actions.login(driver, email, password)

raw_url = "https://www.linkedin.com/in/nicholas-paul-689320311?miniProfileUrn=urn%3Ali%3Afs_miniProfile%3AACoAAE8_WckBVu1JeOqlS5Jrz11uGWJEdOQACiA"
profile_url = raw_url.split("?", 1)[0]  # strip query params

person = Person(profile_url, driver=driver)
print(person.company, person.job_title)
print("Profile URL: ", profile_url)

