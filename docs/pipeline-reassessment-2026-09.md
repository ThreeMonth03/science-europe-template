# PDF／Word 成品導向的流程重新評估

日期：2026-09-11。以下保留實作前的評估紀錄；其中版本及「尚未實作」是當時狀態。
後續已完成客製 profile 接點、翻譯遷移及英中三格式實際渲染，最新結果請見
新 repo `science-europe-template-zhtw/docs/pilot-results.md`，不可把下列舊診斷
當成目前驗收狀態。

## 建議決策

繼續維護一個從官方 Science Europe 衍生的客製英文 Jinja 模板，透過既有
translation tree 產生中文。英文源碼需要具備完整句子、明確的答案狀態與
有效的 HTML 結構；中文翻譯可使用自然語序；PDF 與 Word 分別維護輸出樣式。
兩個語言共享資料選取與分支語意，並分別驗收文字與成品。

官方模板是程式碼來源及更新參考；內容完整性的依據是 Science Europe 指南及
其 DMP evaluation rubric。指南允許因組織、學科需求調整，並要求涵蓋六項核心
內容。對照題目標題或確認欄位非空，均不足以證明實質內容完整。

來源：[Science Europe 2021 extended guide](https://scienceeurope.org/media/4brkxxe5/se_rdm_practical_guide_extended_final.pdf)。

## 本次檢查與可重現結果

檢查的是本機下列版本，未重新查驗線上 DSW 專案或最新 GitHub release：

| 元件 | 本機版本／位置 |
| --- | --- |
| 客製英文 | 本 repo 的 `experiment/completeness-contract`，程式碼提交 `4a232c3` |
| 官方基底 | `v1.30.1`，`22d60aae4b63ee677477ac0c73097807284aaf9f` |
| 轉換工具 | sibling `dsw-document-template-tool`，`d6814d8` |
| 中文控制設定 | sibling `science-europe-template-zh_Hant` 的 `operations`，`b00ffff` |
| 中文後期 QA 工作樹 | `science-europe-template-zh_Hant-v1.30.1-qa-round8`，`13fd8af` |

在 `/tmp/dsw-template-assessment.0Ht1Wd/` 分別執行官方與客製版的 expand、export、audit：

| 檢查 | 官方 1.30.1 | 客製英文實驗版 0.1.0 |
| --- | --- | --- |
| expand / export | 成功 | 成功 |
| transform profile | `science-europe` | `generic` |
| 專用改寫紀錄位置 | 17 筆 | 0 筆 |
| translation tree audit | 通過 | 失敗：12 項句子片段、1 項不明確 placeholder |

17 是 explain 報告的改寫群組／檔案位置紀錄數，並非總共只有 17 個問題或句子。
客製版仍有執行通用 expansion；0 指沒有套用官方 Science Europe 專用改寫。

工具環境原本缺少已宣告的 `defusedxml` 相依套件。本次只把 `defusedxml==0.7.1`
安裝到暫存目錄，以 `PYTHONPATH` 載入；未修改共用虛擬環境或工具程式碼。

重現命令形式（output 請使用新的暫存目錄）：

```sh
dsw-template-transform expand --source SOURCE_TEMPLATE --output EXPANDED
dsw-template-transform explain --source EXPANDED
dsw-template-tree export --source EXPANDED --output TRANSLATION_TREE
dsw-template-tree audit --source EXPANDED --tree TRANSLATION_TREE
```

具體發現：

1. 工具 `_template_transform/science_europe.py` 的 profile 選取限定
   `organization_id == "dsw"` 且 `template_id == "science-europe"`。
   `template_transform.py` 也以此條件決定是否套用 zh-Hant 字型、語言及 KM 等
   localization patches。客製 ID 目前無法直接取得這些處理。
2. 客製版失敗片段包含 `This data are`、`, legally based on`、`available via:`。
   因此只檢查 expand/export 成功會漏掉實際不可翻譯的輸入。
3. 新增的 `macros.missing("SE-1a", "new-data", "...")` 有抽取到說明文字，
   但也把 `SE-1a` 等機器識別碼當成可翻譯字串，部分單位混合 ID、fact ID 與說明。
   不能認定目前缺漏 macro 已具備安全的翻譯介面。
4. 工具已明文允許 placeholder 重排，並維護 Jinja、HTML 與 `data-*` 屬性的
   結構稽核。這些既有機制應保留；但 ID 被當作 macro 字串抽取是另一個接點問題。
5. upstream `v1.30.0..v1.30.1` 修改 15 個檔案、67 行新增／62 行刪除；除
   `dot` 改為 `markdown`，也有 reply path 與變數拼字修正。patch 版號不代表
   只需調整版號，內容、HTML 與翻譯都可能受影響。
6. 既有 QA workflow 的預覽格式是 PDF；文件回歸 base config 指定 HTML，
   翻譯套件回歸使用 `render_success`。它們沒有構成中英文 PDF／DOCX 的完整
   成品驗收。分支覆蓋率高也不等於語意正確或涵蓋所有條件組合。

本次查看了兩份本機 1.30.1 PDF 的第 5 頁影像，並讀取範例文字；可見資料集
名稱落在頁末而說明接到下一頁，以及重複段落與大量逐層列點。
來源為 `dsw-template-quality-review/v1.30.1/` 及工具
`outputs/public-branch-render/dsw-science-europe/v1.30.1/zh-Hant/`。
這些是既有產物；其 metadata 沒有完整 source commit，不能據此宣稱最新 QA
分支或線上版本仍有全部相同問題。本次未重新產生或驗收 DOCX。

## 建議的責任與串接

```text
官方 release 與變更差異
          ↓ 審查、選擇性納入
客製英文 Jinja release ───────────────────→ 英文套件
          ↓ 明確指定來源 commit、轉換設定
既有 expand → translation tree → 中文編修 → sync
          ↓
中文套件
          ↓
同一組專案事實 → 英文／中文各自的 PDF 與 DOCX → 發布驗收
```

- `science-europe-template`：Science Europe 對照、reply/KM 對應、答案狀態、
  英文完整句子、共用文件結構，以及版本化的輸出樣式資產。
- `dsw-document-template-tool`：通用抽取、保護變數與結構、精確翻譯沿用、
  可明確設定的 template family 與 locale 處理、建置及成品測試。
- 新 repo `science-europe-template-zhtw`：審閱過的中文翻譯、術語與文體規則、
  客製英文來源的精確版本引用，以及中文套件發布。

原有 `science-europe-template-zh_Hant` 繼續對應官方來源，本次未修改。

這需要調整既有 infra 的來源 discovery、scaffold artifact 身分與 profile 選取；
修改 `upstream_repository` 一項設定不足以證明接好。應以明確設定選取客製來源
及支援的轉換規則，不能靠冒用官方 template ID 取得處理。
重寫後的客製模板也不應無條件套用全部官方舊字串修補。

## 四個品質問題的處理方式

### 英文內容與 Jinja 條件分支

以每項要求、每個資料集實例為單位，區分：已提供、部分提供、未提供、
明確否定、明確不適用。缺少父題時不能默認 No；子題缺漏不能讓已填內容消失。
若存在矛盾或不可達的舊回覆，應有明確處理規則，不能任意挑選較好看的說法。

保留必要的問題及有用的事實；缺漏提示說明「缺什麼」，不以空話補足答案。
若要標示文件已完成，另以內容檢查與人工審閱判定；仍需提供可清楚辨識缺漏的草稿。
KM 若未蒐集必要資訊，須完成全 KM 對照後才決定增題，不能從單一 Jinja 檔案未
引用某欄位便推斷整個 KM 沒問。

先在每題內整理資料讀取、狀態判斷與輸出區域；只有實際共用的邏輯才抽 macro。
macro 的機器 ID 與可翻譯文字須有可測的邊界。沒有必要先建一套大型新中介格式。

### 中英語序與自由文字

翻譯單位使用完整句子或自足的內容區塊；同一語意分支內允許 placeholder 重排。
例如 `Access to {dataset} will be granted to {users} after {date}.` 可依確切時間
語意譯成「{date}之後，{users}可存取{dataset}。」數量清單及可選子句應有明確
的 0、1、多筆呈現規則，避免將 `and` 或逗點碎片交給譯者拼接。

自由文字不能假定一定是英文動詞片語。原有 `in order to {{ answer|markdown }}`
可能接到完整中文句子、多段文字或清單，語法與 HTML 都會出問題。較穩定的
寫法是完整引導句／標籤搭配獨立說明區塊，例如「資料使用目的」後接使用者回答。
行內純文字與可輸出段落、表格、清單的 Markdown 欄位應分開處理，避免 `<p>`
內再放 `<p>` 或 `<ul>`。

翻譯模板只會翻譯模板擁有的文字。使用者填寫的自由文字會保留原文；若要求
同一份 project 的整份報告皆為雙語，回答本身仍需有經審閱的雙語內容。

### 中文語氣

以臺灣研究計畫／資料管理文件的書面語編修：適當使用「本計畫」，避免反覆
「我們將會」和英語被動句。使用短段落、必要的標籤與清單；不要把每題都變成
表格，也不要把清單強行串成長句。延續既有 glossary，再按語境處理同詞異義。

編修不能把「計畫」「可能」「尚未決定」提升成「已確保」，也不能改變否定、
責任人、限制、期限、金額、URL 或識別碼。必須在具體分支的渲染結果中審閱，
不能只看單獨 translation.md 就認定文氣自然。

### 排版

現有 `template.json` 設定 PDF 經 HTML → WeasyPrint，Word 經另一個 HTML
入口 → Pandoc + `src/word/reference.docx`。共用 HTML 結構仍可保留；但 Word
的字型、標題層級、間距、分頁、表格等應藉由 reference document／轉換樣式
明確設定，不能假定 PDF CSS 會完整搬進 DOCX。

樣式資產建議由英文客製 repo 版本化，讓一個設計版本包含共用、英文與中文的
PDF 樣式及各語言 DOCX reference。建置時明確選取並記錄 checksum。現有工具
禁止 translated output 任意變更 static assets，應在受稽核的 locale 建置階段
選取資產，不要關閉結構稽核或事後手改產物。

優先處理：標題／資料集名稱與首段同頁、段落及列表間距、長 URL 斷行、
表格跨頁與重複表頭、中文字型及字重、沒有資料的版本紀錄頁、封面與前置頁的
必要性。超長資料集區塊仍需允許分頁，整塊設為不可分頁會造成大片空白。

DOCX 須兼顧可編輯性與 Word 開啟效果；LibreOffice 轉 PDF 可作自動回歸代理，
不能視為 Microsoft Word 中呈現完全一致的證明。

## 官方升級與分支

保留官方 Git 歷史及精確基底；客製英文走自己的 release，中文以明確引用的
英文 commit 建置。官方 1.30.1、客製英文 0.2.0、中文修訂 0.2.1 可以並存，
版本關係由 manifest 說明，無須假裝三者版號相同。這些是示例版號。

英文 `main` 建議作為客製開發主線，`upstream/main` 為官方 remote-tracking ref，
功能與升級使用短期分支。中文現有 `operations` + `sync/v*` 的模式可以沿用，
但自動化目前以官方版本為中心；支援客製來源需先完成 artifact、版本選取與
profile 接點的驗證，舊版翻譯分支不可直接換成不相干的英文來源。

句型與輸出結構的實質重構可能會使多個 question Jinja 與官方明顯分歧。
目錄搬家只能減少行衝突，不能消除語意維護工作。對仍近似官方的檔案可評估
普通 merge；對已自行設計的題目與 DOCX 樣式，按變更目的選擇性移植。
官方更新若修正欄位路徑，通常值得納入；官方更換句型、排版或 Word reference
則需確認是否符合客製設計，不能直接覆蓋。

分別記錄：原始基底、已審查至哪個官方版本、哪些變更採用／不採用／待處理。
選擇性移植後不能只把 baseline 更新成新版本，造成已全面整合的錯覺。
每個正式產物記錄英文 commit、中文 commit、工具 commit、KM、DSW/worker 與
樣式版本。發布套件應具備可重現來源，單純沿用可覆寫的 scaffold 名稱不足夠。

## 下一個實驗與驗收門檻

先完成 Q1、Q5、Q15 的端到端切片，再將方法擴展到其餘 12 題。Q1 測資料重用、
複雜分支與語序；Q5 測空白／否定／部分回覆；Q15 測資源清單、金額與重複實例。

實驗順序：

1. 固定官方與既有中文產物作比較基準，建立共用的專案事實及預期輸出清單。
2. 補客製來源與 locale 建置接點，修復機器 ID 被抽取及不可翻譯片段。
3. 調整三題的英文邏輯、完整句子與區塊，再沿用既有流程產生中文，審閱中文文體。
4. 同一套件在受控 DSW 測試環境產生英／中 PDF、英／中 DOCX，留下實際產物。
5. 做一次 1.30.0 → 1.30.1 的升級回放，分開記錄語意、翻譯及排版需要的人工處理。
   客製實驗目前以 1.30.1 為基底；回放需獨立 checkout，不能宣稱目前分支已演練。

輸入至少包括全空、明確否定、適用但部分回覆、完整回覆、重複資料集、0／1／
多筆清單，以及長中文、多段 Markdown、表格、長 URL。分支覆蓋測試之外，加入
彼此影響的條件組合和「刪去一個必要回答」的案例，驗證只標記對應缺漏且不
刪掉無關已填事實。

驗收分成可獨立失敗的四項：

| 驗收 | 必須證明 |
| --- | --- |
| 內容 | 要求與實例都可追溯；空白不變 No；已填事實不流失；無憑空承諾 |
| 雙語 | 相同事實、狀態、數值、責任及限制；placeholder 與結構安全；無意外英文 fallback |
| 文體 | 英文通順、中文自然且術語一致；人工檢查整題和段落，而非只審字串 |
| 輸出 | 英／中 PDF、DOCX 都開啟且可用；檢查分頁、溢出、字型、列表與表格；Word 可編輯 |

語意對照可使用 requirement ID + fact ID + dataset/item ID 及狀態、值，不依賴
逐字相等。現有 data 屬性是起點，尚未涵蓋所有分支與實例；語意錯譯仍需語言
審查。成品自動比對及人工檢查都應留證據，`render_success` 不能替代這些要求。

現有英文單元測試使用簡化的 DSW filters，且 `markdown` 為直接回傳輸入；
它們不能驗證真實 Markdown HTML、worker、PDF 或 DOCX 行為。先前缺漏提示
實驗可繼續使用，但須完成上述切片才能評估為可發布的方案。
