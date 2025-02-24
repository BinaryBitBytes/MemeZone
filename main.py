import requests
import tweepy
import time
import json
import os
from bs4 import BeautifulSoup
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict
import urllib3

# Suppress SSL warnings for testing (remove in production)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Default config file
CONFIG_FILE = "config.json"

# Initial config template
DEFAULT_CONFIG = {
    "twitter": {
        "api_key": "",
        "api_secret": "",
        "access_token": "",
        "access_token_secret": ""
    },
    "dexscreener": {"url": "https://api.dexscreener.com/latest/dex/search?q="},
    "gmgn": {"url": "https://gmgn.ai"},
    "pumpfun": {"url": "https://pump.fun"},
    "tweetscout": {"base_url": "https://app.tweetscout.io", "search_endpoint": "/search"}
}

@dataclass
class State:
    """Centralized state management for tracking data and status."""
    dexscreener: List[Dict] = None
    gmgn: List[Dict] = None
    pumpfun: List[Dict] = None
    tweetscout: List[Dict] = None
    errors: Dict[str, str] = None
    progress: str = "Initializing..."

    def __post_init__(self):
        self.dexscreener = self.dexscreener or []
        self.gmgn = self.gmgn or []
        self.pumpfun = self.pumpfun or []
        self.tweetscout = self.tweetscout or []
        self.errors = self.errors or {}

    def update_progress(self, message: str):
        """Update progress message."""
        self.progress = message
        print(f"[Progress] {message}")

    def add_error(self, source: str, error: str):
        """Record an error for a specific source."""
        self.errors[source] = error
        print(f"[Error] {source}: {error}")

class MemeTracker:
    def __init__(self, config: Dict):
        self.config = config
        self.state = State()
        self.twitter_api = None  # Initialized after authentication
        self.headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

    def _twitter_authenticate(self) -> Optional[tweepy.API]:
        """Authenticate with Twitter API using stored or new credentials."""
        twitter_config = self.config["twitter"]
        if all(twitter_config.get(k) for k in ["api_key", "api_secret", "access_token", "access_token_secret"]):
            try:
                auth = tweepy.OAuth1UserHandler(
                    twitter_config["api_key"],
                    twitter_config["api_secret"],
                    twitter_config["access_token"],
                    twitter_config["access_token_secret"]
                )
                api = tweepy.API(auth, wait_on_rate_limit=True)
                api.verify_credentials()  # Test the credentials
                return api
            except Exception as e:
                self.state.add_error("Twitter", f"Authentication failed with stored credentials: {e}")
                return None
        return None

    def authenticate_twitter(self):
        """Guide user through Twitter OAuth flow and update config."""
        print("\n=== Twitter Authentication ===")
        api_key = input("Enter Twitter API Key (Consumer Key): ").strip()
        api_secret = input("Enter Twitter API Secret (Consumer Secret): ").strip()

        try:
            auth = tweepy.OAuth1UserHandler(api_key, api_secret)
            auth_url = auth.get_authorization_url()
            print(f"\nPlease visit this URL to authorize the app: {auth_url}")
            pin = input("Enter the PIN provided by Twitter: ").strip()
            access_token, access_token_secret = auth.get_access_token(pin)
            
            # Update config with new credentials
            self.config["twitter"] = {
                "api_key": api_key,
                "api_secret": api_secret,
                "access_token": access_token,
                "access_token_secret": access_token_secret
            }
            with open(CONFIG_FILE, "w") as f:
                json.dump(self.config, f, indent=2)
            print("Twitter credentials saved to 'config.json'.")

            # Test the new credentials
            self.twitter_api = tweepy.API(auth, wait_on_rate_limit=True)
            self.twitter_api.verify_credentials()
            print("Twitter authentication successful!")
        except Exception as e:
            self.state.add_error("Twitter", f"Authentication failed: {e}")
            self.twitter_api = None

    def fetch_dexscreener_trends(self):
        """Fetch trending tokens from Dexscreener."""
        self.state.update_progress("Fetching Dexscreener trends...")
        url = f"{self.config['dexscreener']['url']}meme"
        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            data = response.json().get("pairs", [])
            self.state.dexscreener = sorted(data, key=lambda x: float(x.get("volume", {}).get("h24", 0)), reverse=True)[:10]
        except Exception as e:
            self.state.add_error("Dexscreener", str(e))

    def fetch_gmgn_tokens(self):
        """Fetch new tokens from GMGN."""
        self.state.update_progress("Fetching GMGN tokens...")
        url = self.config["gmgn"]["url"]
        try:
            response = requests.get(url, headers=self.headers, timeout=10, verify=False)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")
            tokens = []
            for entry in soup.select(".token-card"):  # Adjust selector
                name_element = entry.select_one(".token-name")
                details_element = entry.select_one(".token-details")
                tokens.append({
                    "name": name_element.text.strip() if name_element else "Unknown",
                    "details": details_element.text.strip() if details_element else "N/A"
                })
            self.state.gmgn = tokens[:10]
        except Exception as e:
            self.state.add_error("GMGN", str(e))

    def fetch_pumpfun_tokens(self):
        """Fetch new tokens from Pumpfun."""
        self.state.update_progress("Fetching Pumpfun tokens...")
        url = self.config["pumpfun"]["url"]
        try:
            response = requests.get(url, headers=self.headers, timeout=10, verify=False)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")
            tokens = []
            for entry in soup.select(".token-list-item"):  # Adjust selector
                name_element = entry.select_one(".token-name")
                volume_element = entry.select_one(".token-volume")
                tokens.append({
                    "name": name_element.text.strip() if name_element else "Unknown",
                    "volume": volume_element.text.strip() if volume_element else "N/A"
                })
            self.state.pumpfun = tokens[:10]
        except Exception as e:
            self.state.add_error("Pumpfun", str(e))

    def fetch_twitter_trends(self, keyword: str, count: int = 10) -> List[Dict]:
        """Search Twitter for trends related to a keyword."""
        if not self.twitter_api:
            self.state.add_error("Twitter", "API not authenticated.")
            return []
        try:
            tweets = self.twitter_api.search_tweets(q=keyword, count=count, result_type="popular", lang="en")
            return [{"text": tweet.text, "user": tweet.user.screen_name} for tweet in tweets]
        except Exception as e:
            self.state.add_error(f"Twitter ({keyword})", str(e))
            return []

    def fetch_tweetscout_accounts(self, keyword: str = "memecoin"):
        """Search TweetScout for memecoin-related Twitter accounts."""
        self.state.update_progress("Fetching TweetScout accounts...")
        url = f"{self.config['tweetscout']['base_url']}{self.config['tweetscout']['search_endpoint']}?query={keyword}&type=account"
        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")
            accounts = []
            for account in soup.select(".account-card"):  # Adjust selector
                name_element = account.select_one(".account-name")
                handle_element = account.select_one(".account-handle")
                followers_element = account.select_one(".account-followers")
                accounts.append({
                    "name": name_element.text.strip() if name_element else "Unknown",
                    "handle": handle_element.text.strip() if handle_element else "N/A",
                    "followers": followers_element.text.strip() if followers_element else "N/A"
                })
            self.state.tweetscout = accounts[:5]
        except Exception as e:
            self.state.add_error("TweetScout", str(e))

    def enrich_dexscreener_with_twitter(self):
        """Enrich Dexscreener trends with Twitter data."""
        if not self.state.dexscreener or not self.twitter_api:
            return
        self.state.update_progress("Enriching Dexscreener with Twitter trends...")
        for token in self.state.dexscreener:
            symbol = token.get("baseToken", {}).get("symbol", "Unknown")
            token["twitter_trends"] = self.fetch_twitter_trends(symbol)
            time.sleep(2)

    def aggregate_trends(self):
        """Aggregate trends from all sources and update state."""
        self.fetch_dexscreener_trends()
        self.fetch_gmgn_tokens()
        self.fetch_pumpfun_tokens()
        self.fetch_tweetscout_accounts()
        self.enrich_dexscreener_with_twitter()
        self.state.update_progress("Aggregation complete.")

    def display_results(self):
        """Display aggregated trends from the current state."""
        print("\n=== Meme & Memecoin Trends ===\n")
        if self.state.errors:
            print("Errors Encountered:")
            for source, error in self.state.errors.items():
                print(f"- {source}: {error}")
            print()

        if self.state.dexscreener:
            print("Top Dexscreener Tokens (by 24h Volume):")
            for i, token in enumerate(self.state.dexscreener, 1):
                symbol = token.get("baseToken", {}).get("symbol", "Unknown")
                volume = float(token.get("volume", {}).get("h24", 0))
                print(f"{i}. {symbol} | Volume: ${volume:,.2f}")
                for j, tweet in enumerate(token.get("twitter_trends", []), 1):
                    print(f"   Tweet {j}: @{tweet['user']}: {tweet['text']}")
            print()

        if self.state.gmgn:
            print("New Tokens on GMGN:")
            for i, token in enumerate(self.state.gmgn, 1):
                print(f"{i}. {token['name']} | Details: {token['details']}")
            print()

        if self.state.pumpfun:
            print("New Tokens on Pumpfun:")
            for i, token in enumerate(self.state.pumpfun, 1):
                print(f"{i}. {token['name']} | Volume: {token['volume']}")
            print()

        if self.state.tweetscout:
            print("Memecoin Twitter Accounts (TweetScout):")
            for i, account in enumerate(self.state.tweetscout, 1):
                print(f"{i}. {account['name']} (@{account['handle']}) | Followers: {account['followers']}")
            print()

    def save_to_json(self, filename: str = "meme_trends.json"):
        """Save the current state to a JSON file."""
        with open(filename, "w") as f:
            json.dump(asdict(self.state), f, indent=2)
        print(f"Results saved to '{filename}'")

def load_or_create_config():
    """Load existing config or create a new one."""
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    else:
        with open(CONFIG_FILE, "w") as f:
            json.dump(DEFAULT_CONFIG, f, indent=2)
        return DEFAULT_CONFIG

def main():
    print("Note: Ensure compliance with each platform's terms of service.")
    print("Warning: SSL verification disabled for Pumpfun and GMGN (testing only).")
    config = load_or_create_config()
    tracker = MemeTracker(config)

    # Initial Twitter authentication check
    tracker.twitter_api = tracker._twitter_authenticate()
    if not tracker.twitter_api:
        print("Twitter API not authenticated. Please authenticate or update credentials.")

    while True:
        action = input("\nOptions: (run/auth/update/exit): ").strip().lower()
        if action == "exit":
            break
        elif action == "auth":
            tracker.authenticate_twitter()
        elif action == "update":
            tracker.config["twitter"] = {
                "api_key": input("Enter Twitter API Key: ").strip(),
                "api_secret": input("Enter Twitter API Secret: ").strip(),
                "access_token": input("Enter Twitter Access Token (optional): ").strip(),
                "access_token_secret": input("Enter Twitter Access Token Secret (optional): ").strip()
            }
            with open(CONFIG_FILE, "w") as f:
                json.dump(tracker.config, f, indent=2)
            print("Config updated. Re-authenticating...")
            tracker.twitter_api = tracker._twitter_authenticate()
        elif action == "run":
            if not tracker.twitter_api:
                print("Twitter API not authenticated. Please use 'auth' or 'update' first.")
                continue
            tracker.state = State()  # Reset state
            tracker.aggregate_trends()
            tracker.display_results()
            tracker.save_to_json()
            action = input("\nWhat next? (retry/exit/filter): ").strip().lower()
            if action == "exit":
                break
            elif action == "retry":
                continue
            elif action == "filter":
                keyword = input("Enter a keyword to filter Dexscreener tokens: ").strip()
                if keyword:
                    tracker.state.dexscreener = [
                        token for token in tracker.state.dexscreener
                        if keyword.lower() in token.get("baseToken", {}).get("symbol", "").lower()
                    ]
                    tracker.enrich_dexscreener_with_twitter()
                    tracker.display_results()
                else:
                    print("No keyword provided; showing all results.")
        else:
            print("Invalid option. Choose 'run', 'auth', 'update', or 'exit'.")

if __name__ == "__main__":
    main()