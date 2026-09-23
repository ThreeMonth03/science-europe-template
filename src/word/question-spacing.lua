-- Submission-only marker; the XML helper changes only this one Heading3's
-- direct paragraph properties. No title/inline/outline/bookmark is replaced.
local requirements = {
  ["q-how-data"]="SE-1a", ["q-what-data"]="SE-1b", ["q-docs-metadata"]="SE-2a",
  ["q-quality-control"]="SE-2b", ["q-store-backup"]="SE-3a", ["q-access-security"]="SE-3b",
  ["q-personal-data"]="SE-4a", ["q-copyright-ipr"]="SE-4b", ["q-ethical-issues"]="SE-4c",
  ["q-share-restrictions"]="SE-5a", ["q-data-preservation"]="SE-5b", ["q-access-data"]="SE-5c",
  ["q-persistent-identifier"]="SE-5d", ["q-dm-responsible"]="SE-6a", ["q-required-resources"]="SE-6b"
}
local function div_shape(block, classes)
  if block.t ~= "Div" or block.identifier ~= "" or #block.attributes ~= 0 or #block.classes ~= #classes then return false end
  for i, class in ipairs(classes) do if block.classes[i] ~= class then return false end end
  return true
end
local function empty_answer(answer, id)
  if not div_shape(answer, {"answer"}) then return false end
  if #answer.content == 0 then return true end
  if id ~= "q-store-backup" or #answer.content ~= 1 then return false end
  local policy = answer.content[1]
  if not div_shape(policy, {"workspace-policy", "dataset-policy"}) or #policy.content ~= 2 then return false end
  for _, gap in ipairs(policy.content) do
    if not div_shape(gap, {"reading-gap"}) or #gap.content ~= 0 then return false end
  end
  return true
end
local function question(div)
  if FORMAT ~= "docx" and FORMAT ~= "json" then return nil end
  if div.classes:includes("answer") or div.classes:includes("answer-detail") or div.classes:includes("abstract") then return div, false end
  if not div.classes:includes("question") then return nil end
  if not requirements[div.identifier] or #div.classes ~= 2 or
      not div.classes:includes("compact-empty-question") or #div.attributes > 1 or
      (#div.attributes == 1 and div.attributes["requirement-id"] ~= requirements[div.identifier]) or #div.content ~= 2 then return div, false end
  local heading, answer = div.content[1], div.content[2]
  if heading.t ~= "Header" or heading.level ~= 3 or not empty_answer(answer, div.identifier) then return div, false end
  -- The known question headings are plain text; unexpected rich headings fall back.
  for _, inline in ipairs(heading.content) do
    if inline.t ~= "Str" and inline.t ~= "Space" and inline.t ~= "SoftBreak" then return div, false end
  end
  div.content = {
    pandoc.RawBlock("openxml", "<!--DSW:SE:empty-question:v1:begin-->"), heading,
    pandoc.RawBlock("openxml", "<!--DSW:SE:empty-question:v1:end-->"), answer
  }
  return div, false
end
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
      for j = 2, #section.content do
        -- Preserve one coherent empty section, not an isolated last question.
        -- The existing question pass still runs on the unmodified question Div.
        if j < #section.content then
          content:insert(pandoc.RawBlock("openxml", "<!--DSW:SE:empty-section-link:v1:begin-->"))
        end
        content:insert(section.content[j])
        if j < #section.content then
          content:insert(pandoc.RawBlock("openxml", "<!--DSW:SE:empty-section-link:v1:end-->"))
        end
      end
      section.content = content
    end
  end
  return div, false
end
return {{traverse="topdown", Div=empty_sections}, {traverse="topdown", Div=question}}
