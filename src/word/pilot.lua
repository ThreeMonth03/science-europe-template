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
-- Q8 reference entries are a plain name Div followed by a permission paragraph.
-- The generic BulletList rule only links the end of an item to the next item;
-- it does not link a name to its own permission. Bound each pair independently.
-- No recursive walk into authored Divs/lists, no new text or paragraph merging.
local function keep_q8_reference_labels(div)
  local function width(value)
    local total = 0
    for _, code in utf8.codes(pandoc.utils.stringify(value)) do
      total = total + (code >= 0x2E80 and 2 or 1)
    end
    return total
  end
  local function plain(block)
    if block.t ~= "Para" and block.t ~= "Plain" then return false end
    for _, inline in ipairs(block.content) do
      if inline.t ~= "Str" and inline.t ~= "Space" and inline.t ~= "SoftBreak" then return false end
    end
    return width(block) > 0
  end
  for _, answer in ipairs(div.content) do
    if answer.t == "Div" and answer.classes:includes("answer") then
      for _, list in ipairs(answer.content) do
        if list.t == "BulletList" and #list.content <= 32 then
          for _, item in ipairs(list.content) do
            if #item == 2 then
              local label, permission = item[1], item[2]
              -- BulletList may have wrapped only the permission in this style.
              if permission.t == "Div" and permission.identifier == "" and #permission.classes == 0 and
                 #permission.attributes == 1 and permission.attributes["custom-style"] == "Pilot List Lead" and
                 #permission.content == 1 then permission = permission.content[1] end
              if label.t == "Div" and label.identifier == "" and #label.classes == 0 and #label.attributes == 0 and
                 #label.content == 1 and plain(label.content[1]) and width(label) <= 80 and
                 plain(permission) and width(permission) <= 320 then
                label.attributes["custom-style"] = "Pilot List Lead"
              end
            end
          end
        end
      end
    end
  end
  return div
end

-- Q15: keep a genuinely short overview with its small budget, without a forced
-- page break. Inspect the entire unit before changing anything. Long, complex,
-- or multi-project budgets retain the original AST and pagination rules.
local function keep_short_budget_overview(div)
  local units = 0
  for _, code in utf8.codes(pandoc.utils.stringify(div)) do
    units = units + (code >= 0x2E80 and 2 or 1)
  end
  if units > 1000 then return div end
  local leading, tables, projects, paragraphs, list_items, headers = {}, 0, 0, 0, 0, 0
  local simple = true
  local function inline_ok(inlines)
    for _, item in ipairs(inlines) do
      if item.t == "Strong" or item.t == "Emph" or item.t == "Span" then
        if not inline_ok(item.content) then return false end
      elseif item.t ~= "Str" and item.t ~= "Space" and item.t ~= "SoftBreak" then
        return false
      end
    end
    return true
  end
  local scan
  scan = function(blocks, in_list, in_table, styled)
    for index, block in ipairs(blocks) do
      if block.t == "Para" or block.t == "Plain" then
        paragraphs = paragraphs + 1
        if not inline_ok(block.content) then simple = false end
        if not in_table then
          if tables > 0 then simple = false end
          if not styled then table.insert(leading, {blocks=blocks, index=index, block=block, in_list=in_list}) end
        end
      elseif block.t == "Div" then
        if block.classes:includes("project-resources") then projects = projects + 1 end
        local style = block.attributes["custom-style"]
        if style and style ~= "Pilot Lead" and style ~= "Pilot Label" and style ~= "Pilot List Lead" then simple = false end
        scan(block.content, in_list, in_table, styled or style ~= nil)
      elseif block.t == "Header" and not in_list and not in_table and tables == 0 then
        headers = headers + 1
        if (headers == 1 and block.level ~= 3) or (headers == 2 and block.level ~= 4) or not inline_ok(block.content) then simple = false end
      elseif block.t == "BulletList" and not in_list and not in_table then
        list_items = list_items + #block.content
        for _, item in ipairs(block.content) do
          if #item ~= 1 then simple = false end
          scan(item, true, false, styled)
        end
      elseif block.t == "Table" and not in_table and not in_list then
        tables = tables + 1
        if not block.classes:includes("resource-table") or #block.colspecs ~= 3 or #block.bodies ~= 1 or
           #block.head.rows ~= 1 or #block.foot.rows ~= 0 or #block.caption.long ~= 0 then
          simple = false
        else
          local body = block.bodies[1]
          if #body.head ~= 0 or #body.body < 1 or #body.body > 2 then simple = false end
          local rows = {block.head.rows[1]}
          for _, row in ipairs(body.body) do table.insert(rows, row) end
          for _, row in ipairs(rows) do
            if #row.cells ~= 3 then simple = false end
            for _, cell in ipairs(row.cells) do
              local width = 0
              for _, code in utf8.codes(pandoc.utils.stringify(cell.contents)) do width = width + (code >= 0x2E80 and 2 or 1) end
              if cell.row_span ~= 1 or cell.col_span ~= 1 or width > 200 then simple = false end
              local previous = paragraphs
              scan(cell.contents, false, true, nil)
              if paragraphs - previous > 3 then simple = false end
            end
          end
        end
      else simple = false end
    end
  end
  scan(div.content, false, false, nil)
  if not simple or tables ~= 1 or projects ~= 1 or headers ~= 2 or list_items > 3 or paragraphs > 24 then return div end
  for _, item in ipairs(leading) do
    local style = item.in_list and "Pilot List Lead" or "Pilot Lead"
    item.blocks[item.index] = pandoc.Div({pandoc.Para(item.block.content)}, pandoc.Attr("", {}, {["custom-style"] = style}))
  end
  return div
end

-- Long Q15 purposes get full-width paragraph rows and a repeating identity
-- header. Validate all rows first; unknown/nested/oversized units keep the old
-- layout. Reuse translated headers and original blocks; never synthesize prose.
local function expand_long_budget_tables(div)
  local function width(value)
    local total = 0
    for _, code in utf8.codes(pandoc.utils.stringify(value)) do total = total + (code >= 0x2E80 and 2 or 1) end
    return total
  end
  local function inline_ok(items)
    for _, item in ipairs(items) do
      if item.t == "Strong" or item.t == "Emph" or item.t == "Span" or item.t == "Link" then
        if not inline_ok(item.content) then return false end
      elseif item.t ~= "Str" and item.t ~= "Space" and item.t ~= "SoftBreak" and item.t ~= "Code" then return false end
    end
    return true
  end
  local units
  units = function(blocks, allow_list)
    local result = pandoc.List()
    for _, block in ipairs(blocks) do
      if block.t == "Para" or block.t == "Plain" then
        if width(block) > 800 or not inline_ok(block.content) then return nil end
        result:insert(block:clone())
      elseif block.t == "Div" then
        local style = block.attributes["custom-style"]
        if block.identifier ~= "" or (style and style ~= "Pilot Label" and style ~= "Pilot Lead" and style ~= "Pilot List Lead") then return nil end
        local children = units(block.content, allow_list)
        if not children then return nil end
        for _, child in ipairs(children) do
          local wrapper = block:clone(); wrapper.content = {child}; result:insert(wrapper)
        end
      elseif block.t == "BulletList" and allow_list and #block.content <= 8 and width(block) <= 800 then
        for _, item in ipairs(block.content) do
          local children = units(item, false)
          if not children or #children ~= 1 then return nil end
        end
        result:insert(block:clone())
      else return nil end
    end
    return result
  end
  local function expand(tbl)
    if not tbl.classes:includes("resource-table") or #tbl.colspecs ~= 3 or #tbl.head.rows ~= 1 or
       #tbl.bodies ~= 1 or #tbl.bodies[1].head ~= 0 or #tbl.foot.rows ~= 0 or #tbl.caption.long ~= 0 then return tbl end
    local rows = tbl.bodies[1].body
    if #rows == 0 or #rows > 32 then return tbl end
    local plans, any_long = {}, false
    for _, row in ipairs(tbl.head.rows) do
      if #row.cells ~= 3 then return tbl end
      for _, cell in ipairs(row.cells) do
        if cell.col_span ~= 1 or cell.row_span ~= 1 or width(cell.contents) > 160 or not units(cell.contents, false) then return tbl end
      end
    end
    for index, row in ipairs(rows) do
      if #row.cells ~= 3 then return tbl end
      for _, cell in ipairs(row.cells) do if cell.col_span ~= 1 or cell.row_span ~= 1 then return tbl end end
      local first = row.cells[1].contents
      if #first < 2 or width(first[1]) > 160 then return tbl end
      local title = first[1]
      if title.t == "Div" and title.attributes["custom-style"] == "Pilot Label" and #title.content == 1 then title = title.content[1] end
      if (title.t ~= "Para" and title.t ~= "Plain") or #title.content ~= 1 or title.content[1].t ~= "Strong" then return tbl end
      if not inline_ok(title.content) then return tbl end
      for col = 2, 3 do
        local metadata = units(row.cells[col].contents, false)
        if not metadata or #metadata > 3 or width(row.cells[col].contents) > (col == 2 and 80 or 160) then return tbl end
      end
      local rest = pandoc.List()
      for i = 2, #first do rest:insert(first[i]) end
      local parts = units(rest, true)
      if not parts or #parts > 160 then return tbl end
      local long = #parts >= 12
      plans[index] = {long=long, parts=parts}; any_long = any_long or long
    end
    if not any_long then return tbl end
    local output, pending = pandoc.List(), pandoc.List()
    local function flush()
      if #pending > 0 then
        local short = tbl:clone(); short.bodies[1].body = pending; output:insert(short); pending = pandoc.List()
      end
    end
    for index, row in ipairs(rows) do
      if not plans[index].long then pending:insert(row:clone())
      else
        flush()
        local expanded = tbl:clone()
        expanded.classes:insert("long-resource-table")
        -- Pandoc's DOCX table writer expects the reference style ID here.
        expanded.attributes["custom-style"] = "PilotLongBudget"
        local identity = row:clone(); identity.cells[1].contents = {row.cells[1].contents[1]:clone()}
        expanded.head.rows = {tbl.head.rows[1]:clone(), identity}
        local detail = pandoc.List()
        for _, part in ipairs(plans[index].parts) do
          local line = row:clone(); local cell = line.cells[1]
          cell.contents = {part}; cell.col_span = 3; line.cells = {cell}; detail:insert(line)
        end
        expanded.bodies[1].body = detail; output:insert(expanded)
      end
    end
    flush(); return output
  end
  return div:walk({Table=expand})
end

function Div(div)
  if div.identifier == "q-copyright-ipr" then return keep_q8_reference_labels(div) end
  if div.identifier == "q-required-resources" then div = expand_long_budget_tables(div) end
  if div.identifier == "q-required-resources" then return keep_short_budget_overview(div) end
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
