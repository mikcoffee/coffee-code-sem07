import time
import logging
from urllib.robotparser import RobotFileParser
import requests

logger = logging.getLogger("collection")

class HttpClient:
    """HTTP client with retries and robots.txt compliance."""
    
    def __init__(self, base_url: str, user_agent: str, max_attempts: int = 3):
        self.base_url = base_url
        self.user_agent = user_agent
        self.max_attempts = max_attempts
        self.session = requests.Session()
        self.session.headers["User-Agent"] = user_agent
        self.robots = None
        self.delay = 1.0

    def load_robots(self):
        """Loads and parses robots.txt."""
        try:
            response = self.session.get(f"{self.base_url}/robots.txt", timeout=10)
            response.raise_for_status()
            self.robots = RobotFileParser()
            self.robots.parse(response.text.splitlines())
            self.delay = float(self.robots.crawl_delay(self.user_agent) or 1.0)
            logger.info(f"robots.txt loaded. Delay between requests: {self.delay} s")
        except Exception as e:
            logger.warning(f"Failed to read robots.txt: {e}. Continuing without restrictions.")
            self.robots = None

    def is_allowed(self, url: str) -> bool:
        """Checks if URL is allowed by robots.txt."""
        if self.robots is None:
            return True
        return self.robots.can_fetch(self.user_agent, url)

    def fetch(self, url: str, timeout: tuple = (3.05, 10)) -> requests.Response:
        """Fetches URL with retries."""
        if not self.is_allowed(url):
            raise RuntimeError(f"robots.txt does not allow: {url}")
        
        for attempt in range(1, self.max_attempts + 1):
            time.sleep(self.delay)
            try:
                response = self.session.get(url, timeout=timeout)
                # Success or non-retryable error
                if response.status_code < 500:
                    response.raise_for_status()
                    return response
                
                # Server error - retry
                if attempt < self.max_attempts:
                    wait_time = 0.5 * (2 ** (attempt - 1))
                    logger.warning(f"HTTP {response.status_code} at {url}: "
                                   f"attempt {attempt} of {self.max_attempts}, "
                                   f"waiting {wait_time} s")
                    time.sleep(wait_time)
                else:
                    response.raise_for_status()
            except (requests.Timeout, requests.ConnectionError) as e:
                if attempt < self.max_attempts:
                    wait_time = 0.5 * (2 ** (attempt - 1))
                    logger.warning(f"{type(e).__name__} at {url}: "
                                   f"attempt {attempt} of {self.max_attempts}, "
                                   f"waiting {wait_time} s")
                    time.sleep(wait_time)
                else:
                    raise
                    
        raise RuntimeError(f"{url}: failed after {self.max_attempts} attempts")
