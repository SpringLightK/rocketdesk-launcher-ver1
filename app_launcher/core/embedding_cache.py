# app_launcher/core/embedding_cache.py
# -*- coding: utf-8 -*-

"""
把 (app_index, alias) 对应的向量缓存到一个 npz 文件里，避免每次重启都重算所有别名的嵌入。
"""

import os  # 处理路径
from typing import Dict, Tuple  # 类型注解（可选）

import numpy as np  # 存放 / 读写向量


# 缓存文件路径：放在 config 目录下
EMB_PATH = os.path.join(
    os.path.dirname(__file__),  # 当前文件所在目录 core/
    "..",                       # 上一级 app_launcher/
    "config",
    "app_embeddings.npz",       # 实际文件名
)


class EmbeddingCache:
    """
    简单的嵌入缓存：
    - 内存里用 dict 存 (app_index, alias) -> 向量
    - 磁盘上用 npz 存 keys 和 vecs
    """

    def __init__(self):
        """构造函数：初始化空缓存并尝试从磁盘加载"""
        self.cache: Dict[Tuple[int, str], np.ndarray] = {}  # 内存里的缓存字典
        self.load()  # 从本地 npz 文件读取已有缓存

    def load(self):
        """从 npz 文件加载缓存到内存"""
        if not os.path.exists(EMB_PATH):
            # 没有缓存文件就算了
            return
        data = np.load(EMB_PATH, allow_pickle=True)  # 读取 npz
        keys = data["keys"].tolist()  # 取出 keys（是一个 object 数组，里面是 (idx, alias)）
        vecs = data["vecs"]           # 取出向量矩阵
        # 重新组装成 dict
        self.cache = {tuple(k): vecs[i] for i, k in enumerate(keys)}

    def save(self):
        """把当前缓存写回 npz 文件"""
        if not self.cache:
            # 没有任何东西，直接删文件（如果有的话）
            if os.path.exists(EMB_PATH):
                os.remove(EMB_PATH)
            return

        # keys 是 (app_index, alias) 的元组列表
        keys = np.array(list(self.cache.keys()), dtype=object)
        # vecs 是对应的向量堆叠起来
        vecs = np.stack(list(self.cache.values()), axis=0)

        os.makedirs(os.path.dirname(EMB_PATH), exist_ok=True)
        np.savez(EMB_PATH, keys=keys, vecs=vecs)  # 保存为 npz

    def get(self, app_index: int, alias: str):
        """
        取出某个 (app_index, alias) 的向量
        :return: np.ndarray 或 None
        """
        return self.cache.get((app_index, alias))

    def set(self, app_index: int, alias: str, vec: np.ndarray):
        """
        设置 / 更新 某个 (app_index, alias) 的向量
        """
        self.cache[(app_index, alias)] = vec
