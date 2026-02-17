import requests
import json

def test_tool_endpoint():
    url = "http://localhost:8090/tool"
    payload = {
        "name": "search_products",
        "arguments": {"query": "laptop"}
    }
    
    print(f"Testing POST {url} with payload {json.dumps(payload)}")
    
    try:
        response = requests.post(url, json=payload)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            print("Success! Response:")
            print(json.dumps(response.json(), indent=2, ensure_ascii=False))
        else:
            print(f"Error: {response.text}")
            
    except Exception as e:
        print(f"Failed to connect to server: {e}")

if __name__ == "__main__":
    test_tool_endpoint()
