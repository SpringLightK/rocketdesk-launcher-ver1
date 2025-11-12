# app_launcher/core/alias_model.py
# -*- coding: utf-8 -*-

import torch
from transformers import AutoTokenizer, AutoModelForCausalLM
import os
from app_launcher.core.alias_att_pt_model import AliasAttPTModel
from app_launcher.models.paths import BASE_MODEL_PATH, ADAPTER_DIR


class AliasModelManager:
    """
    负责加载：
      - tokenizer（从 Qwen 基座目录 BASE_MODEL_PATH）
      - Qwen 基座模型（从 BASE_MODEL_PATH）
      - AliasAttPT 小头权重（从 ADAPTER_DIR/pytorch_model.bin）

    提供单例接口，保证整个进程只加载一次。
    """

    _instance = None

    def __init__(self):
        device = "cuda" if torch.cuda.is_available() else "cpu"
        self.device = device
        print("BASE_MODEL_PATH exists?", os.path.isdir(BASE_MODEL_PATH), BASE_MODEL_PATH)
        print("ADAPTER_DIR exists?", os.path.isdir(ADAPTER_DIR), ADAPTER_DIR)
        # 1) 从 Qwen 基座目录加载 tokenizer，而不是从 adapter 目录
        #    adapter 目录通常没有 tokenizer 配置文件。
        self.tokenizer = AutoTokenizer.from_pretrained(
            BASE_MODEL_PATH,
            trust_remote_code=True,
            local_files_only=True,  # 不从网上下，纯本地
        )
        if self.tokenizer.pad_token is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token
            self.tokenizer.pad_token_id = self.tokenizer.eos_token_id

        # 2) 从 Qwen 基座目录加载 base_model
        self.base_model = AutoModelForCausalLM.from_pretrained(
            BASE_MODEL_PATH,
            torch_dtype=torch.float16 if device == "cuda" else torch.float32,
            trust_remote_code=True,
            local_files_only=True,
        ).to(device)

        # 3) 构造 AliasAttPT 小头结构（参数要和训练时一致）
        self.alias_model = AliasAttPTModel(
            base_model=self.base_model,
            num_virtual_tokens=32,   # 按你训练时的设置来改
            num_attn_heads=8,        # 同上
        )

        # 4) 从 adapter 目录加载小头权重
        adapter_ckpt = os.path.join(ADAPTER_DIR, "pytorch_model.bin")
        if not os.path.exists(adapter_ckpt):
            raise FileNotFoundError(f"找不到小头权重文件: {adapter_ckpt}")

        state_dict = torch.load(adapter_ckpt, map_location=device)
        self.alias_model.load_state_dict(state_dict, strict=True)
        self.alias_model.to(device)
        self.alias_model.eval()

    @classmethod
    def instance(cls) -> "AliasModelManager":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance