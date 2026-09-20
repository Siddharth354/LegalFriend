interface HastNode {
  type: string;
  value?: string;
  tagName?: string;
  properties?: Record<string, unknown>;
  children?: HastNode[];
}

const CITE_RE = /\[(\d{1,3})\]/g;
const OPAQUE_TAGS = new Set(["code", "pre", "cite"]);

function splitTextNode(node: HastNode): HastNode[] {
  const value: string = node.value ?? "";
  CITE_RE.lastIndex = 0;
  if (!CITE_RE.test(value)) return [node];

  CITE_RE.lastIndex = 0;
  const out: HastNode[] = [];
  let last: number = 0;
  let match: RegExpExecArray | null = CITE_RE.exec(value);
  while (match !== null) {
    if (match.index > last) {
      out.push({ type: "text", value: value.slice(last, match.index) });
    }
    out.push({
      type: "element",
      tagName: "cite",
      properties: {},
      children: [{ type: "text", value: match[1] }],
    });
    last = match.index + match[0].length;
    match = CITE_RE.exec(value);
  }
  if (last < value.length) out.push({ type: "text", value: value.slice(last) });
  return out;
}

function walk(node: HastNode): void {
  if (node.children === undefined) return;
  const next: HastNode[] = [];
  for (const child of node.children) {
    if (child.type === "text") {
      next.push(...splitTextNode(child));
      continue;
    }
    if (child.tagName === undefined || !OPAQUE_TAGS.has(child.tagName))
      walk(child);
    next.push(child);
  }
  node.children = next;
}

export function rehypeCitations() {
  return (tree: HastNode): void => walk(tree);
}
