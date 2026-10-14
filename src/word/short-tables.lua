-- Word-only scoped Q2/Q8/Q9/Q10/Q15 authored tables and bounded version-history rows.
-- The matching enrich-docx step consumes these exact generated XML comments.
local begin_marker = "<!--DSW:SE:short-table:v1:begin-->"
local end_marker = "<!--DSW:SE:short-table:v1:end-->"

local function empty_attr(value)
  return value.identifier == "" and #value.classes == 0 and #value.attributes == 0
end

local function width(value)
  local result = 0
  for _, code in utf8.codes(pandoc.utils.stringify(value)) do
    result = result + (code >= 0x2E80 and 2 or 1)
  end
  return result
end

local function simple(inlines)
  for _, value in ipairs(inlines) do
    if value.t == "Strong" or value.t == "Emph" then
      if not simple(value.content) then return false end
    elseif value.t == "Link" then
      if not empty_attr(value) or not simple(value.content) then return false end
    elseif value.t ~= "Str" and value.t ~= "Space" and value.t ~= "SoftBreak" then
      return false
    end
  end
  return true
end

local function bounded(tbl)
  if not empty_attr(tbl) or #tbl.colspecs < 2 or #tbl.colspecs > 4 or
     #tbl.caption.long ~= 0 or tbl.caption.short ~= nil or #tbl.head.rows > 1 or
     #tbl.foot.rows ~= 0 or #tbl.bodies ~= 1 or #tbl.bodies[1].head ~= 0 or
     tbl.bodies[1].row_head_columns ~= 0 or width(tbl) > 500 then return nil end
  local rows = {}
  for _, row in ipairs(tbl.head.rows) do table.insert(rows, row) end
  for _, row in ipairs(tbl.bodies[1].body) do table.insert(rows, row) end
  if #rows < 2 or #rows > 4 then return nil end
  for _, row in ipairs(rows) do
    if not empty_attr(row) or #row.cells ~= #tbl.colspecs then return nil end
    for _, cell in ipairs(row.cells) do
      if not empty_attr(cell) or cell.row_span ~= 1 or cell.col_span ~= 1 or
         #cell.contents ~= 1 or width(cell.contents) > 80 then return nil end
      local block = cell.contents[1]
      if (block.t ~= "Plain" and block.t ~= "Para") or not simple(block.content) then return nil end
      -- Explicit line breaks, images, math, nested blocks and custom styles fail
      -- closed above. Long unbroken ASCII tokens must not force a wide column.
      for token in pandoc.utils.stringify(block):gmatch("%S+") do
        if token:match("^[%z\1-\127]+$") and #token > 40 then return nil end
      end
    end
  end
  return rows
end

local function short_authored_row(row)
  if not empty_attr(row) or #row.cells ~= 2 then return false end
  for _, cell in ipairs(row.cells) do
    if not empty_attr(cell) or cell.row_span ~= 1 or cell.col_span ~= 1 or
       #cell.contents ~= 1 or width(cell.contents) == 0 or width(cell.contents) > 80 then return false end
    local block = cell.contents[1]
    if (block.t ~= "Plain" and block.t ~= "Para") or not simple(block.content) then return false end
    for token in pandoc.utils.stringify(block):gmatch("%S+") do
      if token:match("^[%z\1-\127]+$") and #token > 40 then return false end
    end
  end
  return true
end

-- Q2 non-standard-format reasons may contain long authored tables. Keep only
-- their individually bounded two-cell body rows, not the table or surrounding
-- prose; long/complex rows must remain free to split across pages.
local function keep_authored_format_rows(div)
  for _, answer in ipairs(div.content) do
    if answer.t == "Div" and answer.identifier == "" and #answer.classes == 1 and
       answer.classes:includes("answer") and #answer.attributes == 0 then
      for _, formats in ipairs(answer.content) do
        if formats.t == "Div" and formats.identifier == "" and #formats.classes == 1 and
           formats.classes:includes("data-formats") and #formats.attributes == 0 then
          for _, record in ipairs(formats.content) do
            if record.t == "Div" and record.identifier == "" and #record.classes == 1 and
               record.classes:includes("format-description") and #record.attributes == 1 and
               record.attributes["item-id"] and record.attributes["item-id"] ~= "" then
              for _, detail in ipairs(record.content) do
                if detail.t == "Div" and detail.identifier == "" and #detail.classes == 1 and
                   detail.classes:includes("answer-detail") and #detail.attributes == 2 and
                   detail.attributes["fact-id"] == "nonstandard-reason" and detail.attributes["status"] == "complete" then
                  for _, tbl in ipairs(detail.content) do
                    if tbl.t == "Table" and empty_attr(tbl) and #tbl.colspecs == 2 and #tbl.head.rows <= 1 and
                       #tbl.foot.rows == 0 and #tbl.bodies == 1 and #tbl.bodies[1].head == 0 and
                       tbl.bodies[1].row_head_columns == 0 and #tbl.caption.long == 0 and tbl.caption.short == nil then
                      for _, row in ipairs(tbl.bodies[1].body) do
                        if short_authored_row(row) then
                          row.cells[1].contents:insert(1, pandoc.RawBlock("openxml", "<!--DSW:SE:authored-format-row:v1-->"))
                        end
                      end
                    end
                  end
                end
              end
            end
          end
        end
      end
    end
  end
  return div
end

-- Q8/Q10 authorization tables may continue, but bounded body rows must not
-- leave a blank fragment. Q8 ownership requires its exact direct fact heading;
-- other Q8 answer details and reuse lists remain outside this guard.
local function keep_authored_authorization_rows(div)
  for _, answer in ipairs(div.content) do
    if answer.t == "Div" and answer.identifier == "" and #answer.classes == 1 and
       answer.classes:includes("answer") and #answer.attributes == 0 then
      local authorization_headings = 0
      for _, block in ipairs(answer.content) do
        if block.t == "Header" and block.attributes["fact-id"] == "authorization-arrangements" then
          authorization_headings = authorization_headings + 1
        end
      end
      for index, detail in ipairs(answer.content) do
        local heading = answer.content[index - 1]
        local q8_authorization = div.identifier == "q-copyright-ipr" and authorization_headings == 1 and heading and
          heading.t == "Header" and heading.level == 4 and #heading.classes == 0 and
          #heading.attributes == 1 and heading.attributes["fact-id"] == "authorization-arrangements"
        if detail.t == "Div" and detail.identifier == "" and #detail.classes == 1 and
           #detail.attributes == 0 and
           ((div.identifier == "q-share-restrictions" and detail.classes:includes("authorization-details")) or
            (q8_authorization and detail.classes:includes("answer-detail"))) then
          for _, tbl in ipairs(detail.content) do
            if tbl.t == "Table" and empty_attr(tbl) and #tbl.colspecs == 2 and #tbl.head.rows <= 1 and
               #tbl.foot.rows == 0 and #tbl.bodies == 1 and #tbl.bodies[1].head == 0 and
               tbl.bodies[1].row_head_columns == 0 and #tbl.caption.long == 0 and tbl.caption.short == nil then
              for _, row in ipairs(tbl.bodies[1].body) do
                if short_authored_row(row) then
                  row.cells[1].contents:insert(1, pandoc.RawBlock("openxml", "<!--DSW:SE:authored-authorization-row:v1-->"))
                end
              end
            end
          end
        end
      end
    end
  end
  return div
end

-- Q8 reuse conditions live in a direct answer list, not in the custom-reason
-- answer-detail above it. Only direct tables in each record's authored detail
-- are eligible. Keep individual short rows, never the table or adjacent prose.
local function keep_authored_reuse_rows(div)
  for _, answer in ipairs(div.content) do
    if answer.t == "Div" and answer.identifier == "" and #answer.classes == 1 and
       answer.classes:includes("answer") and #answer.attributes == 0 then
      for _, list in ipairs(answer.content) do
        if list.t == "BulletList" then
          for _, item in ipairs(list.content) do
            local label, permission, detail = item[1], item[2], item[3]
            -- The earlier pilot filter may keep a fixed permission with its
            -- authored terms. Recognize that exact one-paragraph wrapper for
            -- ownership only; retain the wrapper and every existing row rule.
            if permission and permission.t == "Div" and permission.identifier == "" and
               #permission.classes == 0 and #permission.attributes == 1 and
               permission.attributes["custom-style"] == "Pilot List Lead" and
               #permission.content == 1 and permission.content[1].t == "Para" then
              permission = permission.content[1]
            end
            local label_ok = label and label.t == "Div" and label.identifier == "" and #label.classes == 0 and
              (#label.attributes == 0 or (#label.attributes == 1 and label.attributes["custom-style"] == "Pilot List Lead")) and
              #label.content == 1 and (label.content[1].t == "Plain" or label.content[1].t == "Para")
            if #item == 3 and label_ok and (permission.t == "Plain" or permission.t == "Para") then
              if detail.t == "Div" and detail.identifier == "" and #detail.classes == 1 and
                 detail.classes:includes("answer-detail") and #detail.attributes == 0 then
                for _, tbl in ipairs(detail.content) do
                  if tbl.t == "Table" and empty_attr(tbl) and #tbl.colspecs == 2 and #tbl.head.rows <= 1 and
                     #tbl.foot.rows == 0 and #tbl.bodies == 1 and #tbl.bodies[1].head == 0 and
                     tbl.bodies[1].row_head_columns == 0 and #tbl.caption.long == 0 and tbl.caption.short == nil then
                    for _, row in ipairs(tbl.bodies[1].body) do
                      if short_authored_row(row) then
                        row.cells[1].contents:insert(1, pandoc.RawBlock("openxml", "<!--DSW:SE:authored-reuse-row:v1-->"))
                      end
                    end
                  end
                end
              end
            end
          end
        end
      end
    end
  end
  return div
end

-- Q15 authored tables may be long, but an individually short two-cell row
-- should not leave a blank row fragment on the next page. Keep no prose or
-- neighbouring row with it; long/complex cells retain their original AST.
local function keep_authored_resource_rows(div)
  local marker = "<!--DSW:SE:authored-resource-row:v1-->"
  local function owned_id(tbl)
    if tbl.t ~= "Table" or tbl.identifier ~= "" or #tbl.bodies ~= 1 or #tbl.bodies[1].head ~= 0 or
       #tbl.bodies[1].body ~= 1 or #tbl.foot.rows ~= 0 or #tbl.caption.long ~= 0 or tbl.caption.short ~= nil then return nil end
    local row = tbl.bodies[1].body[1]
    if row.identifier ~= "" or #row.classes ~= 0 or #row.attributes ~= 1 then return nil end
    for _, cell in ipairs(row.cells) do
      if cell.row_span ~= 1 or cell.col_span ~= 1 then return nil end
    end
    if #tbl.colspecs == 2 and #tbl.classes == 1 and #tbl.attributes == 1 and
       #row.cells == 2 and tbl.classes:includes("word-rich-funding-metadata") and
       row.attributes["item-id"] == tbl.attributes["item-id"] then
      return tbl.attributes["item-id"]
    end
    if #tbl.colspecs == 3 and #tbl.classes == 2 and #tbl.attributes == 0 and
       #row.cells == 3 and
       tbl.classes:includes("resource-table") and tbl.classes:includes("word-rich-budget-metadata") then
      return row.attributes["item-id"]
    end
    return nil
  end
  for _, answer in ipairs(div.content) do
    if answer.t == "Div" and answer.identifier == "" and #answer.classes == 1 and
       answer.classes:includes("answer") and #answer.attributes == 0 then
      for _, project in ipairs(answer.content) do
        if project.t == "Div" and project.identifier == "" and #project.classes == 1 and
           project.classes:includes("project-resources") then
          local ids = {}
          for _, block in ipairs(project.content) do
            local id = owned_id(block)
            if id and id ~= "" then ids[id] = true end
          end
          for _, resource in ipairs(project.content) do
            if resource.t == "Div" and resource.identifier == "" and #resource.classes == 1 and
               (resource.classes:includes("word-rich-resource-purpose") or resource.classes:includes("word-rich-resource-funding")) and
               #resource.attributes == 1 and ids[resource.attributes["item-id"]] then
              for _, detail in ipairs(resource.content) do
                local attrs_ok = detail.t == "Div" and (#detail.attributes == 0 or
                  (resource.classes:includes("word-rich-resource-purpose") and #detail.attributes == 2 and
                   detail.attributes["fact-id"] == "resource-justification" and detail.attributes["status"] == "complete"))
                if detail.t == "Div" and detail.identifier == "" and attrs_ok and
                   #detail.classes == 1 and detail.classes:includes("answer-detail") then
                  for _, tbl in ipairs(detail.content) do
                    if tbl.t == "Table" and empty_attr(tbl) and #tbl.colspecs == 2 and #tbl.head.rows <= 1 and
                       #tbl.foot.rows == 0 and #tbl.bodies == 1 and #tbl.bodies[1].head == 0 and
                       tbl.bodies[1].row_head_columns == 0 and #tbl.caption.long == 0 and tbl.caption.short == nil then
                      for _, row in ipairs(tbl.bodies[1].body) do
                        if short_authored_row(row) then row.cells[1].contents:insert(1, pandoc.RawBlock("openxml", marker)) end
                      end
                    end
                  end
                end
              end
            end
          end
        end
      end
    end
  end
  return div
end

local function question(div)
  if FORMAT ~= "docx" and FORMAT ~= "json" then return nil end
  if div.classes:includes("answer") or div.classes:includes("answer-detail") or
     div.classes:includes("abstract") then return div, false end
  if div.identifier == "q-what-data" then return keep_authored_format_rows(div), false end
  if div.identifier == "q-required-resources" then return keep_authored_resource_rows(div), false end
  if div.identifier == "q-copyright-ipr" then
    return keep_authored_reuse_rows(keep_authored_authorization_rows(div)), false
  end
  if div.identifier == "q-share-restrictions" then return keep_authored_authorization_rows(div), false end
  if div.identifier ~= "q-ethical-issues" then
    if div.classes:includes("question") then return div, false end
    return nil
  end
  local changed = false
  for _, answer in ipairs(div.content) do
    if answer.t == "Div" and answer.identifier == "" and #answer.classes == 1 and
       answer.classes:includes("answer") and #answer.attributes == 0 then
      for _, detail in ipairs(answer.content) do
        if detail.t == "Div" and detail.identifier == "" and #detail.classes == 1 and
           detail.classes:includes("answer-detail") and #detail.attributes == 0 then
          local blocks = pandoc.List()
          for position, block in ipairs(detail.content) do
            -- Raw markers would interrupt Pandoc's automatic separator between
            -- adjacent tables. Leave such groups completely unchanged.
            local previous, following = detail.content[position - 1], detail.content[position + 1]
            local adjacent = (previous and previous.t == "Table") or (following and following.t == "Table")
            local rows = block.t == "Table" and not adjacent and bounded(block) or nil
            if rows then
              for index = 1, #rows - 1 do
                for _, cell in ipairs(rows[index].cells) do
                  cell.contents = {pandoc.Div({pandoc.Para(cell.contents[1].content)},
                    pandoc.Attr("", {}, {["custom-style"]="Pilot Table Lead"}))}
                end
              end
              blocks:insert(pandoc.RawBlock("openxml", begin_marker))
              blocks:insert(block)
              blocks:insert(pandoc.RawBlock("openxml", end_marker))
              changed = true
            else blocks:insert(block) end
          end
          detail.content = blocks
        end
      end
    end
  end
  if changed then return div, false end
  return nil, false
end

-- A version table may span many pages; keep only individually bounded rows.
-- The question/abstract traversal guards above exclude authored answer tables.
local function history_rows(tbl)
  if (FORMAT ~= "docx" and FORMAT ~= "json") or tbl.identifier ~= "" or
     #tbl.classes ~= 1 or not tbl.classes:includes("version-history") or #tbl.attributes ~= 0 or
     #tbl.colspecs ~= 3 or #tbl.head.rows ~= 1 or #tbl.foot.rows ~= 0 or
     #tbl.bodies ~= 1 or #tbl.bodies[1].head ~= 0 or tbl.bodies[1].row_head_columns ~= 0 or
     #tbl.caption.long ~= 0 or tbl.caption.short ~= nil then return nil end
  for _, row in ipairs(tbl.bodies[1].body) do
    -- Empty name cells have a different Pandoc placeholder encoding; leave
    -- those records unchanged rather than introducing a new paragraph style.
    local eligible = empty_attr(row) and #row.cells == 3 and width(row.cells[1].contents) > 0
    for column, cell in ipairs(row.cells) do
      if not empty_attr(cell) or cell.row_span ~= 1 or cell.col_span ~= 1 or
         #cell.contents > 1 or width(cell.contents) > (({80,32,160})[column] or 0) then eligible = false end
      for _, block in ipairs(cell.contents) do
        if (block.t ~= "Plain" and block.t ~= "Para") or not simple(block.content) then eligible = false end
        for token in pandoc.utils.stringify(block):gmatch("%S+") do
          if token:match("^[%z\1-\127]+$") and #token > 40 then eligible = false end
        end
      end
    end
    if eligible then
      row.cells[1].contents:insert(1, pandoc.RawBlock("openxml", "<!--DSW:SE:history-row:v1-->"))
    end
  end
  return tbl
end

return {{traverse="topdown", Div=question, Table=history_rows}}
