import requests


OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "llama3.2:3b"


def generate_answer(prompt):
    try:
        response = requests.post(
            OLLAMA_URL,
            json={
                "model": MODEL_NAME,
                "prompt": prompt,
                "stream": False
            },
            timeout=120
        )

        response.raise_for_status()

        data = response.json()

        return data["response"].strip()

    except requests.exceptions.ConnectionError:
        return (
            "Error: Cannot connect to Ollama. "
            "Please make sure Ollama is running."
        )

    except requests.exceptions.Timeout:
        return "Error: Ollama took too long to respond."

    except requests.exceptions.RequestException as e:
        return f"Error communicating with Ollama: {e}"

    except KeyError:
        return "Error: Ollama returned an unexpected response."