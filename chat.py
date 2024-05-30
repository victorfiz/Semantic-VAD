import json
import logging
import requests
import time

async def chat_completion(query):
    
    start_time = time.time()
    url = "http://localhost:11434/api/generate"
    headers = {
        "Content-Type": "application/json"
    }
    payload = {
        "model": "mistral:instruct",
        "prompt": query
    }
    logging.info(f"----> Query sent to Ollama: {query}")
    try:
        response = requests.post(url, data=json.dumps(payload), headers=headers, stream=True)
        logging.info(f"Ollama status code: {response.status_code}")
        if response.status_code == 200:
            accumulated_response = ""
            try:
                for line in response.iter_lines():
                    if line:
                        res = line.decode('utf-8')
                        response_json = json.loads(res)
                        accumulated_response += response_json.get("response", "")
                time_taken = time.time() - start_time
                logging.info(f"----> in {time_taken:.2f} seconds Ollama returned: {accumulated_response}")
                return accumulated_response
            except json.JSONDecodeError as e:
                logging.error(f"Failed to decode JSON: {e}")
        else:
            logging.error(f"Failed to get response. Status code: {response.status_code}")
            return ""
    except Exception as e:
        logging.error(f"Error connecting to local model: {e}")
        return ""
