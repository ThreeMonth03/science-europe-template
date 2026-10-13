-- Only template-owned transport containers are processed.
local function empty_attributes(el)
  el.identifier = ''
  el.classes = {}
  el.attributes = {}
  return el
end

local function safe_link(el)
  local target = el.target
  local decoded = target:gsub('%%(%x%x)', function(hex) return string.char(tonumber(hex,16)) end)
  local lower = target:lower()
  if not decoded:find('[%c]') and not target:find('\\') and
     (lower:match('^https?://') or lower:match('^mailto:')) then
    return empty_attributes(el)
  end
  local content = el.content
  content:insert(pandoc.Space())
  content:insert(pandoc.Code(target))
  return content
end

local function literal_raw(el)
  if el.t == 'RawBlock' then return pandoc.CodeBlock(el.text) end
  return pandoc.Code(el.text)
end

function CodeBlock(el)
  if not el.classes:includes('dsw-answer-markdown') or
     not el.identifier:match('^dsw%-md%-%d+$') then return nil end
  -- Encode only this string for transport, avoiding HTML-reader tab expansion.
  -- This is not a project JSON export or an LLM document generation path.
  local decoded, source = pcall(pandoc.json.decode, el.text, false)
  if not decoded or type(source) ~= 'string' then
    error('Invalid template-owned Markdown transport')
  end
  -- Treat EOF as the end of a line; retain the original source for transport
  -- validation. This is not indentation repair or a stored-answer rewrite.
  local parse_source = source
  if parse_source:sub(-1) ~= '\n' then parse_source = parse_source .. '\n' end
  local ok, parsed = pcall(pandoc.read, parse_source, 'commonmark+pipe_tables')
  local blocks
  if not ok then
    blocks = {pandoc.CodeBlock(source)}
  else
    parsed = parsed:walk({
      RawBlock=literal_raw, RawInline=literal_raw, Link=safe_link,
      Image=function(image)
        local content = image.caption
        content:insert(pandoc.Space())
        content:insert(pandoc.Code(image.src))
        return content
      end,
      Header=empty_attributes, Code=empty_attributes, CodeBlock=empty_attributes,
      Div=function(div) return div.content end, Span=empty_attributes,
    })
    blocks = parsed.blocks
  end
  -- No user Raw HTML or Div survives; only this owned outer Div is emitted.
  return pandoc.Div(blocks, pandoc.Attr(el.identifier, {}, {
    ['data-source-sha1']=pandoc.utils.sha1(source),
    ['data-source-json']=pandoc.json.encode(source)}))
end
