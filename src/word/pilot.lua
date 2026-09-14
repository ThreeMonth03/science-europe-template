-- Keep standalone labels with the next paragraph without changing their words.
-- This output-specific rule is independent of the English/Chinese translation.
function Meta(meta)
  -- The shared frontmatter already provides a title; avoid Pandoc's extra cover.
  meta.title = nil
  return meta
end

function Table(tbl)
  if tbl.classes:includes("resource-table") then
    tbl.colspecs = {{pandoc.AlignLeft, 0.57}, {pandoc.AlignLeft, 0.17}, {pandoc.AlignLeft, 0.26}}
  elseif tbl.classes:includes("project-details") or tbl.classes:includes("dataset-version") then
    tbl.colspecs = {{pandoc.AlignLeft, 0.22}, {pandoc.AlignLeft, 0.78}}
  end
  return tbl
end

function Para(paragraph)
  if #paragraph.content == 1 and paragraph.content[1].t == "Strong" then
    return pandoc.Div({paragraph}, pandoc.Attr("", {}, {["custom-style"] = "Pilot Label"}))
  end
end

-- Only an explicitly marked ISO-shaped date gets non-breaking hyphens in Word.
-- Leave file names, URLs and authored prose unchanged.
function Span(span)
  if span.classes:includes("repository-label") then
    -- Own label emphasis here: translation handles words, not decorative markup.
    span.content = {pandoc.Strong(span.content)}
    return span
  end
  if span.classes:includes("date-value") then
    local value = pandoc.utils.stringify(span)
    if value:match("^%d%d%d%d%-%d%d%-%d%d$") then
      span.content = {pandoc.Str(value:gsub("-", utf8.char(0x2011)))}
      return span
    end
  end
end

-- Keep genuinely short lists together, without making long free answers unbreakable.
function BulletList(list)
  if #list.content > 1 and #list.content <= 3 and #pandoc.utils.stringify(list) <= 600 then
    for index = 1, #list.content - 1 do
      local item = list.content[index]
      local last = item[#item]
      if last.t == "Para" or last.t == "Plain" then
        item[#item] = pandoc.Div({pandoc.Para(last.content)}, pandoc.Attr("", {}, {["custom-style"] = "Pilot List Lead"}))
      end
    end
    return list
  end
end

-- Only template-owned policy sentences may be joined; never flatten free answers.
function Div(div)
  if div.classes:includes("identifier-heading") then
    -- Q13 only: combine the existing distribution number and repository type.
    -- Para may already wrap all-Strong labels. Reject unexpected/free blocks;
    -- do not turn this into a generic label/paragraph-flattening operation.
    if #div.content > 2 or utf8.len(pandoc.utils.stringify(div)) > 240 then return div end
    local inlines = pandoc.List()
    for _, block in ipairs(div.content) do
      if block.t == "Div" and block.attributes["custom-style"] == "Pilot Label" and #block.content == 1 then
        block = block.content[1]
      end
      if block.t ~= "Para" and block.t ~= "Plain" then return div end
      if #block.content > 0 then
        if #block.content ~= 1 or block.content[1].t ~= "Strong" then return div end
        if #inlines > 0 then inlines:insert(pandoc.Space()) end
        inlines:extend(block.content)
      end
    end
    if #inlines > 0 then
      div.content = {pandoc.Para(inlines)}
      div.attributes["custom-style"] = "Pilot Label"
    end
    return div
  end
  if div.classes:includes("repository-destinations") then
    -- Recheck the HTML hint against the actual AST, counting Unicode characters.
    -- BulletList may already have styled short items; normalize those wrappers
    -- locally so an authored/long Q11 list cannot inherit that generic keep chain.
    local list, simple = nil, true
    for _, block in ipairs(div.content) do
      if block.t == "BulletList" and list == nil then list = block
      elseif not (block.t == "Div" and block.classes:includes("answer-lead")) then simple = false end
    end
    if list == nil then return div end
    for _, item in ipairs(list.content) do
      for index, block in ipairs(item) do
        if block.t == "Div" and block.attributes["custom-style"] == "Pilot List Lead" and #block.content == 1 then
          item[index] = block.content[1]
        end
      end
      if #item ~= 1 or (item[1].t ~= "Para" and item[1].t ~= "Plain") then simple = false end
    end
    if div.classes:includes("short-repository-list") and simple and #list.content <= 3 and
       utf8.len(pandoc.utils.stringify(list)) <= 900 then
      for index, item in ipairs(list.content) do
        local style = index < #list.content and "Pilot Repository Lead" or "Pilot Repository Item"
        item[1] = pandoc.Div({pandoc.Para(item[1].content)}, pandoc.Attr("", {}, {["custom-style"] = style}))
      end
    end
    return div
  end
  if div.classes:includes("distribution-reading-unit") then
    local flattened = pandoc.List()
    local function collect(blocks, owned)
      for _, block in ipairs(blocks) do
        if block.t == "Div" and (
          block.classes:includes("joined-policy") or
          (owned and (block.classes:includes("answer-lead") or block.classes:includes("license-summary"))) or
          (block.attributes["data-fact-id"] == "distribution-access" and
            (block.attributes["data-status"] == "complete" or block.attributes["data-status"] == "explicit-no"))
        ) then
          collect(block.content, true)
        else flattened:insert(block) end
      end
    end
    collect(div.content, false)
    local blocks, inlines = pandoc.List(), pandoc.List()
    local function flush()
      if #inlines > 0 then blocks:insert(pandoc.Para(inlines)); inlines = pandoc.List() end
    end
    for _, block in ipairs(flattened) do
      if block.t == "Para" then
        if #inlines > 0 then inlines:insert(pandoc.Space()) end
        inlines:extend(block.content)
      else flush(); blocks:insert(block) end
    end
    flush(); div.content = blocks
    -- Continue into the existing bounded keep-with-next rule, if applicable.
  end
  if div.classes:includes("short-table-unit") then
    -- Recheck AST bounds independently of the HTML hint. Keep every cell in
    -- non-final rows with the next row; the final row must NOT keep Q2 with it.
    local rows, paragraphs, simple, tables = {}, {}, true, 0
    for index, block in ipairs(div.content) do
      if block.t == "Para" or block.t == "Plain" then
        if tables > 0 then simple = false end
        table.insert(paragraphs, index)
      elseif block.t == "Table" then
        tables = tables + 1
        if #block.colspecs > 4 or #block.caption.long > 0 then simple = false end
        for _, row in ipairs(block.head.rows) do table.insert(rows, row) end
        for _, body in ipairs(block.bodies) do
          for _, row in ipairs(body.head) do table.insert(rows, row) end
          for _, row in ipairs(body.body) do table.insert(rows, row) end
        end
        for _, row in ipairs(block.foot.rows) do table.insert(rows, row) end
      else simple = false end
    end
    if tables ~= 1 or #rows < 2 or #rows > 4 or utf8.len(pandoc.utils.stringify(div)) > 500 then simple = false end
    for _, row in ipairs(rows) do
      if #row.cells > 4 then simple = false end
      for _, cell in ipairs(row.cells) do
        if cell.row_span ~= 1 or cell.col_span ~= 1 or #cell.contents ~= 1 or utf8.len(pandoc.utils.stringify(cell.contents)) > 80 then simple = false end
        for _, block in ipairs(cell.contents) do
          if block.t ~= "Para" and block.t ~= "Plain" then simple = false end
        end
      end
    end
    if simple then
      for _, index in ipairs(paragraphs) do
        div.content[index] = pandoc.Div({pandoc.Para(div.content[index].content)}, pandoc.Attr("", {}, {["custom-style"] = "Pilot Table Lead"}))
      end
      for index = 1, #rows - 1 do
        for _, cell in ipairs(rows[index].cells) do
          cell.contents = {pandoc.Div({pandoc.Para(cell.contents[1].content)}, pandoc.Attr("", {}, {["custom-style"] = "Pilot Table Lead"}))}
        end
      end
    end
    return div
  end
  if div.classes:includes("short-reading-unit") and utf8.len(pandoc.utils.stringify(div)) <= 500 then
    -- Only bounded owned prose. Preserve nested divs and inline content, and
    -- reject free-answer/list/table units rather than making them unbreakable.
    local paragraphs, simple = {}, true
    local function scan(blocks)
      for index, block in ipairs(blocks) do
        if block.t == "Para" or block.t == "Plain" then
          table.insert(paragraphs, {blocks = blocks, index = index, block = block})
        elseif block.t == "Div" and not block.classes:includes("answer-detail") then
          scan(block.content)
        elseif block.t ~= "Header" then
          simple = false
        end
      end
    end
    scan(div.content)
    if simple then
      for index = 1, #paragraphs - 1 do
        local item = paragraphs[index]
        item.blocks[item.index] = pandoc.Div({pandoc.Para(item.block.content)}, pandoc.Attr("", {}, {["custom-style"] = "Pilot Lead"}))
      end
    end
    return div
  end
  if div.classes:includes("distribution-reading-unit") then
    -- Longer/restricted units skip the short-unit rule but still need to return
    -- their bounded paragraph edits; otherwise Pandoc discards this mutation.
    return div
  end
  if div.classes:includes("answer-lead") then
    div.attributes["custom-style"] = "Pilot Lead"
    return div
  end
  if (div.classes:includes("answer-detail") or div.classes:includes("answer")) and #div.content > 1 and div.content[1].t == "Para" then
    div.content[1] = pandoc.Div({div.content[1]}, pandoc.Attr("", {}, {["custom-style"] = "Pilot Lead"}))
    return div
  end
  if div.identifier == "dmp-content" and FORMAT == "docx" then
    div.content:insert(1, pandoc.RawBlock("openxml", '<w:p><w:r><w:br w:type="page"/></w:r></w:p>'))
    return div
  end
  if div.classes:includes("dataset-policy") then
    local blocks, inlines = pandoc.List(), pandoc.List()
    local function flush()
      if #inlines > 0 then
        blocks:insert(pandoc.Para(inlines))
        inlines = pandoc.List()
      end
    end
    for _, block in ipairs(div.content) do
      if block.t == "Para" then
        if #inlines > 0 then inlines:insert(pandoc.Space()) end
        inlines:extend(block.content)
      else
        flush()
        blocks:insert(block)
      end
    end
    flush()
    div.content = blocks
    return div
  end
end
