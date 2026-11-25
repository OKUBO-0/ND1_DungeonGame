# 評価課題の実装・検証

参照スライド: 1vLud-WEBA21QWb_QgGcpsatiMCBNP6QAcolB0ltIPdo。
提出用ZIPや提出フォルダの作成・整理はユーザー指示により実施しない。

採点: 提出規則6、カメラ20、Unityちゃんカメラ基準移動20、アニメ切替+ランダム足音15、追跡Slime3、巡回追跡切替3、アウトゲーム3、BGM追加SE3、複数レベル3、加点アイテム4、創意工夫最大20。
モデル表記はユーザー確認済み。「教材通りCubeManを継続する」と明示回答。

設計: THE ECHO VAULT。3つのsigilで門を解放する2フロア探索。
タイトル/操作説明/ポーズ/フロアクリア/ゲームオーバー/勝利/再挑戦のフロー。
追加: 探索型ミニマップ、スタミナダッシュ、近距離Slimeスタンパルス、連続取得ボーナス、ベスト記録保存、BGM2曲・効果音8種。

既存のBPプレイヤー/Controller/AnimBP/AIを保持。
新規 C++ Runtime module ND1DungeonRuntime は追加のゲーム進行/UI/Actorを担当。
新規マップは /Game/Maps/L_Vault01, L_Vault02 を作り、旧GameLevelは保持。
AGENTS.md に従い uasset/umap は MCP から編集する。

作業前の Content/Config と既存dirty一覧は Saved/BeforeAssessment に保存。
main の開始コミットと既存の8つのdirtyバイナリは保存・保持する。
UE5.8 の Editor / Game ターゲットのビルド成功。パッケージ化は未実施。
2マップの作成成功（到達可能セル52/74、sigil各3、treasure12/15、Slime3/4）。
UIマテリアル10・BGM2/SE8インポート済み。ConfigにVaultGameInstance/DefaultMap設定済み。
NativeWidgetのRootCanvas再利用、SaveGameのAutomation別スロット、スタン移動停止を修正済み。
UI込みゲーム画面用CapturePlayViewportのSlate対応済み。
assessment_test.py にタイトルからゲームオーバー/Retry/2フロア/Victory/SaveGameまでの検査を追加。
assessment_input_test.py では PlayerInput に実キーを送り、カメラ相対移動、見た目の向き、アニメ、ダッシュ、パルス、ポーズを検査。
画面の開始ボタンと短いPキー入力も実操作で確認。
結果・画面は Saved/Assessment（Git対象外）。検証は専用SaveGameスロットを使う。
最終結果: 統合41項目、入力・足音設定など29項目が全て合格。再起動後も表示を確認。
マテリアルは SkeletalMesh 用の使用フラグを設定して保存。
開始時点の8つの既存変更バイナリはバックアップと同じハッシュで保持し、今回のコミットには含めない。
