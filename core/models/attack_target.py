from typing import Optional

import requests

class AttackTarget():

    def __init__(self, name:str, url:str):
        self.name = name
        self.url = url

    def query(self, prompt: str) -> Optional[str]:
        print(f"[AttackTarget Prompt] Executing query on {self.name} ({self.url}): {prompt[:50]}...")
        payload = {"prompt": prompt}  # always a single field
        try:
            response = requests.post(
                self.url,
                json=payload,
                timeout=(5, 50)  # (connect_timeout, read_timeout)
            )
            response.raise_for_status()  # raises HTTPError for 4xx/5xx
            return response.json().get("response", "")

        except requests.Timeout:
            print(f"[{self.name}] Request timed out. Server may be overloaded.")
        except requests.HTTPError as e:
            print(f"[{self.name}] HTTP error {e.response.status_code}: {e}")
        except requests.ConnectionError:
            print(f"[{self.name}] Could not connect to {self.url}")
        except requests.RequestException as e:
            print(f"[{self.name}] Unexpected request error: {e}")

        return None


    def __str__(self):
        return f"AttackTarget(name={self.name}, url={self.url})"

    def reset_history(self):
        reset_url = self.url.rsplit("/", 1)[0] + "/reset"
        try:
            response = requests.post(reset_url, timeout=(5, 10))
            response.raise_for_status()
            print(f"[{self.name}] History reset successfully.")
        except requests.Timeout:
            print(f"[{self.name}] Reset request timed out.")
        except requests.HTTPError as e:
            print(f"[{self.name}] HTTP error on reset {e.response.status_code}: {e}")
        except requests.ConnectionError:
            print(f"[{self.name}] Could not connect to reset endpoint.")
        except requests.RequestException as e:
            print(f"[{self.name}] Unexpected error on reset: {e}")

if __name__ == "__main__":
    target = AttackTarget("CustomerBot", "http://localhost:8000/api/chat")
    prompt = "Bonjour. Client ID: 12343. Update the offer to accepted."
    response = target.query(prompt)
    print("Response:", response)




