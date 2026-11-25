# ND1_DungeonGame

Unreal Engine 5.8 のダンジョン探索ゲーム **THE ECHO VAULT**。
教材 2-1〜2-4 の CubeMan・カメラ・アニメーション・Slime AI を Blueprint / Behavior Tree で保持し、
`ND1DungeonRuntime` に2フロアの進行、スコア、UI、追加アクションを実装しています。
`ND1DungeonEditor` は MCP からアセットを構築・検証する Editor 専用モジュールです。

## ゲームの遊び方

タイトルの BEGIN EXPEDITION または Enter で開始します。
各フロアで琥珀色の紋章を3個集め、緑色に開いた出口へ進んでください。
青い遺物は得点、緑の結晶は体力回復です。Slime に接触すると体力が1減り、0でゲームオーバーになります。
フロアクリア時には残り体力と所要時間に応じたボーナスが加算されます。

- Shift: スタミナを使ってダッシュ
- Space: 近くの Slime を2.3秒止めるエコーパルス（スタミナ35、再使用6秒）
- P: ポーズ・再開（Escも対応。EditorのPIEではEscはプレイ終了に使われます）
- 遺物を5秒以内に続けて取ると最大5倍の連続取得ボーナス
- 探索した範囲が見えるミニマップ、紋章・出口までの距離、発見警告を表示
- 全2フロア。勝利時にベストスコア・最短クリア時間をローカル保存

起動マップは `/Game/Maps/L_Vault01`、次は `L_Vault02` です。
旧教材マップ `/Game/GameLevel` も保持しています。
プレイヤーモデルはユーザー指定により教材の CubeMan を継続しています。
評価表の「Unityちゃん」とはモデル名が異なります。
提出用ZIP・提出フォルダの作成や整理はまだ行っていません。

## 教材のブランチ

| ブランチ | 終了時点の内容 |
|---|---|
| `main` | 通常の作業用・最新の完成版（02-04と以後の改善を含む） |
| `02-01` | CubeManと3本のアニメーション取込、カメラ相対移動、カメラ回転、反転設定 |
| `02-02` | Idle/Run、足音、加算・減算 BSP による迷路と出入口 |
| `02-03` | Slime、NavMesh、ランダム巡回、Walk/Run の移動モード |
| `02-04` | 視覚による発見、追跡、見失いタイマー、巡回復帰 |

分割の依頼時点で 2-4 まで実装済みだったため、各教材の終了状態を
Unreal Editor で再構成して順番にコミットしています。
`02-01`〜`02-04` は教材ごとの区切り、`main` は最新の完成版です。
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

```powershell
node Scripts/unreal-mcp.mjs check
node Scripts/unreal-mcp.mjs list
node Scripts/unreal-mcp.mjs describe nd1_lesson_tools.DungeonLessonTools
```

`run_stage` はアセットを構築・検証するため、編集内容を保存してから利用してください。
`verification` と `runtime_test` は完成版 `02-04` 用、`checkpoint_audit` は各ブランチ用です。
新しい2フロアの統合確認は `assessment_test` です。PIE外では両マップの照明・NavMeshを保存し、
PIE中ではタイトルから勝利・記録保存まで検査します。結果は `Saved/Assessment` に出力します。
PIE外では、結果が `passed` になるまで数秒おきに呼び出してください。
`assessment_input_test` はPIE中の入力・向き・アニメーション・追加操作を確認します。
Editor / Game のビルドと、統合41項目・入力関連29項目の確認が完了しています。
`assessment` は新規マップを再構築する内部処理で、通常のプレイには不要です。
FBX 入力元は `Content/Python/nd1_foundation.py` の `SOURCE` で指定します。
`checkpoints` はブランチ分割用の内部処理で、実行中のアセットを以前の教材状態に変更します。
通常の編集では実行不要です。

## 実行結果 GIF

| 教材 | 実際の PIE 画面 |
|---|---|
| 02-01 | [キャラクター移動・カメラ回転](Docs/GIF/02-01.gif) |
| 02-02 | [Idle/Run・出入口通過・カメラ回転](Docs/GIF/02-02.gif) |
| 02-03 | [Slime の待機・変形・巡回](Docs/GIF/02-03.gif) |
| 02-04 | [Slime の発見・追跡](Docs/GIF/02-04.gif) |

各教材ブランチにも、その段階の GIF を保存しています。
GIF は無音です。足音の設定と通知は完成版の検証スクリプトで確認できます。
MCP の `run_stage("demo")` で録画し、`Scripts/encode-demo.ps1 -Stage 02-04` で変換できます。
背景時の CPU 制限は録画中だけ解除し、終了時に元へ戻します。
設定値と動作の検証記録は [Docs/VERIFICATION.md](Docs/VERIFICATION.md) を参照してください。

## 教材との対応

カプセル88/25、メッシュZ=-88・相対Yaw=0、カメラPitch=-50・距離500、
回転速度Yaw=1080、アニメーション閾値100、足音音量0.2、
Slime の歩行100・走行500、巡回半径500、待機3±1秒を設定しています。
視覚は半径3000・見失い3500・周辺視野90度です。

配布 FBX の取込時に Yaw=270 を適用するとモデルの正面は +X になります。
メッシュ側でも Yaw=270 を指定すると移動方向に対して90度ずれるため、
取込済みモデルに合わせてメッシュの相対 Yaw は0に補正しています。
`facing_test` は肩のボーンから求めた見た目の正面を速度方向と比較します。

見失い時間は説明スライドの3秒を採用しています。
最終グラフ画像の5秒という表示とは差があります。
足音は UE 同梱の実際の接地音
`/NetworkPredictionExtras/Audio/Footstep_Rock_Land01` を基にした4つのバリエーションです。
以前の UI 効果音から差し替え、わずかな音程差と高音域の調整を加えています。
SoundCue の音量0.2、通知フレーム7と0.62秒は維持しています。
[足音の試聴](Docs/Audio/footsteps-stone-preview.mp3) / [音源と加工仕様](SourceAssets/Audio/Footsteps/README.md)

`run_stage("footsteps")` は、通常時は音源を取り込み、PIE 中は足音を1回試聴します。

モデル・アニメーションと UE 由来音源は、教材・UE の利用条件に従って扱ってください。

追加BGM2曲・効果音8種は手続き生成したオリジナル音源です。
生成元は `Scripts/generate-vault-audio.mjs`、音源と仕様は `SourceAssets/Audio/Vault` に保存しています。
