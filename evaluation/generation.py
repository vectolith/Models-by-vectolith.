"""Helpers for preparing prompts for decoder-only causal generation."""


def render_prompt(tokenizer, messages: list[dict]):
    encoded = tokenizer.apply_chat_template(
        messages,
        tokenize=True,
        add_generation_prompt=True,
        enable_thinking=False,
        return_tensors="pt",
        return_dict=True,
    )
    encoded.pop("token_type_ids", None)
    return encoded
