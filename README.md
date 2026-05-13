# twitter-kol-eva

> 一个命令行小工具：你给它一个 Twitter / X 账号 + 报价，它自动抓取最近的推文，算出 6 个 KOL 评估指标。

**👋 给非技术背景的你：** 这个 README 是按"你从来没跑过 Python 项目也能跟着走通"的标准写的。每一步都告诉你**要打什么命令**和**这一步在干嘛**。如果哪一步卡住，跳到本文末尾的 [出问题怎么办](#出问题怎么办)。

---

## 这个工具能干嘛？

你给它两样东西：
- 一个 Twitter 账号（比如 `@elonmusk`，或者 `https://x.com/elonmusk` 这种链接都可以）
- 这个账号一条赞助推文的报价（比如 500 美元）

它会：
1. 打开一个无头浏览器，登录 Twitter（用你提前导出的 cookie）
2. 翻看这个账号最近的 20 条原创推文（默认；可以改）
3. 抓下每条的**点赞 / 评论 / 转发 / 曝光**
4. 算出 6 个指标 + 用到的样本明细
5. 在终端打印一张漂亮的表格，也可以同时存成 JSON 文件

整个过程大约 30 秒到 2 分钟（取决于你的网络）。

---

## 它会算出哪 6 个指标？

| 指标 | 公式 | 怎么读 |
|------|------|--------|
| **ER（粉丝互动率）** | (点赞+评论+转发) / 粉丝数 | 衡量粉丝有多真。1% 算正常，2% 以上算优秀。 |
| **View ER（曝光互动率）** | (点赞+评论+转发) / 平均曝光 | 排除僵尸粉之后真正的互动质量。3% 以上算优秀。 |
| **C/L Ratio（评论深度比）** | 评论数 / 点赞数 | < 1% 是买赞警报，5% 以上说明内容真在引发讨论。 |
| **Reach Rate（粉丝触达率）** | 平均曝光 / 粉丝数 | 算法给不给推。> 100% 说明经常被推到非粉丝。 |
| **数据稳定性** | 最高曝光 / 最低曝光 | < 5x 算正常，> 10x 数据可能不可靠（爆款 + 哑火混在一起）。 |
| **CPM（千次曝光成本）** | 报价 / (平均曝光 / 1000) | 千次曝光要花你多少钱。CPM 越低越划算。 |

---

## 你需要先准备什么？

1. **一台电脑**：Mac / Windows / Linux 都行
2. **一个 Twitter / X 账号**：自己平时刷的那个就行，**不需要付费 API**
3. **一点终端时间**：第一次大约 15 分钟把环境装好；之后每次跑只要 1 分钟

> "终端 / 命令行"指的是 Mac 的 **Terminal**（应用程序 → 实用工具 → 终端）或 Windows 的 **PowerShell**（在搜索里输 PowerShell）。本文出现的命令都贴在终端里回车执行。

---

## 第一次安装（约 10 分钟）

### 第 1 步：装 uv（Python 的包管理器）

uv 是一个一行命令搞定 Python 环境的工具。

**Mac / Linux：**
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**Windows（PowerShell）：**
```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

装完之后**关掉终端再开一个新的**（让系统知道 uv 命令在哪），然后打：
```bash
uv --version
```
能看到一个版本号就说明装好了。

> 这一步在干嘛：装一个工具，后面我们用它来管理 Python 依赖，比手动用 pip 省心很多。

### 第 2 步：把代码下载到本地

挑一个你想存代码的文件夹（比如 Mac 上的 `~/Documents`），打开终端 `cd` 过去，然后：
```bash
git clone https://github.com/shuangw209/twitter-kol-eva.git
cd twitter-kol-eva
```

> 这一步在干嘛：从 GitHub 把代码下到你电脑上。

### 第 3 步：装依赖

```bash
uv sync
uv run playwright install chromium
```

第二条会下载一个干净的 Chromium 浏览器（专门给程序用的，不影响你日常用的 Chrome）。这一步要联网，可能要 1-2 分钟。

> 这一步在干嘛：把 Python 库（playwright、click、rich 等）装到项目自己的小盒子（虚拟环境）里，不会污染你系统的 Python。

### 第 4 步：建一个 `.env` 配置文件

```bash
cp .env.example .env
```

> 这一步在干嘛：把模板复制一份成 `.env`，工具运行时会读这个文件。

**默认值就能跑，你可以直接进下一步（第 5 步）**——`.env` 里面预设的就是下面这些值，不改也能用：

```
TWITTER_COOKIE_FILE=~/.twitter_cookies.json
DEFAULT_CURRENCY=USD
DEFAULT_RECENT_N=20
```

含义分别是：cookie 文件存在哪、报价单位标签、默认采样多少条推文。

#### （可选）想看 / 改 `.env` 的话怎么打开它？

`.env` 是"以点开头"的文件，Mac 的 Finder 和 Windows 的资源管理器默认会隐藏它。最简单的做法是在终端里用编辑器命令直接打开。

> ⚠️ **下面的命令直接复制整行就好，不要再加任何文字或 `#` 注释**——某些 shell（比如 Mac 默认的 zsh 交互模式）不会把 `#` 当注释，会把后面的字也当成文件名报错。

**Mac**（在 twitter-kol-eva 目录下）。用系统自带的 TextEdit：
```bash
open -e .env
```

装了 VS Code 的话（命令行工具要先装好）：
```bash
code .env
```

如果想在 Finder 里看到隐藏文件，按 `Cmd + Shift + .` 切换显示。

**Windows**（PowerShell）：
```powershell
notepad .env
```

**Linux**。终端内编辑（按 `Ctrl+O` 保存、`Ctrl+X` 退出）：
```bash
nano .env
```

或者图形界面（如果装了）：
```bash
gedit .env
```

### 第 5 步：登录 Twitter，导出 cookie（最关键一步）

这一步本质上是：用真实浏览器登录一次 Twitter，把登录状态保存到一个本地文件，让程序能"借"你的登录态去看推文页面。

#### 路径 A：自动登录（先试这个）

```bash
uv run tweval login
```

会发生什么：
1. 一个浏览器窗口自动弹出，打开 X 的登录页（优先用你系统装的 Chrome；没装就用 Playwright 自带的 Chromium）
2. 你像平时一样输用户名 + 密码（如果有 2FA 就过 2FA）
3. 登录成功，看到自己的 home timeline 之后，**回到终端按一下回车**
4. 程序会把 cookie 存到 `~/.twitter_cookies.json`，然后自动关闭浏览器

> 这一步在干嘛：让脚本以"已登录的你"身份去访问 Twitter，否则 Twitter 会要求登录，曝光数也看不到。
>
> **重要：** 这个 cookie 文件等于你的登录令牌，**不要分享、不要传到任何 repo**。`.gitignore` 已经把它拦在 git 之外。

#### 路径 B：手动导出（如果路径 A 卡在登录页 / 输完账号弹回）

Twitter / X 有时候会识别出 Playwright 自动化的浏览器并拒绝登录——表现就是"输完用户名点 Next 又弹回输入页面"。这种情况下走手动路径，**100% 能成功**。

**操作步骤（Mac / Windows / Linux 通用）：**

1. 用你**平时刷 Twitter 的那个 Chrome**（不是脚本弹的那个），确保已经登录了 https://x.com。

2. 给 Chrome 装一个叫 **Cookie-Editor** 的扩展：
   - 装：https://chromewebstore.google.com/detail/cookie-editor/hlkenndednhfkekhgcdicdfddnkalmdm

3. 在已经登录 X 的那个 Chrome 标签里：
   - 点右上角 Cookie-Editor 扩展图标
   - 看到 cookie 列表后，点底部 **Export** → 选 **Export as JSON**
   - JSON 内容现在在你的剪贴板里

4. 跑工具自带的转换命令（它会从剪贴板读取，转成 Playwright 格式，存到默认路径）：

   ```bash
   uv run tweval import-cookies
   ```

   你也可以指定文件输入：把 JSON 粘贴存成 `/tmp/raw.json`，然后：

   ```bash
   uv run tweval import-cookies --input /tmp/raw.json
   ```

5. 跑一下 `uv run tweval doctor` 验证一下，看到 "Cookie file readable (N cookies)" 就 OK 了。

### 第 6 步：自检

```bash
uv run tweval doctor
```

应该看到一串 ✓。如果有 ✗，按提示修。

✅ **环境就 OK 了。**

---

## 日常使用

> ⚠️ **每次新开终端都要先 cd 进项目目录**，否则 `uv run` 找不到这个项目的环境，会报 `Failed to spawn: tweval`。
>
> ```bash
> cd ~/twitter-kol-eva
> ```
>
> （路径取决于你 clone 在哪——如果你忘了，可以直接打 `cd` 然后回车，再 `find ~ -name twitter-kol-eva -type d 2>/dev/null` 找。）

### 最简单的用法

```bash
uv run tweval evaluate elonmusk --price 500
```

意思是："评估 @elonmusk 这个账号，按一条赞助推文 500 美元的报价。"

会看到一张表，大概长这样（数字是示意）：

```
╭──────────────────────── KOL Snapshot ──────────────────────────╮
│      Account  @elonmusk  (https://x.com/elonmusk)              │
│    Followers  220.30M                                          │
│ Quoted price  USD 500.00                                       │
│  Sample size  20 recent original tweets                        │
│ Avg per tweet views 5.20M | likes 42K | comments 3.1K | ...    │
╰────────────────────────────────────────────────────────────────╯

                       The 6 Metrics
┃ Metric                      ┃        Value ┃ Formula                              ┃
│ ER (粉丝互动率)              │        0.02% │ (likes+comments+shares) / followers │
│ View ER (曝光互动率)         │        0.95% │ (likes+comments+shares) / avg_views │
│ C/L Ratio (评论深度比)       │        7.38% │ comments / likes                    │
│ Reach Rate (粉丝触达率)      │        2.36% │ avg_views / followers               │
│ Stability (数据稳定性)       │        4.12x │ max_views / min_views               │
│ CPM (千次曝光成本)           │     USD 0.10 │ price / (avg_views/1000)            │
```

### 加点参数

```bash
# 多采样几条
uv run tweval evaluate elonmusk --price 500 --recent-n 30

# 用人民币标价（注意：只是标签，不会做汇率换算）
uv run tweval evaluate elonmusk --price 3500 --currency CNY

# 同时把完整 JSON 报告存到文件
uv run tweval evaluate elonmusk --price 500 --json out/elon.json

# 想看着浏览器实际在干嘛（debug 用）
uv run tweval evaluate elonmusk --price 500 --headed

# 直接用一个 URL 当输入也行
uv run tweval evaluate https://x.com/sama --price 800
```

完整参数表：
```bash
uv run tweval evaluate --help
```

---

## 怎么读懂结果

### 单看一个号意义不大，要横向比

CPM 在游戏行业可能是 5 美元，在科技 B2B 可能是 50 美元——**一个数字孤立看没有结论**。建议：

1. 把同类的 5–10 个 KOL 都跑一遍，存成 JSON
2. 把所有人的 6 个指标摆在一起，按 CPM 升序排
3. 删掉 Stability > 10x 或者 C/L Ratio < 1% 的（数据不可信或买赞嫌疑）
4. 剩下的里面再看 ER 和 View ER

### 几个常见的"危险信号"

| 现象 | 可能的问题 |
|------|-----------|
| C/L Ratio < 1% | 评论太少相对于点赞——典型买赞模式 |
| ER < 0.1% 但粉丝很多 | 僵尸粉占比高，粉丝数虚高 |
| Stability > 10x | 数据极不稳定，可能就出过一两条爆款，平时哑火 |
| Reach Rate < 1% | 算法不推，或者有 shadow ban |
| CPM 比同类高 3 倍 | 报价虚高 |

---

## 出问题怎么办

### "Failed to spawn: tweval" / "No such file or directory (os error 2)"
最常见的失误之一：你新开了终端但没有先 cd 进项目目录。`uv run` 是相对于当前目录找项目环境的。先：
```bash
cd ~/twitter-kol-eva
```
然后再跑你的 `uv run tweval ...` 命令。如果忘了 clone 到哪，可以：
```bash
find ~ -name twitter-kol-eva -type d 2>/dev/null
```

### "uv: command not found"
你装了 uv 但终端找不到。解决：**关掉终端再开一个新的**，或者重启电脑。

### `tweval login` 时浏览器弹不出来
你可能没装 Chromium。再跑一次：
```bash
uv run playwright install chromium
```

### `tweval login` 时输完用户名又被弹回输入页（或被 Google 拦着）
Twitter / Google 检测到自动化浏览器了。**走路径 B（手动导出）**——见上面"第 5 步"的"路径 B"，用 Cookie-Editor 扩展从你日常 Chrome 里导出 cookie，然后 `uv run tweval import-cookies`。这条路 100% 能成。

### 跑 `evaluate` 时报 `Auth problem: Twitter is asking us to log in`
你的 cookie 过期了（一般几周一次）。重新导出：
```bash
uv run tweval login
```

### 跑 `evaluate` 时收集到 0 条推文
- 检查账号名拼对没
- 用 `--headed` 跑一次，肉眼看浏览器在干嘛——是不是被卡在 "Something went wrong" 之类的页面
- 这个账号可能确实没原创推文（只转发别人的）——脚本会跳过纯转推

### "Followers count is 0 or unknown"
通常是 Twitter 改了页面结构，followers 选择器找不到了。开 issue 或自己改 `scraper.py` 里的 `_read_followers`。

### Stability 是 0
说明所有样本的 view 数都没抓到——基本确定是没登录或者 cookie 过期。重新 `tweval login`。

### CPM 算出来很离谱
检查报价单位有没有搞错：你输入 `--price 500` 程序按 500 算。**不会自动汇率换算**——`--currency CNY` 只是改个标签。

---

## 项目结构

```
twitter-kol-eva/
├── README.md                  ← 你正在看的这个
├── pyproject.toml             ← Python 项目定义（依赖版本等）
├── .env.example               ← 配置模板
├── .gitignore                 ← Git 忽略规则
├── twitter_kol_eva/
│   ├── cli.py                 ← 命令行入口（evaluate / login / doctor）
│   ├── url_utils.py           ← 解析 @handle 和 URL
│   ├── scraper.py             ← Playwright 抓推文逻辑
│   ├── calculator.py          ← 6 个指标的公式
│   ├── report.py              ← 终端表格 + JSON 输出
│   └── models.py              ← 数据结构定义
└── tests/
    ├── test_calculator.py     ← 公式单元测试
    └── test_url_utils.py      ← URL 解析单元测试
```

跑测试：
```bash
uv run pytest
```

---

## 安全 & 合规

- **cookie 文件 = 登录密码**。`.gitignore` 已经把常见命名拦掉了，但不要主动 `git add` 它。
- 这个工具用浏览器自动化抓公开页面。Twitter / X 的 ToS 是否允许抓取**取决于你怎么用**。商业用途请自己判断风险，作者不承担责任。
- 抓取频率内置了 1.5–3 秒的随机延时；不要把 `recent_n` 设很大、连续跑很多账号——容易触发风控甚至封号。

---

## 后续想加的

- [ ] 批量评估：一个 CSV 进去，一个 CSV 出来
- [ ] Notion 输出（参考 [YoriHan/kol-eval](https://github.com/YoriHan/kol-eval)）
- [ ] 综合评分 + 谈判建议
- [ ] YouTube 支持

有需求随时开 issue。

---

## License

MIT
