import requests
import time

def test_proxy(proxy_full_url):
    """
    Tests a single HTTP/HTTPS proxy.
    proxy_full_url example: "http://198.23.239.134:8080" or "http://user:pass@192.168.1.1:8080"
    """
    proxies = {
        "http": proxy_full_url,
        "https": proxy_full_url # Often, HTTP proxies can also handle HTTPS
    }

    test_url = "http://httpbin.org/ip" # A simple service that returns the request IP

    try:
        start_time = time.time()
        # Set a timeout (e.g., 10 seconds) to avoid hanging indefinitely on dead proxies
        response = requests.get(test_url, proxies=proxies, timeout=10)
        end_time = time.time()

        if response.status_code == 200:
            try:
                origin_ip = response.json().get('origin')
                print(f"✅ SUCCESS: {proxy_full_url} - IP: {origin_ip} - Latency: {end_time - start_time:.2f}s")
                return True, origin_ip, (end_time - start_time)
            except ValueError:
                print(f"⚠️ WARNING: {proxy_full_url} - Successful request, but couldn't parse IP. Possibly transparent.")
                return True, None, (end_time - start_time)
        else:
            print(f"❌ FAILED: {proxy_full_url} - Status Code: {response.status_code}")
            return False, None, None
    except requests.exceptions.ProxyError:
        print(f"❌ FAILED: {proxy_full_url} - Proxy connection error (check format or if it's alive).")
        return False, None, None
    except requests.exceptions.Timeout:
        print(f"❌ FAILED: {proxy_full_url} - Timeout (proxy too slow or unresponsive).")
        return False, None, None
    except requests.exceptions.ConnectionError:
        print(f"❌ FAILED: {proxy_full_url} - Connection error (proxy likely dead or blocked).")
        return False, None, None
    except Exception as e:
        print(f"❌ FAILED: {proxy_full_url} - An unexpected error occurred: {e}")
        return False, None, None

def read_proxies_from_file(filepath):
    """Reads proxies from a text file, one per line."""
    proxies = []
    with open(filepath, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#'): # Ignore empty lines and comments
                proxies.append(line)
    return proxies

if __name__ == "__main__":
    proxy_file = "http.txt" # Your file containing HTTP proxies
    working_proxies = []

    try:
        print(f"Reading proxies from {proxy_file}...")
        all_proxies = read_proxies_from_file(proxy_file)
        if not all_proxies:
            print(f"No proxies found in {proxy_file}. Please ensure the file exists and contains proxies.")
            exit()
        print(f"Found {len(all_proxies)} proxies to test.\n")

        for proxy_entry in all_proxies:
            # Ensure the proxy string starts with "http://" if it's just "IP:PORT"
            if not proxy_entry.startswith("http://") and not proxy_entry.startswith("https://"):
                proxy_full_url = f"http://{proxy_entry}"
            else:
                proxy_full_url = proxy_entry

            success, ip, latency = test_proxy(proxy_full_url)
            if success:
                working_proxies.append((proxy_full_url, ip, latency))
            time.sleep(0.1) # Be polite and don't hammer the test server

        print("\n--- Testing Complete ---")
        if working_proxies:
            print(f"\nFound {len(working_proxies)} working HTTP proxies:")
            for proxy_info in working_proxies:
                print(f"- {proxy_info[0]} (Proxy IP: {proxy_info[1]}, Latency: {proxy_info[2]:.2f}s)")

            # Optionally, save working proxies to a new file
            with open("working_http_proxies.txt", "w") as f_out:
                for proxy_info in working_proxies:
                    f_out.write(f"{proxy_info[0]}\n")
            print("\nWorking proxies saved to 'working_http_proxies.txt'")

        else:
            print("No working HTTP proxies found.")

    except FileNotFoundError:
        print(f"Error: The file '{proxy_file}' was not found. Please make sure it's in the same directory as the script.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
