import { pathToFileURL } from 'node:url';

export const endpoint = 'http://127.0.0.1:8000/mcp';
let session;
let nextId = 1;

export async function rpc(method, params = {}, notification = false) {
  const requestId = notification ? undefined : nextId++;
  const response = await fetch(endpoint, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Accept: 'application/json, text/event-stream',
      ...(session ? { 'Mcp-Session-Id': session } : {}),
    },
    body: JSON.stringify({ jsonrpc: '2.0', ...(!notification ? { id: requestId } : {}), method, params }),
    signal: AbortSignal.timeout(60000),
  });
  session = response.headers.get('mcp-session-id') || session;
  const body = await response.text();
  if (!response.ok) throw new Error(`MCP HTTP ${response.status}: ${body}`);
  if (notification || !body.trim()) return;
  const messages = response.headers.get('content-type')?.includes('text/event-stream')
    ? body.split(/\r?\n\r?\n/).flatMap(event => {
      const data = event.split(/\r?\n/).filter(line => line.startsWith('data:')).map(line => line.slice(5).trimStart()).join('\n');
      return data ? [JSON.parse(data)] : [];
    })
    : [JSON.parse(body)];
  const message = messages.find(item => item.id === requestId);
  if (!message) throw new Error('MCP response has no matching request ID');
  if (message.error) throw new Error(JSON.stringify(message.error));
  return message.result;
}

export async function connect() {
  const info = await rpc('initialize', {
    protocolVersion: '2024-11-05', capabilities: {},
    clientInfo: { name: 'nd1-dungeon-mcp', version: '1.0.0' },
  });
  await rpc('notifications/initialized', {}, true);
  return info;
}

export async function tool(name, args = {}) {
  const result = await rpc('tools/call', { name, arguments: args });
  if (result.isError) throw new Error(JSON.stringify(result));
  return result;
}

export async function call(toolset, name, args = {}) {
  const result = await tool('call_tool', { toolset_name: toolset, tool_name: name, arguments: args });
  const text = result.content?.find(item => item.type === 'text')?.text;
  if (!text) return result;
  try {
    const parsed = JSON.parse(text);
    return Object.hasOwn(parsed, 'returnValue') ? parsed.returnValue : parsed;
  } catch { return text; }
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  try {
    const [operation = 'check', toolset, name, json = '{}'] = process.argv.slice(2);
    if (!['check', 'list', 'describe', 'call'].includes(operation)) throw new Error('Usage: node Scripts/unreal-mcp.mjs check|list|describe <toolset>|call <toolset> <tool> [JSON]');
    const info = await connect();
    let result;
    if (operation === 'check') result = { endpoint, server: info.serverInfo, pieRunning: await call('EditorToolset.EditorAppToolset', 'IsPIERunning'), toolsets: await tool('list_toolsets') };
    else if (operation === 'list') result = await tool('list_toolsets');
    else if (operation === 'describe') result = await tool('describe_toolset', { toolset_name: toolset });
    else result = await call(toolset, name, JSON.parse(json));
    console.log(JSON.stringify(result, null, 2));
  } catch (error) {
    console.error(`Unreal MCP: ${error.message}`);
    process.exitCode = 1;
  }
}
