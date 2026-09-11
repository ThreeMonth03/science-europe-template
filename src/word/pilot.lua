-- Keep standalone labels with the next paragraph without changing their words.
-- This output-specific rule is independent of the English/Chinese translation.
function Para(paragraph)
  if #paragraph.content == 1 and paragraph.content[1].t == "Strong" then
    return pandoc.Div({paragraph}, pandoc.Attr("", {}, {["custom-style"] = "Pilot Label"}))
  end
end
