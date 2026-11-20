# ND1_DungeonGame

Unreal Engine 5.8 のダンジョン探索教材 2-1〜2-4。
ゲーム処理は編集可能な Blueprint、ステートマシン、Behavior Tree で構成しています。
`ND1DungeonEditor` は MCP からアセットを構築・検証する Editor 専用モジュールです。

## 教材のブランチ

| ブランチ | 終了時点の内容 |
|---|---|
| `02-01` | CubeMan、カメラ相対移動、左右キーのカメラ回転、反転設定 |
| `02-02` | Idle/Run、足音、加算・減算 BSP による迷路と出入口 |
| `02-03` | Slime、NavMesh、ランダム巡回、Walk/Run の移動モード |
| `02-04` | 視覚による発見、追跡、見失いタイマー、巡回復帰 |

分割の依頼時点で 2-4 まで実装済みだったため、各教材の終了状態を
Unreal Editor で再構成して順番にコミットしています。`02-04` が完成版です。
共通の MCP スクリプトには後続教材の構築処理も含みます。

## 起動と操作

UE 5.8 と Visual Studio の C++ 開発環境が必要です。
`.uproject` の EngineAssociation をローカルの UE 5.8 に関連付け、
`ND1_DungeonGameEditor Win64 Development` をビルドして開きます。
生成物 Binaries / Intermediate / Saved は Git に含めていません。

- WASD: カメラを基準に移動
- 左右矢印: カメラの水平回転
- `BP_DungeonPlayerController.CameraYawInverse`: 回転方向を反転

## MCP

UE 標準 ModelContextProtocol / EditorToolset / PythonScriptPlugin を使用します。
エディタ起動時に `http://127.0.0.1:8000/mcp` で待ち受けます。
別プロジェクトで同じポートを使用しないでください。

## 実行結果 GIF

`Docs/GIF/` に各教材の実際の PIE 画面を保存します。GIF は無音です。
足音の設定と通知は `02-04` の検証スクリプトで確認できます。
MCP の `run_stage("demo")` で録画し、`Scripts/encode-demo.ps1 -Stage 02-04` で変換できます。
背景時の CPU 制限は録画中だけ解除し、終了時に元へ戻します。

```powershell
node Scripts/unreal-mcp.mjs check
node Scripts/unreal-mcp.mjs list
node Scripts/unreal-mcp.mjs describe nd1_lesson_tools.DungeonLessonTools
```

`run_stage` はアセットを構築・検証するため、編集内容を保存してから利用してください。
`verification` と `runtime_test` は完成版 `02-04` 用、`checkpoint_audit` は各ブランチ用です。
FBX 入力元は `Content/Python/nd1_foundation.py` の `SOURCE` で指定します。
`checkpoints` はブランチ分割用の内部処理で、実行中のアセットを以前の教材状態に変更します。
通常の編集では実行不要です。

## 教材との対応

カプセル88/25、メッシュZ=-88・Yaw=270、カメラPitch=-50・距離500、
回転速度Yaw=1080、アニメーション閾値100、足音音量0.2、
Slime の歩行100・走行500、巡回半径500、待機3±1秒を設定しています。
視覚は半径3000・見失い3500・周辺視野90度です。

見失い時間は説明スライドの3秒を採用しています。
最終グラフ画像の5秒という表示とは差があります。
足音は配布資料に音源がなかったため、ユーザー承認の上で UE 同梱の
`/Engine/VREditor/Sounds/UI/` の次の4音を複製しています。

- `Drop_Item_From_ContentBrowser`
- `Dockable_Window_Drop`
- `Object_Snaps_To_Grid`
- `Object_Snaps_To_Another_Actor`

モデル・アニメーションと UE 由来音源は、教材・UE の利用条件に従って扱ってください。
