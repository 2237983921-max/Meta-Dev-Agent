# 🚀 Meta-Dev: Fully-Automated Multi-Agent Software Factory

Meta-Dev 是一个基于 Python 构建的全自动多智能体（Multi-Agent）软件工场。它通过编排大语言模型（LLM），在本地实现从“一句话需求”到“多文件代码生成、自动化测试、本地沙盒自愈、Git 自动部署”的全链路闭环。

本项目证明了：如何用极简的原生 Python 代码，实现极其硬核的 Agent 本地操作系统级交互与持续集成（CI）流水线。

---

## ✨ 核心特性 (Core Features)

* **🧠 多智能体辩论与决策引擎**
    * 内置 PM（产品）、DEV（开发）、QA（测试）三大角色 Agent。
    * 基于严密的系统提示词工程，实现需求澄清、方案设计、代码编写与代码审查的自主轮转。
* **📂 智能多文件提取与落地**
    * 突破单文件限制，系统能够自动解析大模型输出，精准提取并在本地工作区构建多文件项目结构。
* **🛡️ 工业级本地沙盒与 Error-Reflection (错误反思)**
    * 代码自动在本地 Sandbox 中无干预运行。
    * **AST 静态分析**：自动判定并拦截阻塞型交互逻辑（精准区分 `input()` 与业务同名函数）。
    * **进程隔离**：标准输入（stdin）重定向至 `DEVNULL`，配合严格的超时打断机制，完美防止死循环与卡死。
    * 捕获的真实报错（stderr）将自动喂给 QA Agent，触发“错误反思”机制进行闭环自愈。
* **🧪 动态智能测试路由**
    * 系统具备环境感知能力。生成产物后，智能探测并优先执行测试文件。
    * 自动识别并调度 `pytest` 或 `unittest discover`，在无测试文件时平滑回退至主脚本执行。
* **🛑 强干预质量门禁与自动化 Git 存档**
    * 引入严格的质量护栏（Quality Gates），拒绝失败/超时状态下的强制通过（Pass）。
    * 代码验证通过后，系统自动呼叫 PM Agent 生成规范的 Commit Message，并调用 `subprocess` 完成本地 Git 仓库的自动提交与存档。

---

## ⚙️ 系统工作流 (Workflow)

1. **输入需求**：人类 Boss 输入自然语言需求（如：“写一个带难度选择的猜数字游戏”）。
2. **产品定义**：PM Agent 输出详细的开发文档与验收标准。
3. **代码生成**：DEV Agent 编写代码，系统自动剥离并保存为本地实体文件（单文件或多文件）。
4. **沙盒质检**：系统自动调用 `pytest`/`unittest` 或直接执行脚本，捕获运行状态与异常日志。
5. **AI 审查与自愈**：QA Agent 结合生成的代码与真实运行日志，进行逻辑审查并指出 Bug；流程回转至 DEV 进行修改，直至测试通过。
6. **自动存档**：人工最终确认放行后，系统自动生成摘要并完成 `git commit`。

---

## 🛠️ 快速启动 (Quick Start)

**1. 克隆项目**
git clone https://github.com/YourUsername/Meta-Dev-Agent.git
cd Meta-Dev-Agent

**2. 安装依赖**
pip3 install openai pytest

**3. 配置环境变量**
export OPENAI_API_KEY="sk-你的真实密钥"
export OPENAI_BASE_URL="如果你使用中转站，请配置此项"

**4. 启动软件工场**
python3 meta_dev_core.py
