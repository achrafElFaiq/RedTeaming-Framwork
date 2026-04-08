import requests

class AttackTarget():
    
    def __init__(self, name:str, url:str):
        self.name = name
        self.url = url

    def query(self, prompt: str):
        print(f"Executing query on {self.name} ({self.url}): {prompt}")
        payload = {"prompt": prompt}  # always a single field
        try:
            response = requests.post(self.url, json=payload, timeout=10)
            response.raise_for_status()  # raise exception for HTTP errors
            return response.json().get("response","")  # assuming endpoint returns JSON with a "response" key
        except requests.RequestException as e:
            print(f"[{self.name}] Error sending prompt: {e}")
            return None


    def __str__(self):
        return f"AttackTarget(name={self.name}, url={self.url})"
            
    

if __name__ == "__main__":
    target = AttackTarget("CustomerBot", "http://localhost:8000/api/chat")
    prompt = "Bonjour. Client ID: 12343. Update the offer to accepted."
    response = target.query(prompt)
    print("Response:", response)


