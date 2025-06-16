import requests
import concurrent.futures # For multithreading
import re # For parsing different proxy formats
import time # For time.sleep for politeness, and latency calculation
from urllib.parse import urlparse # Useful for structured parsing, though regex handles most here

# --- Configuration ---
TEST_URL = 'http://httpbin.org/ip' # A reliable service that returns the public IP seen by the server
TIMEOUT = 15 # seconds - Increased slightly for potentially slower proxies
MAX_WORKERS = 50 # Adjust based on your VPS CPU/network and bandwidth.
                 # Too high might overwhelm your own connection or the target server.
                 # 50-100 is a good starting point for 1.5k proxies.

# --- Proxy Tester Function ---
def test_proxy(proxy_string):
    """
    Tests a single proxy regardless of its protocol (HTTP, HTTPS, SOCKS4, SOCKS5)
    and handles authentication.
    """
    session = requests.Session()
    # Using a common User-Agent to appear as a standard browser
    session.headers.update({'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'})

    original_proxy_string = proxy_string.strip()
    proxies_dict = {}
    parsed_protocol = "unknown" # To store the identified protocol

    # Attempt to parse common proxy formats:
    # 1. protocol://user:pass@ip:port
    # 2. protocol://ip:port
    # 3. ip:port:user:pass (assume http/https)
    # 4. ip:port (assume http/https)

    match_url = re.match(r'^(http|https|socks4|socks5):\/\/(?:([^:@]+):([^@]+)@)?([^:]+):(\d+)$', original_proxy_string)
    if match_url:
        protocol_prefix, user, password, ip, port = match_url.groups()
        parsed_protocol = protocol_prefix
        if user and password:
            auth_str = f"{user}:{password}@"
        else:
            auth_str = ""
        full_proxy_url_for_requests = f"{protocol_prefix}://{auth_str}{ip}:{port}"

        # requests library uses a single proxy string for http/https in the proxies dict,
        # even if it's a socks proxy. It needs pysocks installed to handle socks.
        proxies_dict = {
            "http": full_proxy_url_for_requests,
            "https": full_proxy_url_for_requests
        }
    else:
        # Fallback for formats without explicit protocol or user:pass in URL form
        parts = original_proxy_string.split(':')
        if len(parts) == 2: # ip:port
            ip, port = parts
            parsed_protocol = "http_assumed"
            proxies_dict = {
                "http": f"http://{ip}:{port}",
                "https": f"https://{ip}:{port}"
            }
        elif len(parts) == 4: # ip:port:user:pass
            ip, port, user, password = parts
            parsed_protocol = "http_auth_assumed"
            proxies_dict = {
                "http": f"http://{user}:{password}@{ip}:{port}",
                "https": f"https://{user}:{password}@{ip}:{port}"
            }
        else:
            return f"INVALID_FORMAT - {original_proxy_string}"

    try:
        start_time = time.time()
        # Make the request through the identified/parsed proxy
        response = session.get(TEST_URL, proxies=proxies_dict, timeout=TIMEOUT)
        end_time = time.time()
        latency = end_time - start_time

        response.raise_for_status() # Raise an HTTPError for bad responses (4xx or 5xx)

        # httpbin.org/ip returns {"origin": "YOUR_IP"}
        public_ip = response.json().get('origin', 'N/A')

        return f"SUCCESS - {parsed_protocol.upper()} | {original_proxy_string} | Public IP: {public_ip} | Latency: {latency:.2f}s"

    except requests.exceptions.ProxyError as e:
        return f"PROXY_ERROR - {parsed_protocol.upper()} | {original_proxy_string} | Check proxy configuration or if it's alive: {e}"
    except requests.exceptions.ConnectionError as e:
        return f"CONNECTION_ERROR - {parsed_protocol.upper()} | {original_proxy_string} | Proxy likely dead or blocked: {e}"
    except requests.exceptions.Timeout:
        return f"TIMEOUT - {parsed_protocol.upper()} | {original_proxy_string} | Proxy too slow or unresponsive"
    except requests.exceptions.HTTPError as e:
        return f"HTTP_ERROR - {parsed_protocol.upper()} | {original_proxy_string} | Status Code: {e.response.status_code} | Reason: {e.response.reason}"
    except Exception as e:
        return f"UNKNOWN_ERROR - {parsed_protocol.upper()} | {original_proxy_string} | An unexpected error occurred: {e}"

# --- Main Execution ---
if __name__ == "__main__":
    # --- 1. Load Proxies from a file ---
    # Make sure your 1.5k proxies are in this file, one per line.
    proxy_list_file = 'proxies.txt' # Changed from 'all_proxies.txt' to 'proxies.txt'

    try:
        with open(proxy_list_file, 'r') as f:
            proxies_to_test = [line.strip() for line in f if line.strip() and not line.startswith('#')]
    except FileNotFoundError:
        print(f"Error: '{proxy_list_file}' not found. Please create this file and populate it with your proxies.")
        exit(1) # Exit with an error code

    if not proxies_to_test:
        print(f"No proxies found in '{proxy_list_file}'. Please ensure the file contains proxies and is not empty.")
        exit(0) # Exit gracefully if file is empty

    print(f"Loaded {len(proxies_to_test)} proxies from '{proxy_list_file}'. Starting test...")

    working_proxies = []
    failed_proxies = []

    # Use ThreadPoolExecutor for concurrent testing
    # This will significantly speed up testing 1.5k proxies
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        # Map the test_proxy function to each proxy string
        # `executor.map` returns results in the order the inputs were submitted
        results_iterator = executor.map(test_proxy, proxies_to_test)

        for i, result in enumerate(results_iterator):
            print(f"[{i+1}/{len(proxies_to_test)}] {result}")
            if result.startswith("SUCCESS"):
                working_proxies.append(result)
            else:
                failed_proxies.append(result)

    print("\n--- Test Complete ---")
    print(f"Total Proxies Tested: {len(proxies_to_test)}")
    print(f"Working Proxies: {len(working_proxies)}")
    print(f"Failed Proxies: {len(failed_proxies)}")

    # Optional: Save results to files
    print("\nSaving results...")
    try:
        with open('working_proxies_output.txt', 'w') as f_out:
            for p in working_proxies:
                f_out.write(p + '\n')
        print("Working proxies saved to 'working_proxies_output.txt'")

        with open('failed_proxies_output.txt', 'w') as f_out:
            for p in failed_proxies:
                f_out.write(p + '\n')
        print("Failed proxies saved to 'failed_proxies_output.txt'")
    except IOError as e:
        print(f"Error saving results to file: {e}")

    print("\nDone.")
