import time
import torch
import torch.nn.functional as F
import pickle
import os

def load_preinitialized_objects():
    save_dir = './model_data'
    
    try:
        with open(os.path.join(save_dir, 'tokenizer.pkl'), 'rb') as f:
            tokenizer = pickle.load(f)

        with open(os.path.join(save_dir, 'model.pkl'), 'rb') as f:
            model = pickle.load(f)

        with open(os.path.join(save_dir, 'end_tokens.pkl'), 'rb') as f:
            end_tokens = pickle.load(f)
    except Exception as e:
        print(f"Error loading pre-initialized objects: {e}")
        raise

    return tokenizer, model, end_tokens

def get_top_tokens(input_sentence, top_k=100):
    tokenizer, model, end_tokens = load_preinitialized_objects()
    input_ids = tokenizer.encode(input_sentence, return_tensors='pt')
    with torch.no_grad():
        outputs = model(input_ids)
        logits = outputs.logits
        next_token_logits = logits[:, -1, :]
        probabilities = F.softmax(next_token_logits, dim=-1)
        top_k_probs, top_k_ids = torch.topk(probabilities, k=top_k, dim=-1)

    top_tokens = []
    for prob, token_id in zip(top_k_probs[0], top_k_ids[0]):
        token = tokenizer.decode(token_id)
        top_tokens.append((token, prob.item()))

    return top_tokens, end_tokens

def calculate_end_tokens_prob(input_sentence):
    top_tokens, end_tokens = get_top_tokens(input_sentence)
    end_tokens_probs = [value for key, value in top_tokens if key in end_tokens]
    top_3_tokens = [token for token, _ in sorted(top_tokens, key=lambda x: x[1], reverse=True)[:3]]
    return sum(end_tokens_probs), top_3_tokens

if __name__ == "__main__":
    input_sentence = "Hello nice to meet you too"
    print(f"Top tokens: {get_top_tokens(input_sentence)}")
    print(f"Sum of end tokens probabilities: {calculate_end_tokens_prob(input_sentence)}")
