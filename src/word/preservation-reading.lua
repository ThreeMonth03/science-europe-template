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

-- Dataset ownership is a single shallow indent in both languages. Visit only
-- direct owned records, never a lookalike inside an authored answer. Existing
-- keep styles retain their behavior; a proven short record links only its own
-- paragraphs and ends with keepNext=false, not the following dataset.
local function layout_question(question)
  if question.classes:includes("answer") or question.classes:includes("answer-detail") or
     question.classes:includes("abstract") then return question, false end
  if question.identifier ~= "q-how-data" and question.identifier ~= "q-share-restrictions" and
     question.identifier ~= "q-data-preservation" then return nil end
  if FORMAT ~= "docx" and FORMAT ~= "json" then return nil end
  local styles = {["Pilot Label"]="Pilot Dataset Label", ["Pilot Lead"]="Pilot Dataset Lead",
    ["Pilot Provenance"]="Pilot Dataset Provenance", ["Pilot Preservation Summary"]="Pilot Dataset Summary"}
  local function record(dataset)
    if dataset.t ~= "Div" or dataset.identifier ~= "" or not dataset.classes:includes("dataset-section") or
       #dataset.classes > 2 or #dataset.attributes ~= 1 or not dataset.attributes["item-id"] then return end
    dataset.attributes["custom-style"] = "Pilot Dataset Detail"
    local paragraphs, simple = {}, true
    local function scan(blocks, start, repository_list, authored)
      for index=start or 1,#blocks do
        local block = blocks[index]
        if block.t == "Para" or block.t == "Plain" then
          if width(block) > 360 then simple = false end
          block:walk({Inline=function(inline)
            if inline.t == "Image" or inline.t == "Note" or inline.t == "Math" or inline.t == "RawInline" then simple = false end
          end})
          table.insert(paragraphs, {blocks=blocks, index=index, block=block, owned=not authored})
        elseif block.t == "Div" then
          -- Only this fixed rights-holder label is secondary type. An author's
          -- own bold paragraph keeps the ordinary body-size label style.
          local label = block.content[1]
          if block.classes:includes("answer-detail") and block.attributes["fact-id"] == "reuse-rightsholder" and
             label and label.t == "Div" and label.attributes["custom-style"] == "Pilot Label" then
            label.attributes["custom-style"] = "Pilot Dataset Attribute"
          end
          local style = block.attributes["custom-style"]
          if styles[style] then block.attributes["custom-style"] = styles[style] end
          scan(block.content, 1, block.classes:includes("repository-destinations"),
            authored or block.classes:includes("answer-detail"))
        elseif block.t == "BulletList" then
          if not repository_list or #block.content > 3 then simple = false end
          for _, item in ipairs(block.content) do scan(item, 1, false, authored) end
        else simple = false end
      end
    end
    -- Header5 (or the generated neutral-label paragraph) remains the anchor.
    local first = dataset.content[1]
    local anchor = first and (first.t == "Header" or
      (first.t == "Div" and first.attributes["custom-style"] == "Pilot Label"))
    scan(dataset.content, anchor and 2 or 1)
    local bounded = dataset.classes:includes("short-dataset-record") and simple and
      width(dataset) <= 700 and #paragraphs >= 1 and #paragraphs <= 8
    if bounded then
      for index, item in ipairs(paragraphs) do
        item.blocks[item.index] = pandoc.Div({pandoc.Para(item.block.content)},
          pandoc.Attr("", {}, {["custom-style"]=index < #paragraphs and "Pilot Dataset Lead" or "Pilot Dataset Terminal"}))
      end
    elseif question.identifier == "q-share-restrictions" and #paragraphs >= 2 then
      local tail = dataset.content[#dataset.content]
      local previous, final = paragraphs[#paragraphs-1], paragraphs[#paragraphs]
      -- A longer record can still have a bounded fixed terminal pair. Keep
      -- only the previous paragraph's end with this tail; the record may flow.
      if known_div(tail, {"qualified-reference-tail"}, {}) and #tail.content == 1 and
         tail.content[1] == final.block and final.owned and previous.owned and
         width(final.block) <= 160 and width(previous.block) <= 600 then
        previous.blocks[previous.index] = pandoc.Div({pandoc.Para(previous.block.content)},
          pandoc.Attr("", {}, {["custom-style"]="Pilot Dataset Lead"}))
        final.blocks[final.index] = pandoc.Div({pandoc.Para(final.block.content)},
          pandoc.Attr("", {}, {["custom-style"]="Pilot Dataset Terminal"}))
      end
    end
  end
  local function records(container)
    for _, child in ipairs(container.content) do record(child) end
  end
  for _, answer in ipairs(question.content) do
    if known_div(answer, {"answer"}, {}) then
      records(answer)
      for _, block in ipairs(answer.content) do
        if known_div(block, {"dataset-list"}, {}) then records(block)
        elseif known_div(block, {}, {}) and block.content[1] and block.content[1].t == "Header" and block.content[1].level == 4 then
          for _, list in ipairs(block.content) do if known_div(list, {"dataset-list"}, {}) then records(list) end end
        end
      end
    end
  end
  return question, false
end

return {{traverse="topdown", Div=Div}, {traverse="topdown", Div=layout_question}}
