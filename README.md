# 代码解释与文档生成工作流

这个项目包含两个命令行入口。`main.py` 用于解释代码，支持按需读取文件和多轮问答；`workflow_main.py` 用于生成代码文档，依次执行分析、撰写和审校三个节点。

文档工作流复用代码解释功能中的模型客户端、文件读取工具和调用重试逻辑。三个节点各自使用独立的提示词和对话记录，通过编排器传递结果。

## 仓库地址

- GitHub：<https://github.com/HenryCreel-25/SE-homework2>

## 功能

- 代码问答：模型可调用 `read_file` 和 `list_files`，并保留多轮对话记录。
- 文档工作流：三个节点顺序处理同一份代码，保存各阶段结果和运行状态。
- 离线演示：`--demo` 可在不调用模型接口的情况下检查流程。

## 技术依赖

- 语言：Python 3.10+
- 模型接口：DeepSeek（默认 `deepseek-chat`）
- 依赖：`openai`（SDK）、`python-dotenv`（读取 `.env`）

## 安装

需要 Python 3.10 或更高版本。调用模型接口时，还需要 [DeepSeek API Key](https://platform.deepseek.com)。

```bash
cd code-agent
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## 配置 API Key

1. 复制示例配置：

   ```bash
   # Windows
   copy .env.example .env
   # macOS / Linux
   cp .env.example .env
   ```

2. 编辑 `.env`，填入你的 Key：

   ```dotenv
   DEEPSEEK_API_KEY=sk-你的真实Key
   ```

   `.env` 已列入 `.gitignore`，提交前仍应检查仓库中是否包含密钥。也可以直接设置环境变量 `DEEPSEEK_API_KEY`。

可选环境变量：

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `DEEPSEEK_API_KEY` | 无 | 必填，你的 API Key |
| `DEEPSEEK_MODEL` | `deepseek-chat` | 模型名（函数调用请使用 `deepseek-chat`） |
| `DEEPSEEK_BASE_URL` | `https://api.deepseek.com` | 接口地址 |

## 使用方法

### 代码解释：交互式对话

```bash
python main.py
```

示例：

```
你 > 请解释 examples/sample.py
Agent 思考中…
Agent > 这段代码定义了一个 calculate_total 函数……
```

可用命令：

| 命令 | 作用 |
|------|------|
| `/help` | 查看帮助 |
| `/clear` | 清空对话上下文 |
| `/exit` | 退出 |

### 单次问答

```bash
python main.py --once "请解释 examples/sample.py"
```

### 离线演示（无需 Key）

```bash
python main.py --demo
# 或
python main.py --demo --once "请解释 examples/sample.py"
```

离线演示会走一遍文件读取和回答流程，回答内容不代表实际模型分析。

### 可以这样提问

- 指向文件：`请解释 examples/sample.py`
- 直接贴代码：`下面这段代码是什么意思？`（随后粘贴代码）
- 代码问题：`calculate_total 为什么要检查 discount 的范围？`

## 项目结构

```
code-agent/
├── main.py                 # 代码解释入口
├── workflow_main.py        # 文档工作流入口
├── requirements.txt        # 依赖清单
├── .env.example            # 配置模板（复制为 .env 使用）
├── agent/
│   ├── config.py           # 全局配置
│   ├── llm.py              # LLM 调用层（DeepSeek / Demo 客户端）
│   ├── prompts.py          # Prompt 设计
│   ├── tools.py            # 工具定义与执行
│   ├── memory.py           # 上下文记忆
│   └── agent.py            # Agent 核心循环
├── workflow/
│   ├── core.py             # 顺序编排、交接与运行状态
│   ├── prompts.py          # 三个 Agent 的角色定义
│   └── demo.py             # 离线工作流演示客户端
├── examples/
│   └── sample.py           # 示例代码
└── tests/                  # 单元测试
```

## 测试

```bash
python -m unittest discover -s tests -t .
```

## 代码文档工作流

输入单个源代码文件。分析节点输出代码说明，文档节点据此写草稿，审校节点对照源代码修订草稿。最终结果保存为 Markdown 文件。

```bash
# 使用 DeepSeek，需配置 DEEPSEEK_API_KEY
python workflow_main.py --file examples/sample.py

# 不调用模型接口，检查节点执行与结果交接
python workflow_main.py --demo --file examples/sample.py

# 指定输出根目录
python workflow_main.py --file examples/sample.py --output-dir runs
```

每次运行会在 `runs/<运行编号>/` 中保存：

| 文件 | 含义 |
|------|------|
| `analysis.md` | 分析 Agent 的输出 |
| `draft.md` | 文档 Agent 的草稿 |
| `review.json` | 审校意见及审校后的完整文档 |
| `final.md` | 最终交付文档 |
| `state.json` | 每个节点的输入来源、状态、时间与错误信息 |

工作流一次处理一个非空文本代码文件。文件类型和 200 KB 大小限制由 `agent/tools.py` 控制，工作流另设 20,000 字符的输入上限。节点失败后，已完成的产物和 `state.json` 会保留。审校结果若不是有效 JSON，会重试一次。

测试覆盖原有代码解释功能以及工作流的节点交接、失败停止和审校格式修复。`--demo` 只检查编排；文档准确性需要在实际调用模型后对照源代码核查。

实现细节见 [Design.md](Design.md)。
