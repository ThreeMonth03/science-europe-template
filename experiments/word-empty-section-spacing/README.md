# Word 全空節間距原型

正式來源仍為 0.3.49，本實驗尚未整合或升版。只在短期
`fix/word-empty-section-spacing` 分支維護原型；檢核／提交不拆長期分支。

原型在既有 `question-spacing.lua`／`question-spacing.xml` 中，僅對可信
全空節的 Heading2 設定段前 6pt、段後 3pt。保留字級、keep-next、outline、
所有題目、答案及 Word 轉換步驟；HTML／PDF／檢核版應完全不變。
先驗證六節根結構與題目次序，再核對空題標記及空答案 AST。使用者答案內
的仿造結構不處理；未知、混合與有答案的節維持原狀。

空題標記由共用 Jinja 保守分類器生成，Lua 再查 AST；Pandoc 會丟棄空 `<p>`，
所以不能宣稱只靠 AST 能辨認所有原始 HTML。測試中的空作者段落遵循實際
分類器輸出，不偽造可信空題標記。

```sh
python experiments/word-empty-section-spacing/check.py --output outputs/word-empty-section-prototype.json
```

上述引擎檢查使用固定 digest 的公開 Pandoc worker，驗證標記、完整 DOCX XML、
未修改組件及拒絕案例；不等於逐頁排版或 Microsoft Word 驗收。
中英成品仍需經既有中文建置流程及離線原生 PDF／Word 對照。
