-- Runs before the existing question marker pass, only at the owned DMP root.
-- Existing question parsing and content remain untouched.
local sections = {
  {"sec-data-collection", {"q-how-data", "q-what-data"}},
  {"sec-docs-metadata", {"q-docs-metadata", "q-quality-control"}},
  {"sec-storage-backup", {"q-store-backup", "q-access-security"}},
  {"sec-ethics-legal", {"q-personal-data", "q-copyright-ipr", "q-ethical-issues"}},
  {"sec-sharing-preservation", {"q-share-restrictions", "q-data-preservation", "q-access-data", "q-persistent-identifier"}},
  {"sec-responsibilities-resources", {"q-dm-responsible", "q-required-resources"}}
}
local function plain_heading(block, level)
  if block.t ~= "Header" or block.level ~= level or #block.content == 0 then return false end
  for _, inline in ipairs(block.content) do
    if inline.t ~= "Str" and inline.t ~= "Space" and inline.t ~= "SoftBreak" then return false end
  end
  return true
end
local function trusted_empty_question(block, id)
  if block.t ~= "Div" or block.identifier ~= id or #block.classes ~= 2 or
      not block.classes:includes("question") or not block.classes:includes("compact-empty-question") or
      #block.attributes > 1 or (#block.attributes == 1 and block.attributes["requirement-id"] ~= requirements[id]) or
      #block.content ~= 2 then return false end
  return plain_heading(block.content[1], 3) and empty_answer(block.content[2], id)
end
local function empty_sections(div)
  if FORMAT ~= "docx" and FORMAT ~= "json" then return nil end
  if div.classes:includes("answer") or div.classes:includes("answer-detail") or div.classes:includes("abstract") then return div, false end
  if div.identifier ~= "dmp-content" then return nil end
  -- pilot.lua inserts exactly this page break before the six sections in DOCX.
  -- JSON has no prefix; do not skip arbitrary raw blocks or authored paragraphs.
  local offset = 0
  if FORMAT == "docx" then
    local first = div.content[1]
    if not first or first.t ~= "RawBlock" or first.format ~= "openxml" or
        first.text ~= '<w:p><w:r><w:br w:type="page"/></w:r></w:p>' then return div, false end
    offset = 1
  end
  if #div.classes ~= 0 or #div.attributes ~= 0 or #div.content ~= #sections + offset then return div, false end
  -- Reject an unknown/reordered root before adding any markers.
  for i, expected in ipairs(sections) do
    local section = div.content[i + offset]
    if section.t ~= "Div" or section.identifier ~= expected[1] then return div, false end
  end
  for i, expected in ipairs(sections) do
    local section = div.content[i + offset]
    -- Pandoc preserves an HTML <section> as a Div with its synthetic section class.
    local eligible = #section.classes == 2 and section.classes[1] == "section" and section.classes[2] == "dmp-section" and
      #section.attributes == 0 and #section.content == #expected[2] + 1 and plain_heading(section.content[1], 2)
    if eligible then
      for j, id in ipairs(expected[2]) do
        if not trusted_empty_question(section.content[j + 1], id) then eligible = false; break end
      end
    end
    if eligible then
      local content = pandoc.List({
        pandoc.RawBlock("openxml", "<!--DSW:SE:empty-section:v1:begin-->"),
        section.content[1],
        pandoc.RawBlock("openxml", "<!--DSW:SE:empty-section:v1:end-->")
      })
      for j = 2, #section.content do content:insert(section.content[j]) end
      section.content = content
    end
  end
  return div, false
end
return {{traverse="topdown", Div=empty_sections}, {traverse="topdown", Div=question}}
