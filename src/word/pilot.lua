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
