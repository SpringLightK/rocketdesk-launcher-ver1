# -*- coding: utf-8 -*-  # 指定源码文件编码为 UTF-8，保证中文注释不乱码

import torch  # 导入 PyTorch 主包
import torch.nn as nn  # 导入神经网络模块
from transformers import AutoModelForCausalLM  # 导入自回归语言模型通用加载类


class AliasAttPTModel(nn.Module):
    """
    AliasAttPT（Alias Attention Prompt Tuning）模型
    冻结大模型，只训练：
      1）一串虚拟 prompt 向量
      2）一个带注意力的小网络，让 prompt 向量去“看”原句 embedding，从而生成上下文相关的 prompt
    """

    def __init__(
        self,
        base_model: AutoModelForCausalLM,  # 冻结的基座 Qwen 模型
        num_virtual_tokens: int = 32,  # 虚拟 prompt token 的个数
        num_attn_heads: int = 8,  # 小注意力网络的头数
    ):
        super().__init__()  # 调用父类构造函数

        # 保存基座模型到成员变量
        self.base_model = base_model  # 冻结的大模型

        # 冻结基座模型所有参数，不参与训练
        for param in self.base_model.parameters():  # 遍历基座模型所有参数
            param.requires_grad = False  # 关闭梯度更新

        # 从基座模型配置中读取隐藏维度
        hidden_size = self.base_model.config.hidden_size  # 隐藏向量维度大小

        # 定义一串可训练的虚拟 prompt 向量（形状为 [num_virtual_tokens, hidden_size]）
        self.prompt_embeddings = nn.Parameter(  # 使用 nn.Parameter 声明可训练张量
            torch.randn(num_virtual_tokens, hidden_size)  # 初始化为标准正态分布随机数
        )  # 结束 prompt_embeddings 定义

        # 记录虚拟 token 的个数，方便后面构造 batch
        self.num_virtual_tokens = num_virtual_tokens  # 保存虚拟 token 数量

        # 定义一个多头注意力层，让 prompt 向量作为 Query，句子 embedding 作为 Key/Value
        self.attn = nn.MultiheadAttention(
            embed_dim=hidden_size,  # 注意力输入/输出的特征维度
            num_heads=num_attn_heads,  # 多头注意力的头数
            batch_first=True,  # 设为 True，输入输出的形状为 [batch, seq_len, hidden]
        )  # 结束注意力层定义

        # 再加一个前馈网络，对注意力输出做一个简单变换
        self.ffn = nn.Sequential(  # 使用 Sequential 串联多层
            nn.Linear(hidden_size, hidden_size),  # 线性层：hidden -> hidden
            nn.ReLU(),  # 非线性激活函数
            nn.Linear(hidden_size, hidden_size),  # 再映射回 hidden 维度
        )  # 结束前馈网络定义

        # LayerNorm，用于规范化 prompt 表示，稳定训练
        self.prompt_layer_norm = nn.LayerNorm(hidden_size)  # 对 hidden 维度做 LayerNorm

    def forward(
        self,
        input_ids=None,  # 输入 token id 序列 [batch, seq_len]
        attention_mask=None,  # 注意力 mask，1 表示有效 token，0 表示 padding
        labels=None,  # 标签序列 [batch, seq_len]，非 -100 位置参与 loss
        **kwargs,  # 预留额外关键字参数，兼容 Trainer
    ):
        """
        前向计算逻辑：
          1）先用基座模型的 embedding 层将 input_ids 转成 embedding
          2）根据句子 embedding，通过注意力让 prompt 向量“看”句子
          3）生成上下文相关的 prompt embedding
          4）把 prompt embedding 拼在句子 embedding 前面交给基座模型
          5）labels 相应前面补一段 -100，保证只对原句子中 alias 部分算 loss
        """

        # 1. 使用基座模型的 embedding 层，将 input_ids 转成 embedding
        inputs_embeds = self.base_model.get_input_embeddings()(input_ids)  # [batch, seq_len, hidden]

        # 获取当前 batch 大小
        batch_size = input_ids.size(0)  # 从 input_ids 形状中取出 batch 维度

        # 2. 构造 batch 维度的 prompt 初始向量（把 [num_virtual_tokens, hidden] 扩展成 [batch, num_virtual_tokens, hidden]）
        prompt_embeds = self.prompt_embeddings.unsqueeze(0).expand(  # 在第 0 维加 batch 维，再扩展
            batch_size,  # batch 大小
            -1,  # 虚拟 token 数保持不变
            -1,  # hidden 维度保持不变
        )  # 结果形状为 [batch, num_virtual_tokens, hidden]

        # 3. 用注意力让 prompt 向量去“看”句子 embedding，生成上下文相关的 prompt
        # MultiheadAttention 的调用形式为：attn(query, key, value)
        # 此处 query = prompt_embeds, key/value = inputs_embeds
        attn_output, _ = self.attn(
            query=prompt_embeds,  # 查询向量，来自虚拟 prompt
            key=inputs_embeds,  # 键向量，来自原句 embedding
            value=inputs_embeds,  # 值向量，来自原句 embedding
        )  # attn_output 形状为 [batch, num_virtual_tokens, hidden]

        # 把注意力的输出加回 prompt_embeds，形成残差结构
        prompt_context = prompt_embeds + attn_output  # 残差相加，形状不变

        # 再通过前馈网络进一步变换
        prompt_context = self.ffn(prompt_context)  # [batch, num_virtual_tokens, hidden]

        # 做 LayerNorm，增加稳定性
        prompt_context = self.prompt_layer_norm(prompt_context)  # 归一化后的 prompt 表示

        # 4. 把生成好的 prompt_context 拼在原句 embedding 前面
        full_embeds = torch.cat(
            [prompt_context, inputs_embeds],  # 在序列维度上拼接 prompt + 原句 embedding
            dim=1,  # 序列长度所在的维度为 1
        )  # full_embeds 形状为 [batch, num_virtual_tokens + seq_len, hidden]

        # 5. 构造对应的 attention_mask
        if attention_mask is not None:  # 如果传入了 attention_mask
            # 为 prompt 部分构造全 1 的 mask，表示这些位置都参与注意力计算
            prompt_mask = torch.ones(
                batch_size,  # batch 大小
                self.num_virtual_tokens,  # prompt 序列长度
                dtype=attention_mask.dtype,  # 数据类型与原 attention_mask 一致
                device=attention_mask.device,  # 放在同一个设备上
            )  # prompt_mask 形状为 [batch, num_virtual_tokens]

            # 把 prompt 的 mask 和原 attention_mask 拼在一起
            full_attention_mask = torch.cat(
                [prompt_mask, attention_mask],  # 拼接 prompt mask 和原 mask
                dim=1,  # 在序列长度维度拼接
            )  # full_attention_mask 形状为 [batch, num_virtual_tokens + seq_len]
        else:
            # 如果没有提供 attention_mask，就直接设为 None
            full_attention_mask = None  # 基座模型内部会自行处理

        # 6. 处理 labels：前面为 prompt 部分补一段 -100（表示不参与 loss）
        if labels is not None:  # 如果提供了标签
            # 构造全 -100 的 prompt_label，用于 prompt 部分
            prompt_labels = torch.full(
                (batch_size, self.num_virtual_tokens),  # 形状为 [batch, num_virtual_tokens]
                -100,  # CrossEntropyLoss 的 ignore_index，表示忽略这些位置
                dtype=labels.dtype,  # 与 labels 的数据类型一致
                device=labels.device,  # 放在同一设备
            )  # prompt_labels 形状为 [batch, num_virtual_tokens]

            # 把 prompt_labels 和原 labels 拼在一起
            full_labels = torch.cat(
                [prompt_labels, labels],  # 先是 prompt 的 -100，再是句子的 labels（只对 alias 部分非 -100）
                dim=1,  # 在序列长度维度拼接
            )  # full_labels 形状为 [batch, num_virtual_tokens + seq_len]
        else:
            # 若没有传 labels，则置为 None
            full_labels = None  # 推理阶段可以不需要 labels

        # 7. 调用基座模型进行前向计算，此时使用的是 inputs_embeds 而不是 input_ids
        outputs = self.base_model(
            inputs_embeds=full_embeds,  # 使用我们构造的完整 embedding 作为输入
            attention_mask=full_attention_mask,  # 对应的注意力 mask
            labels=full_labels,  # 带有 prompt 部分 -100 的标签
            use_cache=False,  # 训练时关闭缓存
            **kwargs,  # 传递其他可能的关键字参数
        )  # 基座模型会返回 loss 和 logits 等信息

        # 直接返回基座模型的输出
        return outputs  # Trainer 会从 outputs.loss 中取出损失进行优化

