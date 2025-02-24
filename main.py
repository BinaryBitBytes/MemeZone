import tweepy
from tweepy.errors import Forbidden
import logging

# Set up logging for debugging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Replace these with your actual API credentials from the X Developer Portal
API_KEY = "your_api_key"
API_SECRET = "your_api_secret"
ACCESS_TOKEN = "your_access_token"
ACCESS_TOKEN_SECRET = "your_access_token_secret"

# Authenticate with the latest API version (v2)
def authenticate_v2():
    try:
        client = tweepy.Client(
            consumer_key=API_KEY,
            consumer_secret=API_SECRET,
            access_token=ACCESS_TOKEN,
            access_token_secret=ACCESS_TOKEN_SECRET
        )
        # Test a simple v2 endpoint to check access (e.g., get current user's info)
        client.get_me()
        logger.info("Successfully authenticated with X API v2")
        return client
    except Forbidden as e:
        logger.error(f"v2 Authentication failed: {e}")
        return None

# Authenticate with the fallback API version (v1.1)
def authenticate_v1_1():
    try:
        auth = tweepy.OAuth1UserHandler(
            API_KEY, API_SECRET, ACCESS_TOKEN, ACCESS_TOKEN_SECRET
        )
        api = tweepy.API(auth)
        # Test a simple v1.1 endpoint to verify access
        api.verify_credentials()
        logger.info("Successfully authenticated with X API v1.1")
        return api
    except Forbidden as e:
        logger.error(f"v1.1 Authentication failed: {e}")
        return None

# Function to call an endpoint with version fallback
def call_api_with_fallback(endpoint_func_v2, endpoint_func_v1_1, *args, **kwargs):
    # Try v2 first
    client_v2 = authenticate_v2()
    if client_v2:
        try:
            result = endpoint_func_v2(client_v2, *args, **kwargs)
            return result
        except Forbidden as e:
            logger.error(f"v2 Endpoint call failed: {e}")
            # If v2 fails due to access restriction, fall back to v1.1

    # Fallback to v1.1
    api_v1_1 = authenticate_v1_1()
    if api_v1_1:
        try:
            result = endpoint_func_v1_1(api_v1_1, *args, **kwargs)
            return result
        except Forbidden as e:
            logger.error(f"v1.1 Endpoint call failed: {e}")
            raise Exception("Access denied for both v2 and v1.1 endpoints")
    else:
        raise Exception("Authentication failed for both v2 and v1.1")

# Example endpoint functions
def get_user_v2(client, user_id):
    return client.get_user(id=user_id)

def get_user_v1_1(api, user_id):
    return api.get_user(user_id=user_id)

# Usage example
try:
    user_id = "123456789"  # Replace with a valid user ID
    user = call_api_with_fallback(get_user_v2, get_user_v1_1, user_id=user_id)
    logger.info(f"User data: {user}")
except Exception as e:
    logger.error(f"Failed to retrieve data: {e}")