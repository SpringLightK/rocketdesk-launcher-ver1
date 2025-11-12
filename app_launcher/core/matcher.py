# app_launcher/core/matcher.py
# -*- coding: utf-8 -*-

"""
AppMatcher 负责两件事：

1. rebuild():
   - 遍历所有 app 的所有别名
   - 先从 EmbeddingCache 里取向量，取不到才用 encoder 计算
   - 一次性把所有别名向量堆在 alias_vectors 里
   - 同时记录 alias_meta（每个向量对应哪个 app / 哪个别名）

2. find_top_k(query_alias, k):
   - 对 query_alias 算一个向量
   - 和 alias_vectors 做相似度（点积）
   - 按分数排序，每个 app 只保留得分最高的一个别名，返回 top-k
"""

from typing import List, Dict  # 类型注解

import numpy as np  # 处理向量

from app_launcher.core.sentence_encoder import QwenSentenceEncoder  # 句向量编码器接口
from app_launcher.core.config_store import AppConfigStore          # 配置存储
from app_launcher.core.embedding_cache import EmbeddingCache       # 嵌入缓存


class AppMatcher:
    """基于所有别名的句向量，为 query_alias 找最相近的 app"""

    def __init__(self, encoder: QwenSentenceEncoder, store: AppConfigStore):
        """
        :param encoder: 句向量编码器，要求 encode(text 或 [text]) -> np.ndarray
        :param store:   AppConfigStore 实例，提供 apps 列表
        """
        self.encoder = encoder          # 保存编码器
        self.store = store              # 保存配置存储
        self.cache = EmbeddingCache()   # 嵌入磁盘缓存

        # alias_vectors: [num_aliases, hidden_dim]
        self.alias_vectors = np.zeros((0, 1), dtype=np.float32)
        # alias_meta: 长度 = num_aliases，每个元素是一个 dict，记录这个向量对应的 app / alias / 路径等信息
        self.alias_meta: List[Dict] = []

        # 启动时先重建一遍（如果缓存存在，会大量复用）
        self.rebuild()

    def rebuild(self):
        """
        配置变化时调用：
        - 遍历所有 app 的所有别名
        - 对每个 (app_index, alias):
            * 尝试从 cache 取向量
            * 没有就用 encoder.encode(alias) 算一次，并写回 cache
        - 全部别名的向量堆到 alias_vectors
        - alias_meta 记录每个向量的元信息
        - 最后把 cache.save() 写回本地 npz
        """
        all_vecs = []         # 用来存所有别名的向量
        self.alias_meta = []  # 清空 meta 列表

        for idx, app in enumerate(self.store.apps):
            app_id = app.get("id")
            base_name = app.get("base_name", app_id)
            exe_path = app.get("exe_path", "")
            aliases = app.get("aliases", []) or []

            for alias in aliases:
                # 1) 先试着从缓存里拿
                vec = self.cache.get(idx, alias)
                if vec is None:
                    # 2) 缓存没有，再用 encoder 算一次
                    # encoder.encode 支持单个字符串或字符串列表，这里直接传字符串
                    vec = self.encoder.encode(alias)[0]
                    self.cache.set(idx, alias, vec)

                all_vecs.append(vec)

                # 记录这个向量的元信息
                self.alias_meta.append({
                    "app_index": idx,      # 属于 store.apps 的哪一行
                    "app_id": app_id,      # app 的 id
                    "base_name": base_name,# app 的原始名称（用于显示）
                    "alias": alias,        # 这个向量对应的别名
                    "exe_path": exe_path,  # 对应的路径
                })

        if all_vecs:
            # 把所有向量堆成 [num_aliases, hidden_dim]
            self.alias_vectors = np.stack(all_vecs, axis=0)
        else:
            # 没有任何 app 时，保持一个空矩阵
            self.alias_vectors = np.zeros((0, 1), dtype=np.float32)

        # 把更新后的缓存写回本地文件
        self.cache.save()

    def find_top_k(self, query_alias: str, k: int = 3) -> List[Dict]:
        """
        用 query_alias 在所有别名里做相似度匹配，返回最多 k 个 app（按 app 去重）。

        返回的每个元素是一个 dict，字段包括：
        - app_index: 在 store.apps 里的行号
        - app_id:    app 的 id
        - base_name: app 的原始名称（显示用）
        - match_alias: 实际匹配到的别名
        - exe_path:  路径
        - score:     相似度分数（float）
        """
        query_alias = query_alias.strip()
        if not query_alias:
            return []
        if self.alias_vectors.shape[0] == 0:
            return []

        # 1) 对 query_alias 算一个向量
        q_vec = self.encoder.encode(query_alias)[0]  # [hidden_dim]

        # 如果 encoder 没做归一化，这里可以手动归一化一下（可选）
        # q_norm = np.linalg.norm(q_vec) + 1e-12
        # q_vec = q_vec / q_norm
        # v_norms = np.linalg.norm(self.alias_vectors, axis=1, keepdims=True) + 1e-12
        # vecs = self.alias_vectors / v_norms
        # sims = vecs @ q_vec

        # 简单起见：假设 encoder 已经输出归一化向量，直接点积就是余弦相似度
        sims = self.alias_vectors @ q_vec  # [num_aliases]

        # 2) 从大到小排序的索引
        idxs = np.argsort(-sims)

        results: List[Dict] = []
        used_app_indices = set()  # 已经选过的 app_index（保证每个 app 只出现一次）

        for idx in idxs:
            meta = self.alias_meta[idx]
            app_index = meta["app_index"]
            if app_index in used_app_indices:
                # 这个 app 已经通过另一个别名选过了，跳过
                continue
            used_app_indices.add(app_index)

            results.append({
                "app_index": app_index,
                "app_id": meta["app_id"],
                "base_name": meta["base_name"],   # 原始名称
                "match_alias": meta["alias"],     # 实际匹配到的别名
                "exe_path": meta["exe_path"],
                "score": float(sims[idx]),
            })

            if len(results) >= k:
                break

        return results
