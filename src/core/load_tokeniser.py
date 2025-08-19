import time
from transformers import AutoTokenizer, AutoModelForCausalLM
import pickle
import os
from huggingface_hub import login
from collections import OrderedDict
from config.config import HUGGINGFACE_TOKEN

def load_and_save_models():
    start_time = time.time()

    if not HUGGINGFACE_TOKEN:
        raise ValueError("HUGGINGFACE_TOKEN environment variable is not set")
        
    user_home = os.path.expanduser('~')  # Get the path to the user's home directory
    token_path = os.path.join(user_home, '.cache/huggingface/token')  # Change the token path to user's home directory
    my_model = "gpt2"
    save_dir = './model_data'  # Directory to save the models and tokenizer

    # Ensure the directory exists
    os.makedirs(os.path.dirname(token_path), exist_ok=True)
    os.makedirs(save_dir, exist_ok=True)

    # Login and set the environment variable if the token path does not exist
    if not os.path.exists(token_path):
        login(token=HUGGINGFACE_TOKEN, add_to_git_credential=True)
        os.environ['HF_TOKEN'] = HUGGINGFACE_TOKEN

    # Load tokenizer and model
    tokenizer = AutoTokenizer.from_pretrained(my_model, token=HUGGINGFACE_TOKEN)
    model = AutoModelForCausalLM.from_pretrained(my_model, token=HUGGINGFACE_TOKEN)

    try:
        with open(os.path.join(save_dir, 'tokenizer.pkl'), 'wb') as f:
            pickle.dump(tokenizer, f)

        with open(os.path.join(save_dir, 'model.pkl'), 'wb') as f:
            pickle.dump(model, f)
    except Exception as e:
        print(f"Error saving tokenizer or model: {e}")

    # Get the tokenizer vocabulary and filter end tokens
    token_dict = tokenizer.get_vocab()
    ordered_token_dict = OrderedDict(sorted(token_dict.items(), key=lambda item: item[1]))
    end_tokens = {token: idx for token, idx in ordered_token_dict.items() if any(char in token for char in ['.', '?', '!', ';'])}

    try:
        with open(os.path.join(save_dir, 'end_tokens.pkl'), 'wb') as f:
            pickle.dump(end_tokens, f)
    except Exception as e:
        print(f"Error saving end tokens: {e}")

    print(f"The {len(end_tokens)} end tokens are: {end_tokens}")

    time_taken = time.time() - start_time
    print(f"{time_taken:.4f} sec")

if __name__ == "__main__":
    load_and_save_models()
