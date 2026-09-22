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
return {{traverse="topdown", Div=question}}
