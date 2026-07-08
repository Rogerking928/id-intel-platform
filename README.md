# 🦠 Global AMR & Infectious Disease Intelligence Platform

一個以 **AI 為核心**、每天自動收集並分析全球感染症與抗藥性資訊的平台。
它不是新聞聚合器，而是會**自動萃取結構化資訊、分類、建立知識關聯、產生趨勢分析與週報**，
並且每一筆資料都保留原文與模型輸出，可直接支援後續研究與論文（Paper 1：LLM AMR 萃取 benchmark）。

> 完全使用免費、開源工具。不需要信用卡。沒有 AI 金鑰也能完整運作（離線 rule-based 萃取）。

---

## 這個平台會做什麼（對應你的需求）

| 你的需求 | 對應功能 | 檔案 |
|---|---|---|
| 每天自動收集 WHO / CDC / ECDC / PubMed / ClinicalTrials / GLASS | 6 個 collector | `collectors/` |
| AI 自動萃取（病原體、國家、抗生素、抗藥基因、研究類型、摘要…） | rule-based（永遠可用）+ Gemini（可選） | `extract/` |
| AI 自動分類成 8 類事件 | 分類器 | `extract/rule_based.py` |
| 知識關聯（Pathogen → Country → Gene → Antibiotic …） | entities + relations 表 | `db.py`, 知識圖頁面 |
| AI 趨勢分析（最近討論最多／上升最快／哪些國家…） | 由 LLM 或模板產生 | `analysis/trends.py` |
| 網站 Dashboard（Today / Trend / Latest …） | Streamlit 多頁面 | `app/` |
| 搜尋（病原體／國家／抗生素／基因／日期／事件類型） | 搜尋頁 | `app/pages/1_*.py` |
| AI 週報（可輸出 Markdown / PDF） | 週報產生器 | `analysis/weekly_report.py` |

---

## 一、安裝（只需做一次）

你需要先安裝 **Python 3.10 以上**。以下擇一：

### 方法 A —— Windows（最簡單，建議初學者用這個）

打開「PowerShell」，逐行貼上：

```powershell
cd C:\Users\roger\Desktop\id-intel-platform
py -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

### 方法 B —— WSL / Linux

```bash
cd /mnt/c/Users/roger/Desktop/id-intel-platform
# 若 venv 可用：
python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt
# 若出現 "ensurepip is not available"，改用這一行即可：
pip install --user --break-system-packages -r requirements.txt
```

---

## 二、每天更新資料（收集 + AI 萃取）

```bash
python run_daily.py            # 收集所有來源、AI 萃取、建立知識圖
python run_daily.py --report   # 同上，並且產生本週週報
```

第一次執行會抓比較多歷史資料（尤其 CDC），之後每天只會新增新資料（自動去重）。

想控制抓取量（跑快一點）可以加環境變數，例如：
```bash
PUBMED_MAX_PER_QUERY=10 WHO_MAX_ITEMS=15 python run_daily.py
```

---

## 三、打開網站 Dashboard

```bash
streamlit run app/Home.py
```

瀏覽器會自動打開 `http://localhost:8501`。左側 sidebar 有五個頁面：

- **Home** — Today's highlights、30 天趨勢圖、Latest publications / trials / guidelines
- **🔎 Search** — 依病原體／國家／抗生素／基因／事件類型／日期查詢，可下載 CSV
- **📈 Trends** — AI 趨勢分析、上升最快、時間趨勢圖
- **🕸️ Knowledge Graph** — 選一個病原體，看它連到的國家／基因／抗生素／疾病
- **📰 Weekly Report** — 一鍵產生週報，下載 Markdown 或 HTML（用瀏覽器列印成 PDF）

---

## 四、AI 功能（Gemini）—— 已啟用

平台**永遠**會跑免費、離線的規則式萃取。若 `.env` 裡有 `GEMINI_API_KEY`，就會**額外**跑一次 Gemini
萃取，並把它設為 search / 知識圖 / 趨勢分析採用的版本。

- 申請金鑰：<https://aistudio.google.com/apikey>（Google 帳號登入，免信用卡）。點 **Create API key**，
  複製那把金鑰（新版金鑰是 `AQ.` 開頭，舊版是 `AIza` 開頭，兩種都可以）。
- 把金鑰貼進 `.env`（本專案已內建 `.env` 自動載入，**不需要**再打 `source .env`）：
  ```
  GEMINI_API_KEY=你的金鑰
  GEMINI_MODEL=gemini-2.5-flash
  ```
- 然後照常 `python run_daily.py` 就會自動開啟 AI。

**免費額度節流（重要）**：免費 tier 每分鐘請求數有限，所以每次執行預設只對 `GEMINI_MAX_PER_RUN=50`
篇做 LLM 萃取，且每次呼叫間隔 `GEMINI_MIN_INTERVAL=4.5` 秒。要一次跑多一點就調高上限，例如：
```bash
GEMINI_MAX_PER_RUN=200 python run_daily.py
```
每天排程執行就會慢慢把整個資料庫補完。每篇資料會**同時**保留規則式與 Gemini 兩種萃取結果 ——
這正是 Paper 1 要比較的模型資料（實測 Gemini 能抓到 KPC-234、NDM-1、質體型別等規則式漏掉的細節）。

---

## 五、讓它每天自動跑（排程）

**WSL / Linux（cron）** — 每天早上 7 點：
```
0 7 * * * cd /mnt/c/Users/roger/Desktop/id-intel-platform && /usr/bin/python3 run_daily.py --report >> data/cron.log 2>&1
```
用 `crontab -e` 貼上。

**Windows（工作排程器 Task Scheduler）**：建立一個每日任務，
程式填 `py`，引數填 `run_daily.py --report`，開始位置填專案資料夾。

---

## 專案結構

```
id-intel-platform/
├─ run_daily.py          # ★ 一鍵：收集→萃取→分類→知識圖（可排程）
├─ config.py             # 所有設定（要追蹤的病原體、查詢字串、抓取量…）
├─ db.py                 # SQLite 資料庫（documents / extractions / entities / relations / annotations）
├─ requirements.txt
├─ .env.example          # 可選金鑰設定範本
├─ collectors/           # 六個資料來源
│  ├─ pubmed.py  clinicaltrials.py  who.py  rss.py(CDC/ECDC)  glass.py
├─ extract/              # AI 萃取
│  ├─ dictionaries.py    # 受控詞彙（病原體/抗生素/抗藥基因/國家）＝ Paper 1 codebook
│  ├─ rule_based.py      # 規則式萃取（永遠可用，也是論文 baseline）
│  ├─ llm.py             # Gemini 萃取（可選）
│  └─ pipeline.py        # 萃取流程 + 知識圖建立
├─ analysis/
│  ├─ trends.py          # 趨勢分析（含 AI 敘述）
│  └─ weekly_report.py   # 週報（Markdown + HTML）
├─ app/                  # Streamlit 網站
│  ├─ Home.py  common.py  pages/…
├─ data/                 # SQLite 檔（自動建立）
└─ reports/              # 產出的週報
```

---

## 這個平台如何支援你的論文（Paper 1）

每一筆資料都保留：**原文 raw_text + 來源 + URL + 抓取時間 + 模型名稱/版本/prompt 版本/原始輸出**。
`annotations` 資料表用來存放你（與第二位標註者）的 gold-standard 標註，之後可計算
per-field F1、macro-F1、κ，比較規則式 vs 免費 LLM 在 CRE/VRE/MRSA 萃取上的表現。

> ⚠️ 為避免 data leakage：先凍結 `extract/dictionaries.py`（codebook）與 schema，
> **再**去看模型輸出與做標註。

---

## 之後可以擴充（不是第一版）

Neo4j 真正的知識圖、AI 預測趨勢/研究熱點、各國 Guideline 差異比較、
全球抗藥性互動地圖、對外提供研究者 API、系統性回顧自動整理。
目前架構（collector → extractor → entities/relations → analysis → app）已經預留這些接口。
