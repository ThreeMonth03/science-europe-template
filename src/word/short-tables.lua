-- Word-only Q9 short authored tables; run after the existing shared filters.
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

local function question(div)
  if FORMAT ~= "docx" and FORMAT ~= "json" then return nil end
  if div.classes:includes("answer") or div.classes:includes("answer-detail") or
     div.classes:includes("abstract") then return div, false end
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

return {{traverse="topdown", Div=question}}
