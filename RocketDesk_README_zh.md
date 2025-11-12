# RocketDesk / Alias App Launcher

桌面应用**自然语言搜索 + 快速启动**小工具。  
支持中文 / 韩文 / 英文混合指令，例如：

- `打开微信`
- `카카오 켜봐`
- `멜론 열어줘`
- `실행해줘 Melon`

工具会自动从指令中抽取**应用别名**，在你配置好的桌面应用列表中做相似度匹配，然后一键启动对应程序。

---

## 1. 功能简介

### 🖥 桌面应用启动器

- 支持**自定义应用列表**：手动添加或一键扫描桌面 / 快捷方式 / 文件夹
- 每个应用可以配置**多个别名**（例如“微信 / WeChat / 微信聊天”等）
- 可以从配置里删除应用、重命名路径、管理别名

### 🔍 自然语言别名识别

- 使用 **Qwen-Instruct 基座模型 + AliasAttPT 小头** 对输入指令做别名抽取
- 支持中/韩/英混合句子，从整句中找出真正的“应用名”片段
- 例如：  
  - 输入：`我要去学校，把카카오 맵打开` → 抽取：`카카오 맵`  
  - 输入：`실행해줘 Melon` → 抽取：`Melon`

### 🤝 语义相似度匹配

- 对所有 **应用别名** 预先计算句向量嵌入（带磁盘缓存）  
- 搜索时对用户抽取出的别名做一次编码，和已存别名做相似度匹配  
- 返回 Top‑K（默认 3 个）候选：  
  - 显示“原始应用名 / 匹配到的别名 / 可执行路径 / 相似度”

### 🪟 悬浮窗 + 系统托盘

- 悬浮窗：
  - 只占一行的搜索框 + 搜索按钮
  - 支持回车触发搜索
  - 搜索结果列表支持双击启动应用
  - 结果区域可以一键收起，保持桌面干净
- 系统托盘：
  - 自定义 Logo（放大镜 + 火箭）
  - 右键菜单：
    - 显示 / 隐藏悬浮窗
    - 打开“启动 App 设置”
    - 打开“查询配置”
    - 退出程序

---

## 2. 目录结构概览

仓库核心结构大致如下：

```text
app_launcher/
  core/             # 模型封装、匹配逻辑、桌面扫描等
  gui/              # PyQt5 图形界面（悬浮窗、托盘、设置对话框）
  img/              # 应用图标 app_icon.ico / 源 SVG
  config/           # 配置文件（如 apps_config.json、嵌入缓存等）
  models/           # 模型目录（需要自行下载 / 准备，见下文）
    qwen-instruct-1.5/
    train_augmented/
      alias_att_pt_adapter/
  utils/            # 路径等辅助工具
  main.py           # 程序入口：python -m app_launcher.main
```

> ⚠️ **仓库里不会包含编译好的 exe 文件**，也不强制把模型打包进 exe。  
> exe 可以按下面“打包为 exe”一节在本地自行生成。

---

## 3. 模型说明

当前版本使用 **两个本地模型**：

1. **Qwen-Instruct 基座模型**  
   - 放在：`app_launcher/models/qwen-instruct-1.5/`
   - 用于提供基础语言理解与生成能力

2. **AliasAttPT 适配器（P‑Tuning 小头）**  
   - 放在：`app_launcher/models/train_augmented/alias_att_pt_adapter/`
   - 只负责从整句中“抠出”应用别名，参数量相对较小

路径由 `app_launcher/models/paths.py` 统一管理：

```python
from app_launcher.models.paths import BASE_MODEL_PATH, ADAPTER_DIR
```

只要你在本地把模型目录放在上述位置，程序就能直接使用。

---

## 4. 运行方式

### 4.1 开发环境运行

1. 安装依赖（示例）

> 主要依赖：  
> - Python 3.9+  
> - PyQt5  
> - torch  
> - transformers  
> - 以及项目内部用到的其他库

2. 确保模型目录存在：

```text
app_launcher/models/qwen-instruct-1.5/...
app_launcher/models/train_augmented/alias_att_pt_adapter/...
```

3. 运行：

```bash
python -m app_launcher.main
```

启动后：

- 系统托盘会出现一个 RocketDesk 图标（放大镜 + 火箭）
- 右键托盘 → “显示悬浮窗” 即可打开搜索窗口

---

## 5. 打包为 exe（本地自行生成）

本仓库 **不直接包含 exe 文件**，但可以使用 PyInstaller 在本地生成。  
以下示例以 Windows + PyInstaller 的 “onedir”为例：

1. 在项目根目录执行：

```bash
pyinstaller app_launcher\main.py --name RocketDesk --icon app_launcher\img\app_icon.ico --noconsole --add-data "app_launcher\img;app_launcher\img" --add-data "app_launcher\config;app_launcher\config"
```

生成后目录大致为：

```text
dist/
  RocketDesk/
    RocketDesk.exe
	_internal/
    app_launcher/
      img/
      config/
    pythonXX.dll
    其他运行时依赖...
```

2. 将模型目录放在 exe 同级的 `models` 文件夹下（与运行时逻辑一致）：

```text
dist/
  RocketDesk/
    RocketDesk.exe
    models/
      qwen-instruct-1.5/
      train_augmented/
        alias_att_pt_adapter/
```

根据 `paths.py` 的逻辑，程序会优先从 exe 同级的 `models/` 目录加载模型。


---

## 6. 当前问题：模型过重 & 资源占用

目前直接在本地加载：

- 一个完整的 Qwen 基座模型
- 再加上 AliasAttPT 适配器

现在带来几个明显问题：

1. **显存 / 内存占用非常高**  
   - 启动一次工具就需要加载整套大模型，动辄数 GB 以上  
   - 对于只做“别名抽取 + 简单推理”的任务来说，明显浪费

2. **冷启动时间长**  
   - 第一次加载模型耗时较久，对于一个桌面小工具来说体验一般

---

## 7. 未来计划：模型蒸馏

为了解决“读取两个模型非常繁重、内存吃得厉害”的问题，下一步计划是：

- 针对当前任务（**应用别名抽取 + 相似度匹配**）做一个 **小模型蒸馏版本**  

> 也可以把别名抽取这一块迁移到服务器上，由服务端模型完成推理、客户端只负责展示结果。 


