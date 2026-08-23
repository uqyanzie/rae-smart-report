import threading
import time
import webbrowser
import urllib.request

def open_browser_when_ready(host: str = "127.0.0.1", port: int = 8000, timeout: int = 15):
    """
    Polls the health endpoint until the server is alive, then opens the default browser.
    """
    url = f"http://{host}:{port}"
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        try:
            with urllib.request.urlopen(f"{url}/api/health", timeout=1) as response:
                if response.status == 200:
                    webbrowser.open(url)
                    return
        except Exception:
            time.sleep(0.3)
            
    # Open anyway after timeout expires
    webbrowser.open(url)

def start_browser_thread(host: str = "127.0.0.1", port: int = 8000):
    thread = threading.Thread(target=open_browser_when_ready, args=(host, port), daemon=True)
    thread.start()
