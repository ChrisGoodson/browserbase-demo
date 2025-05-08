from flask import Flask, jsonify, render_template
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
from browserbase import Browserbase
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
bb = Browserbase(api_key=os.getenv("BROWSERBASE_API_KEY"))

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/run-automation", methods=["POST"])
def run_automation():
    project_id = os.getenv("BROWSERBASE_PROJECT_ID")
    session = bb.sessions.create(project_id=project_id)
    session_id = session.id
    connect_url = session.connect_url

    static_dir = os.path.join(os.getcwd(), "static")
    os.makedirs(static_dir, exist_ok=True)

    sites = [
        {"name": "Hacker News", "url": "https://news.ycombinator.com"},
        {"name": "GitHub Trending", "url": "https://github.com/trending"},
        {"name": "Python.org", "url": "https://www.python.org"},
        {"name": "Browserbase", "url": "https://browserbase.com"},
    ]

    pages = []
    with sync_playwright() as pw:
        browser = pw.chromium.connect_over_cdp(connect_url)
        page = browser.contexts[0].pages[0]
        page.set_default_navigation_timeout(60000)
        page.set_default_timeout(60000)

        for idx, site in enumerate(sites):
            try:
                page.goto(site["url"], timeout=60000)
                page.wait_for_load_state("networkidle", timeout=60000)
                title = page.title()
                fn = f"screenshot_{idx}.png"
                fp = os.path.join(static_dir, fn)
                page.screenshot(path=fp, full_page=True)
                pages.append({
                    "name": site["name"],
                    "url": site["url"],
                    "title": title,
                    "screenshot_url": f"/static/{fn}"
                })
            except PlaywrightTimeoutError:
                pages.append({"name": site["name"], "url": site["url"], "title": "⚠️ Timeout", "screenshot_url": None})
            except Exception as e:
                pages.append({"name": site["name"], "url": site["url"], "title": f"Error: {e}", "screenshot_url": None})

        page.close()
        browser.close()

    replay_url = f"https://browserbase.com/sessions/{session_id}"
    return jsonify(status="success", pages=pages, replay_url=replay_url)

if __name__ == "__main__":
    app.run(debug=True)
