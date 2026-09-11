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

-- Only template-owned policy sentences may be joined; never flatten free answers.
function Div(div)
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
