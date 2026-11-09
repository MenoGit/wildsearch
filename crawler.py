"""
Web Crawler
Run with:  python3 crawler.py
"""

import os
import csv
import json
import time
from collections import deque
from html.parser import HTMLParser
from urllib.parse import urljoin, urldefrag, urlparse, quote
from urllib.robotparser import RobotFileParser
from urllib.error import HTTPError
from email.utils import parsedate_to_datetime
import urllib.request


#settings

SKIP_URLS = {
    "https://www.fws.gov/policy/library/2019/2019-27334.html"
}

SEED_URLS = [
    "https://wdfw.wa.gov/hunting",
    "https://myodfw.com/",
    "https://www.fws.gov/",
    "https://www.nps.gov/"
]

ALLOWED_DOMAINS = {
    "wdfw.wa.gov",
    "myodfw.com",
    "www.fws.gov",
    "www.nps.gov"
}

MAX_PAGES = 100_000 
DELAY = 1.0                            #seconds between requests
TIMEOUT = 10                           #seconds before giving up on a page
USER_AGENT = "CS454StudentCrawler/1.0"
DATA_DIR = "data"
PAGES_DIR = "data/pages"

CHECKPOINT_FILE = os.path.join(DATA_DIR, "checkpoint.json") 
CHECKPOINT_INTERVAL = 100 


#html parsing

class PageParser(HTMLParser):

    def __init__(self):
        HTMLParser.__init__(self)
        self.text_parts = []
        self.links = []
        self.skipping = 0              #above 0 while inside <script>/<style>

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "noscript"):
            self.skipping = self.skipping + 1
        if tag == "a":
            for name, value in attrs:
                if name == "href" and value is not None:
                    self.links.append(value)

    def handle_endtag(self, tag):
        if tag in ("script", "style", "noscript") and self.skipping > 0:
            self.skipping = self.skipping - 1

    def handle_data(self, data):
        #only the text a reader would see not the code
        if self.skipping == 0 and data.strip() != "":
            self.text_parts.append(data.strip())

    def get_text(self):
        return " ".join(self.text_parts)


#url cleanup and filtering

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None
opener = urllib.request.build_opener(NoRedirect)

def clean_url(page_url, href):
    #relative to absolute, drop the #part, escape accents
    full = urljoin(page_url, href)
    full = urldefrag(full)[0]
    return quote(full, safe=":/?#[]@!$&'()*+,;=%~")


def is_allowed(url, allowed_domains):
    parts = urlparse(url)
    if parts.scheme not in ("http", "https"):
        return False                   #drops mailto:, tel:, javascript:
    if parts.netloc not in allowed_domains:
        return False
    return True


#robots.txt and downloading

def load_robots(site):
    #returns None if it can't be read and then we don't crawl at all
    robots = RobotFileParser()
    try:
        request = urllib.request.Request(site + "/robots.txt",
                                         headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
            raw = response.read()
        robots.parse(raw.decode("utf-8", "replace").splitlines())
    except Exception as error:
        print("Could not read robots.txt: " + str(error))
        return None
    return robots


def get_retry_delay(error):
    retry_after = error.headers.get("Retry-After")
    if retry_after:
        try:
            return max(0, int(retry_after))
        except ValueError:
            try:
                retry_time = parsedate_to_datetime(retry_after)
                return max(0, retry_time.timestamp()-time.time())
            except (ValueError, TypeError, OverflowError):
                pass
    return 10.0

def download(url):
    for attempt in range(2):
        try:
            request = urllib.request.Request(
                    url,
                    headers={"User-Agent": USER_AGENT}
            )

            with opener.open(request, timeout=TIMEOUT) as response:
                if "text/html" not in response.headers.get("Content-Type", "").lower():
                    print("Skipped: non-HTML page " + url)
                    return None, None


                html = response.read().decode("utf-8", "replace")
                return "success", html

        except HTTPError as error:
            if error.code in (301, 302, 303, 307, 308):
                location = error.headers.get("Location")

                if location:
                    destination = clean_url(url, location)
                    print("Redirect:", url, "->", destination)
                    return "redirect", destination
            
            if error.code in (429, 503):
                delay = get_retry_delay(error)
                if attempt == 0 and delay <= 60:
                    print("HTTP", error.code, "- retrying after", delay, "seconds")
                    time.sleep(delay)
                    continue

                print("HTTP", error.code, " - pausing crawl:", url)
                return "pause", None

            print("Skipped: HTTP", error.code, url)
            return None, None
        
        except Exception as error:
            print("Skipped:", error, url)
            return None, None


#saving

def save_page(page_id, url, text):
    path = os.path.join(PAGES_DIR, str(page_id) + ".json")
    temp_path = path + ".tmp"

    with open(temp_path, "w", encoding="utf-8") as file:
        json.dump(
                {"id": page_id, "url": url, "text": text},
                file,
                ensure_ascii=False
        )
    os.replace(temp_path, path)



def save_urls(url_to_id):
    #a list so urls[42] is the url of page 42
    urls = [None] * len(url_to_id)
    for url in url_to_id:
        urls[url_to_id[url]] = url
    out = open(DATA_DIR + "/urls.json", "w", encoding="utf-8")
    json.dump(urls, out, ensure_ascii=False, indent=1)
    out.close()


#adjacency matrix

def save_matrix(graph, url_to_id):
    #graph still holds urls, they turn into ids here because during the
    #crawl most pages don't have an id yet
    count = len(url_to_id)

    out = open(DATA_DIR + "/adjacency_matrix.csv", "w", newline="")
    writer = csv.writer(out)
    writer.writerow(["from\\to"] + list(range(count)))

    #one row at a time, 5000 x 5000 is 25 million cells
    for page_id in range(count):
        row = [0] * count
        for link in graph[page_id]:
            if link in url_to_id:
                row[url_to_id[link]] = 1
        writer.writerow([page_id] + row)

    out.close()


#the crawler

def save_edges(graph, url_to_id):
    header = ['source_id','destination_id']
    with open('edges.csv', 'w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow(header)
        
        for key in range(len(url_to_id)):
            for url in graph[key]:
                if url in url_to_id:
                    writer.writerow([key,url_to_id[url]])

def save_checkpoint(queue, seen, url_to_id, graph):
    state = {
            "queue": list(queue),
            "seen": list(seen),
            "url_to_id": url_to_id,
            "graph": graph
            }

    temp_file = CHECKPOINT_FILE + ".tmp"

    with open(temp_file, "w", encoding="utf-8") as file:
        json.dump(state, file)

    os.replace(temp_file, CHECKPOINT_FILE)

    print("Checkpoint saved:", len(url_to_id), "pages")

def load_checkpoint():
    if not os.path.exists(CHECKPOINT_FILE):
        return None

    with open(CHECKPOINT_FILE, "r", encoding="utf-8") as file:
        state = json.load(file)


    state["queue"] = deque(state["queue"])
    state["seen"] = set(state["seen"])

    state["graph"] = {
            int(key): value
            for key, value in state["graph"].items()
    }
    return state


    

def crawl(seed_urls, allowed_domains, max_pages):
    """Crawl breadth-first from seed_urls, staying on allowed_domains,
    and stop after max_pages pages."""
    os.makedirs(PAGES_DIR, exist_ok=True)

    state = load_checkpoint()
    if state is not None:
        queue = state['queue']
        seen = state["seen"]
        url_to_id = state["url_to_id"]
        graph = state["graph"]
        print("Resuming from", len(url_to_id), "pages")
    else:
        queue = deque(seed_urls)
        seen = set(seed_urls)          #already crawled or already in the queue
        url_to_id = {}                 #crawled url -> page id
        graph = {}                     #page id -> the links that page had

        print("Starting a new crawl")

    print("WildSearch crawler")
    print("Seed: " + ", ".join(seed_urls))
    print("Domain: " + ", ".join(allowed_domains))
    print("Target: " + str(max_pages))
    print("")

    #robots = load_robots("https://" + urlparse(seed_urls[0]).netloc)
    robots = {} 

    for seed_url in seed_urls:
        domain = urlparse(seed_url).netloc
        value = load_robots("https://" + domain)
        robots[domain] = value
        #robots.append(load_robots("https://" + urlparse(seed_url).netloc))




    for robot in robots.values():
        if robot is None:
            print("Crawler stopped because robots.txt could not be checked.")
            return

    start = time.time()

    paused = False
    while len(queue) > 0 and len(url_to_id) < max_pages:
        url = queue.popleft()      #off the front so it's fifo which is bfs
        if url in SKIP_URLS:
            print("Skipped: Known unavailable URL", url)
            continue
        
        domain = urlparse(url).netloc
        robot = robots.get(domain)

        if robot is None or not robot.can_fetch(USER_AGENT, url):
            print("Skipped: robots.txt disallowed " + url)
            continue

        status, result = download(url)
        time.sleep(DELAY)

        if status == "pause":
            queue.appendleft(url)
            paused = True
            print("Crawl paused, Progress will be saved.")
            break

        if status == "redirect":
            destination = result

            if is_allowed(destination, allowed_domains):
                if destination not in seen:
                    seen.add(destination)
                    queue.append(destination)
            else:
                print("Skipped: redirect outside allowed domains", destination)

            continue

        if status != "success":
            continue

        html = result

        parser = PageParser()

        try:
            parser.feed(html)
        except Exception as error:
            print("Warning: bad HTML, " + str(error))

        page_id = len(url_to_id)
        url_to_id[url] = page_id
        save_page(page_id, url, parser.get_text())

        #clean the links and keep the ones we can follow
        links = []
        found = set()
        for href in parser.links:
            link = clean_url(url, href)
            if link not in found and is_allowed(link, allowed_domains):
                found.add(link)
                links.append(link)
        graph[page_id] = links

        #new ones go on the back of the queue
        for link in links:
            if link not in seen:
                seen.add(link)
                queue.append(link)

        if len(url_to_id) % CHECKPOINT_INTERVAL == 0:
            save_checkpoint(queue, seen, url_to_id, graph)

        print("[" + str(page_id + 1) + "/" + str(max_pages) + "] " +
              urlparse(url).path.replace("/wiki/", ""))



    print("")
    save_checkpoint(queue, seen, url_to_id, graph)
    save_urls(url_to_id)
    save_edges(graph, url_to_id)

    if paused:
        print("Crawl paused. You can resume later.")
    else:
        print("Crawl finished.")
    print("Pages crawled: " + str(len(url_to_id)))
    print("Time: " + str(int(time.time() - start)) + " seconds")


if __name__ == "__main__":
    crawl(SEED_URLS, ALLOWED_DOMAINS, MAX_PAGES)
