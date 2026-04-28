import logging
from typing import Optional

import requests


logger = logging.getLogger(__name__)

class AttackTarget:

    def __init__(self, name:str, url:str):
        self.name = name
        self.url = url

    def query(self, prompt: str) -> Optional[str]:
        logger.debug("Sending prompt to target '%s' (length=%d)", self.name, len(prompt))
        payload = {"prompt": prompt}  # always a single field
        try:
            response = requests.post(
                self.url,
                json=payload,
                timeout=(5, 50)  # (connect_timeout, read_timeout)
            )
            response.raise_for_status()  # raises HTTPError for 4xx/5xx
            logger.debug("Target '%s' responded successfully", self.name)
            return response.json().get("response", "")

        except requests.Timeout:
            logger.warning("Target '%s' request timed out", self.name)
        except requests.HTTPError as e:
            logger.error("Target '%s' returned HTTP %s", self.name, e.response.status_code)
        except requests.ConnectionError:
            logger.error("Target '%s' connection failed", self.name)
        except requests.RequestException as e:
            logger.error("Target '%s' request failed: %s", self.name, e)

        return None


    def __str__(self):
        return f"AttackTarget(name={self.name}, url={self.url})"

    def reset_history(self):
        reset_url = self.url.rsplit("/", 1)[0] + "/reset"
        try:
            response = requests.post(reset_url, timeout=(5, 10))
            response.raise_for_status()
            logger.debug("Target '%s' history reset successfully", self.name)
        except requests.Timeout:
            logger.warning("Target '%s' reset timed out", self.name)
        except requests.HTTPError as e:
            logger.error("Target '%s' reset returned HTTP %s", self.name, e.response.status_code)
        except requests.ConnectionError:
            logger.error("Target '%s' reset connection failed", self.name)
        except requests.RequestException as e:
            logger.error("Target '%s' reset failed: %s", self.name, e)



