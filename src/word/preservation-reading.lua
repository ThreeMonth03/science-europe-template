-- Owned, Word-only presentation after pilot.lua; no translated prose here.
-- Keep a short dataset label and its already-joined fixed policy in one
-- paragraph. A label becomes a bold paragraph lead, not a Heading5. Retain
-- its anchor for links, and never change the question's Heading3/navigation.
local function width(block)
  local result = 0
  for _, code in utf8.codes(pandoc.utils.stringify(block)) do
    result = result + (code >= 0x2E80 and 2 or 1)
  end
  return result
end

local function plain(inlines)
  if #inlines == 0 then return false end
  for _, value in ipairs(inlines) do
    if value.t ~= "Str" and value.t ~= "Space" and value.t ~= "SoftBreak" then return false end
  end
  return true
end

local function known_div(block, classes, attributes)
  if block.t ~= "Div" or block.identifier ~= "" or #block.classes ~= #classes then return false end
  for _, class in ipairs(classes) do if not block.classes:includes(class) then return false end end
  for key, _ in pairs(block.attributes) do if not attributes[key] then return false end end
  return true
end

function Div(question)
  -- Top-down traversal prevents an authored nested lookalike question from
  -- being rewritten before its owning answer-detail boundary is encountered.
  if question.classes:includes("answer") or question.classes:includes("answer-detail") or
     question.classes:includes("abstract") then return question, false end
  if question.identifier ~= "q-data-preservation" then return nil end
  if FORMAT ~= "docx" and FORMAT ~= "json" then return nil end
  local changed = false
  -- Direct known answer/dataset children only: do not descend into authored
  -- answer-detail markup even if it contains similar-looking headings/classes.
  for _, answer in ipairs(question.content) do
    if known_div(answer, {"answer"}, {}) then
      for _, dataset in ipairs(answer.content) do
        -- Pandoc's HTML reader strips the data- prefix from custom attributes.
        if known_div(dataset, {"dataset-section"}, {["item-id"]=true}) and dataset.attributes["item-id"] and
           dataset.attributes["item-id"] ~= "" and #dataset.content >= 2 then
          local label, policy = dataset.content[1], dataset.content[2]
          if label.t == "Header" and label.level == 5 and #label.classes == 0 and #label.attributes == 0 and
             plain(label.content) and width(label) > 0 and width(label) <= 80 and
             known_div(policy, {"preservation-summary", "dataset-policy"}, {}) and #policy.content == 1 then
            local summary = policy.content[1]
            if summary.t == "Para" and plain(summary.content) and width(summary) > 0 and width(summary) <= 360 then
              local inlines = pandoc.List()
              -- Pandoc may supply an anchor even when the template has none.
              -- Preserve it without putting the summary into a heading/TOC.
              local name = label.content
              if label.identifier ~= "" then name = {pandoc.Span(name, pandoc.Attr(label.identifier))} end
              inlines:insert(pandoc.Strong(name))
              inlines:insert(pandoc.LineBreak())
              inlines:extend(summary.content)
              policy.content = {pandoc.Div({pandoc.Para(inlines)},
                pandoc.Attr("", {}, {["custom-style"]="Pilot Preservation Summary"}))}
              dataset.content:remove(1)
              changed = true
            end
          end
        end
      end
    end
  end
  if changed then return question, false end
  return nil, false
end

return {{traverse="topdown", Div=Div}}
