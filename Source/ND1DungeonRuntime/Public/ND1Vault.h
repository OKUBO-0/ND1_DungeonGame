#pragma once
#include "CoreMinimal.h"
#include "Engine/GameInstance.h"
#include "GameFramework/GameModeBase.h"
#include "GameFramework/SaveGame.h"
#include "Engine/DataAsset.h"
#include "Blueprint/UserWidget.h"
#include "ND1Vault.generated.h"

class USoundBase;
class UAudioComponent;
class UStaticMeshComponent;
class USphereComponent;
class UBoxComponent;
class UPointLightComponent;
class UCanvasPanel;
class UTextBlock;
class UProgressBar;
class UMaterialInterface;
class UVerticalBox;
class ACharacter;
class UND1VaultHUD;
class UPrimitiveComponent;

UENUM(BlueprintType)
enum class EVaultState : uint8 { Title, Playing, Paused, FloorClear, GameOver, Victory, Controls };
UENUM(BlueprintType)
enum class EVaultPickup : uint8 { Treasure, Sigil, Heart };

UCLASS(BlueprintType)
class ND1DUNGEONRUNTIME_API UND1VaultAudio : public UDataAsset
{
    GENERATED_BODY()
public:
    UPROPERTY(EditAnywhere, BlueprintReadWrite) TObjectPtr<USoundBase> Pickup;
    UPROPERTY(EditAnywhere, BlueprintReadWrite) TObjectPtr<USoundBase> Sigil;
    UPROPERTY(EditAnywhere, BlueprintReadWrite) TObjectPtr<USoundBase> Hit;
    UPROPERTY(EditAnywhere, BlueprintReadWrite) TObjectPtr<USoundBase> Pulse;
    UPROPERTY(EditAnywhere, BlueprintReadWrite) TObjectPtr<USoundBase> Gate;
    UPROPERTY(EditAnywhere, BlueprintReadWrite) TObjectPtr<USoundBase> Alert;
    UPROPERTY(EditAnywhere, BlueprintReadWrite) TObjectPtr<USoundBase> Confirm;
    UPROPERTY(EditAnywhere, BlueprintReadWrite) TObjectPtr<USoundBase> Clear;
};

UCLASS()
class ND1DUNGEONRUNTIME_API UND1VaultSave : public USaveGame
{
    GENERATED_BODY()
public:
    UPROPERTY(BlueprintReadOnly) int32 BestScore = 0;
    UPROPERTY(BlueprintReadOnly) float BestSeconds = 0;
    UPROPERTY(BlueprintReadOnly) int32 CompletedRuns = 0;
};

UCLASS()
class ND1DUNGEONRUNTIME_API UND1VaultInstance : public UGameInstance
{
    GENERATED_BODY()
public:
    virtual void Init() override;
    void ResetRun();
    void SaveRecord();
    UPROPERTY(BlueprintReadOnly) int32 Score = 0;
    UPROPERTY(BlueprintReadOnly) int32 Health = 3;
    UPROPERTY(BlueprintReadOnly) int32 Floor = 1;
    UPROPERTY(BlueprintReadOnly) float Seconds = 0;
    UPROPERTY(BlueprintReadOnly) bool RunActive = false;
    UPROPERTY(BlueprintReadOnly) int32 FloorStartScore = 0;
    UPROPERTY(BlueprintReadOnly) float FloorStartSeconds = 0;
    UPROPERTY(BlueprintReadOnly) TObjectPtr<UND1VaultSave> Record;
};

/** Editable map metadata also drives the fog-of-war minimap. */
UCLASS()
class ND1DUNGEONRUNTIME_API AND1VaultLevel : public AActor
{
    GENERATED_BODY()
public:
    UPROPERTY(EditAnywhere, BlueprintReadWrite) int32 FloorNumber = 1;
    UPROPERTY(EditAnywhere, BlueprintReadWrite) FString DisplayName = TEXT("THE OUTER VAULT");
    UPROPERTY(EditAnywhere, BlueprintReadWrite) FName NextLevel = TEXT("L_Vault02");
    UPROPERTY(EditAnywhere, BlueprintReadWrite) TArray<FString> Grid;
    UPROPERTY(EditAnywhere, BlueprintReadWrite) float CellSize = 360;
    UPROPERTY(EditAnywhere, BlueprintReadWrite) FVector Origin = FVector::ZeroVector;
    UPROPERTY(EditAnywhere, BlueprintReadWrite) int32 RequiredSigils = 3;
    UPROPERTY(EditAnywhere, BlueprintReadWrite) TObjectPtr<USoundBase> Music;
};

UCLASS()
class ND1DUNGEONRUNTIME_API AND1VaultPickup : public AActor
{
    GENERATED_BODY()
public:
    AND1VaultPickup();
    virtual void BeginPlay() override;
    virtual void Tick(float DeltaSeconds) override;
    UPROPERTY(EditAnywhere, BlueprintReadWrite) EVaultPickup Kind = EVaultPickup::Treasure;
    UPROPERTY(EditAnywhere, BlueprintReadWrite) int32 Points = 100;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly) TObjectPtr<USphereComponent> Trigger;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly) TObjectPtr<UStaticMeshComponent> Gem;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly) TObjectPtr<UPointLightComponent> Light;
private:
    FVector StartLocation;
    bool Collected = false;
    UFUNCTION() void Touch(UPrimitiveComponent* Component, AActor* Other, UPrimitiveComponent* OtherComponent, int32 Body, bool Sweep, const FHitResult& Hit);
};

UCLASS()
class ND1DUNGEONRUNTIME_API AND1VaultGate : public AActor
{
    GENERATED_BODY()
public:
    AND1VaultGate();
    virtual void Tick(float DeltaSeconds) override;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly) TObjectPtr<UBoxComponent> Trigger;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly) TObjectPtr<UBoxComponent> Blocker;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly) TObjectPtr<UStaticMeshComponent> Bars;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly) TObjectPtr<UPointLightComponent> Light;
    UPROPERTY(EditAnywhere, BlueprintReadWrite) TObjectPtr<UMaterialInterface> OpenMaterial;
private:
    bool WasOpen = false;
    UFUNCTION() void Touch(UPrimitiveComponent* Component, AActor* Other, UPrimitiveComponent* OtherComponent, int32 Body, bool Sweep, const FHitResult& Hit);
};

UCLASS()
class ND1DUNGEONRUNTIME_API AND1VaultPulse : public AActor
{
    GENERATED_BODY()
public:
    AND1VaultPulse();
    virtual void Tick(float DeltaSeconds) override;
    UPROPERTY(VisibleAnywhere) TObjectPtr<UStaticMeshComponent> Shell;
    UPROPERTY(EditAnywhere) TObjectPtr<UMaterialInterface> PulseMaterial;
private:
    float Age = 0;
};

UCLASS()
class ND1DUNGEONRUNTIME_API AND1VaultGameMode : public AGameModeBase
{
    GENERATED_BODY()
public:
    AND1VaultGameMode();
    virtual void BeginPlay() override;
    virtual void Tick(float DeltaSeconds) override;
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;
    UPROPERTY(EditAnywhere, BlueprintReadWrite) TObjectPtr<UND1VaultAudio> Audio;
    UPROPERTY(EditAnywhere, BlueprintReadWrite) TObjectPtr<UMaterialInterface> HeroMaterial;
    UPROPERTY(EditAnywhere, BlueprintReadWrite) TObjectPtr<UMaterialInterface> PulseMaterial;
    UPROPERTY(BlueprintReadOnly) EVaultState State = EVaultState::Title;
    UPROPERTY(BlueprintReadOnly) TObjectPtr<AND1VaultLevel> LevelInfo;
    UPROPERTY(BlueprintReadOnly) TObjectPtr<UND1VaultHUD> HUD;
    UPROPERTY(BlueprintReadOnly) int32 Sigils = 0;
    UPROPERTY(BlueprintReadOnly) float Stamina = 100;
    UPROPERTY(BlueprintReadOnly) float PulseCooldown = 0;
    UPROPERTY(BlueprintReadOnly) float Invulnerability = 0;
    UPROPERTY(BlueprintReadOnly) bool Alerted = false;
    UPROPERTY(BlueprintReadOnly) FString Message;
    UPROPERTY(BlueprintReadOnly) float MessageSeconds = 0;
    UPROPERTY(BlueprintReadOnly) int32 Combo = 0;
    TSet<FIntPoint> Explored;
    UFUNCTION(BlueprintCallable) void StartRun();
    UFUNCTION(BlueprintCallable) void RestartFloor();
    UFUNCTION(BlueprintCallable) void ReturnToTitle();
    UFUNCTION(BlueprintCallable) void ContinueFloor();
    UFUNCTION(BlueprintCallable) void TogglePause();
    UFUNCTION(BlueprintCallable) void ShowControls();
    UFUNCTION(BlueprintCallable) void BackFromControls();
    UFUNCTION(BlueprintCallable) void Collect(EVaultPickup Kind, int32 Points);
    UFUNCTION(BlueprintCallable) void EnterGate();
    UFUNCTION(BlueprintCallable) void TryPulse();
    UFUNCTION(BlueprintCallable) void Notify(const FString& Text, float Duration = 2.5f);
    UFUNCTION(BlueprintCallable) void SetState(EVaultState NewState);
    UFUNCTION(BlueprintPure) bool GateOpen() const;
    UFUNCTION(BlueprintPure) UND1VaultInstance* Run() const;
    UFUNCTION(BlueprintPure) ACharacter* Player() const;
    UFUNCTION(BlueprintPure) FVector NearestObjective() const;
    void Play(USoundBase* Sound, float Volume = 0.7f) const;
private:
    UPROPERTY() TObjectPtr<UAudioComponent> Music;
    float ComboSeconds = 0;
    float AlertSoundCooldown = 0;
    bool ControlsBound = false;
    bool Sprinting = false;
    bool HeroStyled = false;
    EVaultState BeforeControls = EVaultState::Title;
    TArray<TPair<TWeakObjectPtr<AActor>,float>> Stunned;
    void TakeHit(AActor* Enemy);
    void UpdateExploration();
};

UCLASS()
class ND1DUNGEONRUNTIME_API UND1VaultHUD : public UUserWidget
{
    GENERATED_BODY()
public:
    virtual void NativeConstruct() override;
    virtual TSharedRef<SWidget> RebuildWidget() override;
    virtual FReply NativeOnKeyDown(const FGeometry& Geometry, const FKeyEvent& Event) override;
    virtual int32 NativePaint(const FPaintArgs& Args, const FGeometry& Geometry, const FSlateRect& CullingRect, FSlateWindowElementList& Elements, int32 Layer, const FWidgetStyle& Style, bool ParentEnabled) const override;
    void Refresh();
    void Build();
private:
    UPROPERTY() TObjectPtr<UCanvasPanel> Canvas;
    UPROPERTY() TMap<FName,TObjectPtr<UTextBlock>> Labels;
    UPROPERTY() TObjectPtr<UProgressBar> StaminaBar;
    EVaultState BuiltState = EVaultState::Controls;
    AND1VaultGameMode* Mode() const;
    UTextBlock* Label(FName Name, const FString& Text, int32 Size, FLinearColor Color);
    void Button(UVerticalBox* Box, const FString& Text, FName Action, bool Primary = false);
    UFUNCTION() void StartClick();
    UFUNCTION() void RetryClick();
    UFUNCTION() void TitleClick();
    UFUNCTION() void NextClick();
    UFUNCTION() void ResumeClick();
    UFUNCTION() void ControlsClick();
    UFUNCTION() void BackClick();
    UFUNCTION() void QuitClick();
};
