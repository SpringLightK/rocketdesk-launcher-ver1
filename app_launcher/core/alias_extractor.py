# app_launcher/core/alias_extractor.py
from typing import Tuple
import torch
from app_launcher.core.alias_model import AliasModelManager
from app_launcher.core.alias_att_pt_model import AliasAttPTModel
def clean_alias(alias_part: str, input_text: str) -> str:
    # 1. 取第一行
    alias_line = alias_part.strip().splitlines()[0].strip()

    # 2. 先干掉明显的对话标记
    for sep in ["Human:", "Assistant:", "User:", "AI:", "系统:", "用户:", "助手:"]:
        if sep in alias_line:
            alias_line = alias_line.split(sep)[0].strip()

    # 2.5 如果整段就出现在原句中，直接用
    if alias_line and alias_line in input_text:
        return alias_line.strip(" ：:，,。.!? ")

    # 3. 对于中/韩这种没空格的情况：在 input_text 里找「最长片段」跟 alias_line 重叠
    candidates = []
    for i in range(len(input_text)):
        for j in range(i + 1, len(input_text) + 1):
            phrase = input_text[i:j].strip()
            if phrase and phrase in alias_line:
                candidates.append(phrase)

    if candidates:
        candidates.sort(key=len, reverse=True)
        best = candidates[0].strip(" ：:，,。.!? ")
        return best

    # 4. 最后再用你之前的英文 token 逻辑兜底（可选）
    tokens = alias_line.split()
    for i in range(len(tokens)):
        for j in range(i + 1, len(tokens) + 1):
            phrase = " ".join(tokens[i:j]).strip()
            if phrase and phrase in input_text:
                candidates.append(phrase)

    if candidates:
        candidates.sort(key=len, reverse=True)
        best = candidates[0].strip(" ：:，,。.!? ")
        return best

    # 5. 实在抠不出来就返回空
    return ""


def build_prefixed_inputs(
    model: AliasAttPTModel,       # 我们的 AliasAttPT 模型
    input_ids: torch.Tensor,      # 原始 input_ids，形状 [batch, seq_len]
    attention_mask: torch.Tensor, # 原始 attention_mask，形状 [batch, seq_len]
):
    """
    根据 AliasAttPT 的逻辑构造前缀：
      - 用小头的注意力计算出上下文相关的 prompt_context
      - 把 prompt_context 拼在原句 embedding 前面
      - 同时构造对应的 attention_mask

    这里最关键的一步：把所有相关张量和小头权重的 dtype
    统一成和 base_model 的 embedding 输出一样，避免 Half / Float 打架。
    """

    # 0. 从小头中取出基座模型
    base_model = model.base_model  # 冻结的大模型

    # 1. 使用基座模型的 embedding 层将 input_ids 转为 embedding
    inputs_embeds = base_model.get_input_embeddings()(input_ids)  # [batch, seq_len, hidden]

    # 取出当前实际使用的 dtype（可能是 fp16，也可能是 fp32）
    base_dtype = inputs_embeds.dtype  # 比如 torch.float16 或 torch.float32

    # 为了安全，统一把小头的参数也 cast 到这个 dtype 和设备上
    model.attn.to(device=inputs_embeds.device, dtype=base_dtype)             # 注意力层权重 dtype 对齐
    model.ffn.to(device=inputs_embeds.device, dtype=base_dtype)              # 前馈网络权重 dtype 对齐
    model.prompt_layer_norm.to(device=inputs_embeds.device, dtype=base_dtype)  # LayerNorm 权重 dtype 对齐

    # 2. 构造 batch 维度的虚拟 prompt 初始向量
    #    这里不能直接用原来的 model.prompt_embeddings（它可能是 float32），
    #    我们要先把它 cast 成和 inputs_embeds 一样的 dtype，再扩展 batch 维。
    prompt_weight = model.prompt_embeddings.to(  # 把参数 cast 到统一 dtype 和设备
        device=inputs_embeds.device,
        dtype=base_dtype,
    )  # 形状仍然是 [num_virtual_tokens, hidden]

    prompt_embeds = prompt_weight.unsqueeze(0).expand(
        inputs_embeds.size(0),  # batch 大小
        -1,                     # 虚拟 token 数量不变
        -1,                     # hidden 维度不变
    )  # 得到 [batch, num_virtual_tokens, hidden]，dtype 与 inputs_embeds 一致

    # 3. 用多头注意力让 prompt_embeds 去“看”句子 embedding
    attn_output, _ = model.attn(
        query=prompt_embeds,   # 查询：虚拟 prompt（已经是 base_dtype）
        key=inputs_embeds,     # 键：原句 embedding（base_dtype）
        value=inputs_embeds,   # 值：原句 embedding（base_dtype）
    )  # 得到 attn_output，形状 [batch, num_virtual_tokens, hidden]，dtype 同样为 base_dtype

    # 残差连接：prompt_embeds + 注意力输出
    prompt_context = prompt_embeds + attn_output  # 形状不变，dtype 仍是 base_dtype

    # 通过前馈网络
    prompt_context = model.ffn(prompt_context)  # 形状 [batch, num_virtual_tokens, hidden]

    # 通过 LayerNorm 提升稳定性
    prompt_context = model.prompt_layer_norm(prompt_context)  # 形状不变

    # 4. 把 prompt_context 拼在原句 embedding 前面
    full_embeds = torch.cat(
        [prompt_context, inputs_embeds],  # [batch, num_virtual_tokens + seq_len, hidden]
        dim=1,                            # 在序列长度维度拼接
    )  # full_embeds 的 dtype 与 base_dtype 一致

    # 5. 构造对应的 attention_mask
    if attention_mask is not None:  # 如果提供了原始 mask
        # 为 prompt 部分构造全 1 的 mask（全部参与注意力）
        prompt_mask = torch.ones(
            attention_mask.size(0),        # batch 大小
            model.num_virtual_tokens,      # prompt token 数量
            dtype=attention_mask.dtype,    # 和原 attention_mask 同 dtype（一般是 long）
            device=attention_mask.device,  # 同一设备
        )  # 形状 [batch, num_virtual_tokens]

        # 拼接 prompt_mask 和原 attention_mask
        full_attention_mask = torch.cat(
            [prompt_mask, attention_mask],  # 得到 [batch, num_virtual_tokens + seq_len]
            dim=1,                          # 在序列维度拼接
        )
    else:
        full_attention_mask = None  # 如果没有 mask，就直接设置为 None

    # 返回构造好的 embedding 和 attention_mask
    return full_embeds, full_attention_mask


def generate_alias(input_text: str) -> str:
    """
    高层接口：GUI 只用传一条字符串进来，拿到 alias 字符串。
    模型的加载、device 管理都由 AliasModelManager 负责。
    """
    mgr = AliasModelManager.instance()
    model = mgr.alias_model
    tokenizer = mgr.tokenizer
    device = mgr.device

    prompt = f"用户指令: {input_text}\n对应的App别名: "

    inputs = tokenizer(prompt, return_tensors="pt")
    input_ids = inputs["input_ids"].to(device)
    attention_mask = inputs["attention_mask"].to(device)

    full_embeds, full_attention_mask = build_prefixed_inputs(
        model=model,
        input_ids=input_ids,
        attention_mask=attention_mask,
    )

    with torch.no_grad():
        output_ids = model.base_model.generate(
            inputs_embeds=full_embeds,
            attention_mask=full_attention_mask,
            max_new_tokens=8,
            do_sample=False,
            num_beams=1,
            eos_token_id=tokenizer.eos_token_id,
            pad_token_id=tokenizer.pad_token_id,
        )

    generated_text = tokenizer.decode(output_ids[0], skip_special_tokens=True)

    marker = "对应的App别名:"
    if marker in generated_text:
        alias_part = generated_text.split(marker)[-1]
    else:
        alias_part = generated_text

    alias = clean_alias(alias_part, input_text)
    return alias
