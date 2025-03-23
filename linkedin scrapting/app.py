import re
import time
from flask import Flask, render_template, jsonify, request
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from bs4 import BeautifulSoup

app = Flask(__name__)

# --- Configuration ---
LINKEDIN_EMAIL = "fusionlab79@gmail.com"
LINKEDIN_PASSWORD = "Mumbai@123"
# List of LinkedIn profile URLs to scrape
USER_PROFILE_URLS = [
    "https://www.linkedin.com/in/nikhil-kanojiya-a80858290/",
    "https://www.linkedin.com/in/sanket-rasal-b7873225a/",
    "https://www.linkedin.com/in/nehachandane/"
]
SELENIUM_HEADLESS = True  # Set to True for server, False for local testing

# --- Selenium Setup Functions ---
def setup_driver():
    options = webdriver.ChromeOptions()
    if SELENIUM_HEADLESS:
        options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    driver = webdriver.Chrome(options=options)
    return driver

def login_to_linkedin(driver):
    driver.get("https://www.linkedin.com/login")
    time.sleep(2)
    driver.find_element(By.ID, "username").send_keys(LINKEDIN_EMAIL)
    driver.find_element(By.ID, "password").send_keys(LINKEDIN_PASSWORD + Keys.RETURN)
    time.sleep(5)

def scroll_page(driver, scrolls=3, pause=3):
    for _ in range(scrolls):
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(pause)

def clean_text(raw_text):
    text = re.sub(r"Feed post number\s*\d+\s*", "", raw_text, flags=re.IGNORECASE)
    text = re.sub(r"\s+", " ", text)
    return text.strip()

def extract_post_number(text):
    match = re.search(r"Feed post number\s*(\d+)", text, flags=re.IGNORECASE)
    return int(match.group(1)) if match else ""

def scrape_user_posts_for_profile(profile_url):
    driver = setup_driver()
    try:
        login_to_linkedin(driver)
        # Navigate to the user's shares page
        if "recent-activity/shares" not in profile_url:
            posts_url = profile_url.rstrip("/") + "/detail/recent-activity/shares/"
        else:
            posts_url = profile_url
        driver.get(posts_url)
        time.sleep(5)
        scroll_page(driver, scrolls=3, pause=3)
        soup = BeautifulSoup(driver.page_source, "html.parser")
        posts = soup.find_all("div", class_="occludable-update")
        if not posts:
            posts = soup.find_all("div", class_="feed-shared-update-v2")
        post_list = []
        for post in posts:
            raw_text = post.get_text(separator=" ", strip=True)
            cleaned = clean_text(raw_text)
            post_num = extract_post_number(raw_text)
            img_tags = post.find_all("img")
            images = []
            for img in img_tags:
                url = img.get("src")
                if url:
                    # Filter to keep only post images
                    if (("dms/image" in url or "media.licdn.com/media" in url)
                        and "profile-framedphoto" not in url
                        and "aero-v1/sc/h/" not in url):
                        images.append(url)
            post_list.append({
                "profile": profile_url,
                "post_number": post_num,
                "post": cleaned,
                "images": images
            })
        return post_list
    finally:
        driver.quit()

# --- Flask Routes ---
@app.route("/")
def index():
    # Only show first two profiles as cards
    cards = USER_PROFILE_URLS[:2]
    return render_template("index.html", cards=cards)

@app.route("/api/profile")
def api_profile():
    profile_url = request.args.get("url")
    if not profile_url:
        return jsonify({"error": "No profile URL provided"}), 400
    posts = scrape_user_posts_for_profile(profile_url)
    return jsonify(posts)

if __name__ == "__main__":
    app.run(debug=True)
