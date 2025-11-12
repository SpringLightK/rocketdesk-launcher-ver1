# app_launcher/core/sentence_encoder.py
import torch
import numpy as np
from app_launcher.core.alias_model import AliasModelManager

class QwenSentenceEncoder:
    def __init__(self):
        mgr = AliasModelManager.instance()
        self.base_model = mgr.base_model
        self.tokenizer = mgr.tokenizer
        self.device = mgr.device

    @torch.no_grad()
    def encode(self, texts):
        if isinstance(texts, str):
            texts = [texts]

        inputs = self.tokenizer(
            texts,
            return_tensors="pt",
            padding=True,
            truncation=True,
            max_length=64,
        ).to(self.device)

        outputs = self.base_model(
            **inputs,
            output_hidden_states=True,
        )
        hidden = outputs.hidden_states[-1]  # [batch, seq_len, hidden]

        mask = inputs["attention_mask"].unsqueeze(-1)
        summed = (hidden * mask).sum(dim=1)
        counts = mask.sum(dim=1).clamp(min=1)
        mean_pooled = summed / counts

        vecs = mean_pooled.cpu().numpy()
        norms = np.linalg.norm(vecs, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        return vecs / norms
