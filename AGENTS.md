# ND1_DungeonGame

このフォルダの ND1_DungeonGame.uproject（UE 5.8）を作業対象とする。

## Unreal MCP

- UE標準の ModelContextProtocol / EditorToolset / PythonScriptPlugin を有効化済み。
- 接続先は `http://127.0.0.1:8000/mcp`。エディタ起動時に自動起動する。
- Codexの既存の `unreal-mcp` 接続を使用する。ツールがチャットに表示されない場合は、Node.jsの `Scripts/unreal-mcp.mjs` で同じMCP APIを呼び出せる。
- 作業前に8000番ポートの所有プロセスがこの `.uproject` を開いていることを確認する。他プロジェクトと同じポートを同時に使用しない。
- `node Scripts/unreal-mcp.mjs check` で接続とPIE状態を確認できる。
- `node Scripts/unreal-mcp.mjs list` → `describe <toolset>` でスキーマを確認し、`call <toolset> <tool> '<JSON>'` で操作する。引数はスキーマに従う。
- スクリプトからは `connect` / `tool` / `call` をimport可能。PowerShellで複雑なJSONを渡す場合は、Node.jsのスクリプトから呼ぶと引用符の問題を避けられる。
- Blueprint、アクタ、アセットの編集にはMCPを使用し、バイナリの `.uasset` / `.umap` を直接書き換えない。編集後は必要なコンパイルと保存を行う。

設定は `Config/DefaultEditorPerProjectUserSettings.ini`。変更後はエディタの再起動が必要。
