#include "ND1Vault.h"
#include "AIController.h"
#include "BrainComponent.h"
#include "BehaviorTree/BlackboardComponent.h"
#include "Perception/AIPerceptionComponent.h"
#include "GameFramework/Character.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/PlayerController.h"
#include "Components/AudioComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/SphereComponent.h"
#include "Components/BoxComponent.h"
#include "Components/InputComponent.h"
#include "Components/PointLightComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "Kismet/GameplayStatics.h"
#include "Kismet/KismetSystemLibrary.h"
#include "UObject/ConstructorHelpers.h"
#include "Sound/SoundBase.h"
#include "InputCoreTypes.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"

static FString VaultSaveSlot()
{
    return FParse::Param(FCommandLine::Get(),TEXT("ND1Automation"))?TEXT("EchoVaultRecord_Automation"):TEXT("EchoVaultRecord");
}

void UND1VaultInstance::Init()
{
    Super::Init();
    Record = Cast<UND1VaultSave>(UGameplayStatics::LoadGameFromSlot(VaultSaveSlot(),0));
    if (!Record) Record = Cast<UND1VaultSave>(UGameplayStatics::CreateSaveGameObject(UND1VaultSave::StaticClass()));
}
void UND1VaultInstance::ResetRun()
{
    Score=0; Health=3; Floor=1; Seconds=0; FloorStartScore=0; FloorStartSeconds=0; RunActive=true;
}
void UND1VaultInstance::SaveRecord()
{
    if (!Record) return;
    Record->BestScore=FMath::Max(Record->BestScore,Score);
    if (Record->BestSeconds<=0 || Seconds<Record->BestSeconds) Record->BestSeconds=Seconds;
    ++Record->CompletedRuns;
    UGameplayStatics::SaveGameToSlot(Record,VaultSaveSlot(),0);
}

AND1VaultPickup::AND1VaultPickup()
{
    PrimaryActorTick.bCanEverTick=true;
    Trigger=CreateDefaultSubobject<USphereComponent>(TEXT("PickupTrigger")); SetRootComponent(Trigger);
    Trigger->SetSphereRadius(65); Trigger->SetCollisionProfileName(TEXT("OverlapAllDynamic"));
    Gem=CreateDefaultSubobject<UStaticMeshComponent>(TEXT("Crystal")); Gem->SetupAttachment(Trigger);
    static ConstructorHelpers::FObjectFinder<UStaticMesh> Shape(TEXT("/Engine/BasicShapes/Cone.Cone"));
    Gem->SetStaticMesh(Shape.Object); Gem->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    Gem->SetRelativeScale3D(FVector(0.32f,0.32f,0.65f)); Gem->SetRelativeRotation(FRotator(180,0,0));
    Light=CreateDefaultSubobject<UPointLightComponent>(TEXT("Glow")); Light->SetupAttachment(Trigger);
    Light->SetIntensity(3); Light->SetAttenuationRadius(180); Light->SetCastShadows(false);
    Trigger->OnComponentBeginOverlap.AddDynamic(this,&AND1VaultPickup::Touch);
}
void AND1VaultPickup::BeginPlay()
{
    Super::BeginPlay(); StartLocation=GetActorLocation();
    Light->SetLightColor(Kind==EVaultPickup::Sigil?FLinearColor(1,0.64f,0.14f):Kind==EVaultPickup::Heart?FLinearColor(0.35f,1,0.64f):FLinearColor(0.2f,0.72f,1));
}
void AND1VaultPickup::Tick(float DeltaSeconds)
{
    Super::Tick(DeltaSeconds);
    if (Collected) return;
    const float Time=GetWorld()->GetTimeSeconds();
    SetActorLocation(StartLocation+FVector(0,0,FMath::Sin(Time*2.1f+StartLocation.X*0.01f)*8));
    Gem->AddLocalRotation(FRotator(0,55*DeltaSeconds,0));
}
void AND1VaultPickup::Touch(UPrimitiveComponent*,AActor* Other,UPrimitiveComponent*,int32,bool,const FHitResult&)
{
    if (Collected || !Other || !Other->ActorHasTag(TEXT("Player"))) return;
    auto* Mode=Cast<AND1VaultGameMode>(UGameplayStatics::GetGameMode(this));
    if (!Mode || Mode->State!=EVaultState::Playing) return;
    Collected=true; Mode->Collect(Kind,Points); Destroy();
}

AND1VaultGate::AND1VaultGate()
{
    PrimaryActorTick.bCanEverTick=true;
    Trigger=CreateDefaultSubobject<UBoxComponent>(TEXT("ExitTrigger")); SetRootComponent(Trigger);
    Trigger->SetBoxExtent(FVector(145,145,120)); Trigger->SetCollisionProfileName(TEXT("OverlapAllDynamic"));
    Blocker=CreateDefaultSubobject<UBoxComponent>(TEXT("ClosedCollision")); Blocker->SetupAttachment(Trigger);
    Blocker->SetBoxExtent(FVector(145,145,125)); Blocker->SetCollisionProfileName(TEXT("BlockAll"));
    Bars=CreateDefaultSubobject<UStaticMeshComponent>(TEXT("Gate")); Bars->SetupAttachment(Trigger);
    static ConstructorHelpers::FObjectFinder<UStaticMesh> Cube(TEXT("/Engine/BasicShapes/Cube.Cube"));
    Bars->SetStaticMesh(Cube.Object); Bars->SetRelativeScale3D(FVector(2.1f,0.18f,2.5f)); Bars->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    Light=CreateDefaultSubobject<UPointLightComponent>(TEXT("GateGlow")); Light->SetupAttachment(Trigger);
    Light->SetIntensity(6); Light->SetAttenuationRadius(380); Light->SetLightColor(FLinearColor(1,0.48f,0.12f)); Light->SetCastShadows(false);
    Trigger->OnComponentBeginOverlap.AddDynamic(this,&AND1VaultGate::Touch);
}
void AND1VaultGate::Tick(float DeltaSeconds)
{
    Super::Tick(DeltaSeconds);
    auto* Mode=Cast<AND1VaultGameMode>(UGameplayStatics::GetGameMode(this));
    if (!Mode) return;
    const bool Open=Mode->GateOpen();
    if (Open!=WasOpen)
    {
        WasOpen=Open; Blocker->SetCollisionEnabled(Open?ECollisionEnabled::NoCollision:ECollisionEnabled::QueryAndPhysics);
        Bars->SetVisibility(!Open); Light->SetLightColor(Open?FLinearColor(0.25f,1,0.75f):FLinearColor(1,0.48f,0.12f));
        if (Open) { Mode->Play(Mode->Audio?Mode->Audio->Gate:nullptr); Mode->Notify(TEXT("GATE UNSEALED  /  Follow the green beacon"),4); }
    }
}
void AND1VaultGate::Touch(UPrimitiveComponent*,AActor* Other,UPrimitiveComponent*,int32,bool,const FHitResult&)
{
    if (!Other || !Other->ActorHasTag(TEXT("Player"))) return;
    if (auto* Mode=Cast<AND1VaultGameMode>(UGameplayStatics::GetGameMode(this)))
    {
        if (Mode->GateOpen()) Mode->EnterGate();
        else Mode->Notify(FString::Printf(TEXT("THE GATE IS SEALED  /  Sigils %d / %d"),Mode->Sigils,Mode->LevelInfo?Mode->LevelInfo->RequiredSigils:3));
    }
}

AND1VaultPulse::AND1VaultPulse()
{
    PrimaryActorTick.bCanEverTick=true;
    Shell=CreateDefaultSubobject<UStaticMeshComponent>(TEXT("EchoShell")); SetRootComponent(Shell);
    static ConstructorHelpers::FObjectFinder<UStaticMesh> Sphere(TEXT("/Engine/BasicShapes/Sphere.Sphere"));
    Shell->SetStaticMesh(Sphere.Object); Shell->SetCollisionEnabled(ECollisionEnabled::NoCollision); Shell->SetCastShadow(false);
    SetActorScale3D(FVector(0.1f));
}
void AND1VaultPulse::Tick(float DeltaSeconds)
{
    Super::Tick(DeltaSeconds); Age+=DeltaSeconds;
    if (PulseMaterial) Shell->SetMaterial(0,PulseMaterial);
    SetActorScale3D(FVector(0.3f+Age*12,0.3f+Age*12,0.08f));
    if (Age>0.6f) Destroy();
}

AND1VaultGameMode::AND1VaultGameMode() { PrimaryActorTick.bCanEverTick=true; }
UND1VaultInstance* AND1VaultGameMode::Run() const { return Cast<UND1VaultInstance>(GetGameInstance()); }
ACharacter* AND1VaultGameMode::Player() const { return UGameplayStatics::GetPlayerCharacter(this,0); }
bool AND1VaultGameMode::GateOpen() const { return Sigils>=(LevelInfo?LevelInfo->RequiredSigils:3); }
void AND1VaultGameMode::Play(USoundBase* Sound,float Volume) const { if (Sound) UGameplayStatics::PlaySound2D(this,Sound,Volume); }
void AND1VaultGameMode::BeginPlay()
{
    Super::BeginPlay();
    for (TActorIterator<AND1VaultLevel> It(GetWorld());It;++It) { LevelInfo=*It; break; }
    if (auto* PC=UGameplayStatics::GetPlayerController(this,0))
    {
        HUD=CreateWidget<UND1VaultHUD>(PC,UND1VaultHUD::StaticClass()); HUD->AddToViewport(20);
    }
    if (LevelInfo && LevelInfo->Music)
    {
        Music=UGameplayStatics::SpawnSound2D(this,LevelInfo->Music,0.25f,1,0,nullptr,false,false);
    }
    if (Run()) Run()->Floor=LevelInfo?LevelInfo->FloorNumber:1;
    SetState(Run() && Run()->RunActive?EVaultState::Playing:EVaultState::Title);
    if (State==EVaultState::Playing) Notify(TEXT("RECOVER 3 SIGILS  /  Then reach the gate"),4);
}
void AND1VaultGameMode::EndPlay(const EEndPlayReason::Type Reason)
{
    if (Music) Music->Stop();
    if (Player() && Player()->GetMesh()) Player()->GetMesh()->SetVisibility(true);
    Super::EndPlay(Reason);
}
void AND1VaultGameMode::SetState(EVaultState NewState)
{
    State=NewState;
    auto* PC=UGameplayStatics::GetPlayerController(this,0);
    const bool Playing=State==EVaultState::Playing;
    if (PC)
    {
        PC->ResetIgnoreMoveInput(); PC->ResetIgnoreLookInput();
        PC->bShowMouseCursor=!Playing;
        if (Playing) { FInputModeGameOnly Input; PC->SetInputMode(Input); }
        else
        {
            PC->SetIgnoreMoveInput(true); PC->SetIgnoreLookInput(true);
            FInputModeUIOnly Input; if (HUD) Input.SetWidgetToFocus(HUD->TakeWidget()); PC->SetInputMode(Input);
        }
    }
    if (!Playing && Player()) Player()->GetCharacterMovement()->StopMovementImmediately();
    UGameplayStatics::SetGamePaused(this,!Playing);
    if (HUD) { HUD->Build(); if (!Playing) HUD->SetKeyboardFocus(); }
}
void AND1VaultGameMode::StartRun()
{
    Play(Audio?Audio->Confirm:nullptr); if (Run()) Run()->ResetRun();
    UGameplayStatics::SetGamePaused(this,false); UGameplayStatics::OpenLevel(this,TEXT("L_Vault01"));
}
void AND1VaultGameMode::RestartFloor()
{
    if (Run()) { Run()->Score=Run()->FloorStartScore; Run()->Seconds=Run()->FloorStartSeconds; Run()->Health=3; Run()->RunActive=true; }
    Play(Audio?Audio->Confirm:nullptr); UGameplayStatics::SetGamePaused(this,false);
    UGameplayStatics::OpenLevel(this,LevelInfo && LevelInfo->FloorNumber==2?TEXT("L_Vault02"):TEXT("L_Vault01"));
}
void AND1VaultGameMode::ReturnToTitle()
{
    if (Run()) Run()->RunActive=false;
    UGameplayStatics::SetGamePaused(this,false); UGameplayStatics::OpenLevel(this,TEXT("L_Vault01"));
}
void AND1VaultGameMode::ContinueFloor()
{
    if (!LevelInfo || !Run()) return;
    Run()->FloorStartScore=Run()->Score; Run()->FloorStartSeconds=Run()->Seconds; Run()->Health=FMath::Min(3,Run()->Health+1);
    Play(Audio?Audio->Confirm:nullptr); UGameplayStatics::SetGamePaused(this,false); UGameplayStatics::OpenLevel(this,LevelInfo->NextLevel);
}
void AND1VaultGameMode::TogglePause()
{
    if (State==EVaultState::Playing) SetState(EVaultState::Paused);
    else if (State==EVaultState::Paused) SetState(EVaultState::Playing);
}
void AND1VaultGameMode::ShowControls() { BeforeControls=State; SetState(EVaultState::Controls); }
void AND1VaultGameMode::BackFromControls() { SetState(BeforeControls); }
void AND1VaultGameMode::Notify(const FString& Text,float Duration) { Message=Text; MessageSeconds=Duration; }
void AND1VaultGameMode::Collect(EVaultPickup Kind,int32 Points)
{
    if (State!=EVaultState::Playing || !Run()) return;
    if (Kind==EVaultPickup::Sigil)
    {
        ++Sigils; Run()->Score+=250; Play(Audio?Audio->Sigil:nullptr);
        Notify(FString::Printf(TEXT("SIGIL RECOVERED  %d / %d   +250"),Sigils,LevelInfo?LevelInfo->RequiredSigils:3));
    }
    else if (Kind==EVaultPickup::Heart)
    {
        Run()->Health=FMath::Min(3,Run()->Health+1); Run()->Score+=25;
        Play(Audio?Audio->Pickup:nullptr); Notify(TEXT("VITALITY RESTORED   +25"));
    }
    else
    {
        Combo=ComboSeconds>0?FMath::Min(Combo+1,5):1; ComboSeconds=5;
        const int32 Gain=Points*Combo; Run()->Score+=Gain; Play(Audio?Audio->Pickup:nullptr);
        Notify(FString::Printf(TEXT("RELIC FOUND   +%d    CHAIN x%d"),Gain,Combo),1.4f);
    }
}
void AND1VaultGameMode::EnterGate()
{
    if (State!=EVaultState::Playing || !GateOpen() || !Run()) return;
    const int32 Bonus=FMath::Max(0,1200-FMath::RoundToInt((Run()->Seconds-Run()->FloorStartSeconds)*5));
    Run()->Score+=Bonus+Run()->Health*100;
    Play(Audio?Audio->Clear:nullptr);
    if (LevelInfo && LevelInfo->FloorNumber>=2) { Run()->SaveRecord(); Run()->RunActive=false; SetState(EVaultState::Victory); }
    else SetState(EVaultState::FloorClear);
}
void AND1VaultGameMode::TryPulse()
{
    if (State!=EVaultState::Playing || !Player() || Stamina<35 || PulseCooldown>0) return;
    Stamina-=35; PulseCooldown=6;
    auto* Effect=GetWorld()->SpawnActor<AND1VaultPulse>(Player()->GetActorLocation()-FVector(0,0,75),FRotator::ZeroRotator);
    if (Effect) Effect->PulseMaterial=PulseMaterial;
    int32 Count=0;
    for (TActorIterator<AAIController> It(GetWorld());It;++It)
    {
        APawn* Pawn=It->GetPawn();
        if (Pawn && FVector::Dist2D(Pawn->GetActorLocation(),Player()->GetActorLocation())<430 && It->BrainComponent)
        {
            It->BrainComponent->PauseLogic(TEXT("Echo pulse")); Stunned.Emplace(TWeakObjectPtr<AActor>(Pawn),2.3f); ++Count;
            if (auto* Character=Cast<ACharacter>(Pawn)) Character->GetCharacterMovement()->DisableMovement();
        }
    }
    Play(Audio?Audio->Pulse:nullptr); Notify(FString::Printf(TEXT("ECHO PULSE  /  %d sentinel%s stunned"),Count,Count==1?TEXT(""):TEXT("s")),1.5f);
}
void AND1VaultGameMode::TakeHit(AActor* Enemy)
{
    if (!Run() || !Player()) return;
    --Run()->Health; Invulnerability=1.8f; Combo=0; ComboSeconds=0;
    FVector Away=Player()->GetActorLocation()-Enemy->GetActorLocation(); Away.Z=0; Away.Normalize();
    Player()->LaunchCharacter(Away*650+FVector(0,0,170),true,true);
    Play(Audio?Audio->Hit:nullptr); Notify(TEXT("SENTINEL STRIKE  /  Shift to sprint, Space to pulse"),2);
    if (Run()->Health<=0) { Run()->RunActive=false; SetState(EVaultState::GameOver); }
}
void AND1VaultGameMode::UpdateExploration()
{
    if (!LevelInfo || !Player()) return;
    const FVector Relative=Player()->GetActorLocation()-LevelInfo->Origin;
    const int32 X=FMath::RoundToInt(Relative.X/LevelInfo->CellSize),Y=FMath::RoundToInt(Relative.Y/LevelInfo->CellSize);
    for (int32 DY=-2;DY<=2;++DY) for (int32 DX=-2;DX<=2;++DX)
        if (DX*DX+DY*DY<=6) Explored.Add(FIntPoint(X+DX,Y+DY));
}
FVector AND1VaultGameMode::NearestObjective() const
{
    if (!Player()) return FVector::ZeroVector;
    FVector Target=Player()->GetActorLocation(); float Best=TNumericLimits<float>::Max();
    if (!GateOpen())
    {
        for (TActorIterator<AND1VaultPickup> It(GetWorld());It;++It) if (It->Kind==EVaultPickup::Sigil)
        {
            const float Distance=FVector::DistSquared2D(Player()->GetActorLocation(),It->GetActorLocation());
            if (Distance<Best) { Best=Distance; Target=It->GetActorLocation(); }
        }
    }
    else for (TActorIterator<AND1VaultGate> It(GetWorld());It;++It) { Target=It->GetActorLocation(); break; }
    return Target;
}
void AND1VaultGameMode::Tick(float DeltaSeconds)
{
    Super::Tick(DeltaSeconds);
    if (State!=EVaultState::Playing || !Player() || !Run()) return;
    // The default pawn may be spawned after GameMode::BeginPlay.
    if (!HeroStyled && HeroMaterial && Player()->GetMesh()->GetSkeletalMeshAsset() && Player()->GetMesh()->GetSkeletalMeshAsset()->GetFName()==TEXT("SK_CubeMan"))
    {
        for (int32 Index=0;Index<Player()->GetMesh()->GetNumMaterials();++Index) Player()->GetMesh()->SetMaterial(Index,HeroMaterial);
        HeroStyled=true;
    }
    auto* PC=UGameplayStatics::GetPlayerController(this,0);
    if (!ControlsBound && PC && PC->InputComponent)
    {
        PC->InputComponent->BindKey(EKeys::SpaceBar,IE_Pressed,this,&AND1VaultGameMode::TryPulse);
        PC->InputComponent->BindKey(EKeys::P,IE_Pressed,this,&AND1VaultGameMode::TogglePause);
        PC->InputComponent->BindKey(EKeys::Escape,IE_Pressed,this,&AND1VaultGameMode::TogglePause);
        ControlsBound=true;
    }
    Run()->Seconds+=DeltaSeconds;
    PulseCooldown=FMath::Max(0.0f,PulseCooldown-DeltaSeconds); Invulnerability=FMath::Max(0.0f,Invulnerability-DeltaSeconds);
    MessageSeconds=FMath::Max(0.0f,MessageSeconds-DeltaSeconds); ComboSeconds=FMath::Max(0.0f,ComboSeconds-DeltaSeconds);
    AlertSoundCooldown=FMath::Max(0.0f,AlertSoundCooldown-DeltaSeconds);
    if (ComboSeconds<=0) Combo=0;
    const bool Moving=Player()->GetVelocity().Size2D()>30;
    Sprinting=PC && PC->IsInputKeyDown(EKeys::LeftShift) && Stamina>1 && Moving;
    Stamina=FMath::Clamp(Stamina+(Sprinting?-30.0f:18.0f)*DeltaSeconds,0.0f,100.0f);
    Player()->GetCharacterMovement()->MaxWalkSpeed=Sprinting?850.0f:600.0f;
    Player()->GetMesh()->SetVisibility(Invulnerability<=0 || FMath::Fmod(Invulnerability,0.22f)<0.11f);
    if (State!=EVaultState::Playing) return;
    for (int32 Index=Stunned.Num()-1;Index>=0;--Index)
    {
        Stunned[Index].Value-=DeltaSeconds;
        if (!Stunned[Index].Key.IsValid() || Stunned[Index].Value<=0)
        {
            if (auto* Pawn=Cast<APawn>(Stunned[Index].Key.Get()))
            {
                if (auto* Character=Cast<ACharacter>(Pawn)) Character->GetCharacterMovement()->SetMovementMode(MOVE_Walking);
                if (auto* AI=Cast<AAIController>(Pawn->GetController())) if (AI->BrainComponent) AI->BrainComponent->ResumeLogic(TEXT("Echo pulse ended"));
            }
            Stunned.RemoveAt(Index);
        }
    }
    bool AnyChase=false;
    for (TActorIterator<AAIController> It(GetWorld());It;++It)
    {
        APawn* Enemy=It->GetPawn(); if (!Enemy) continue;
        if (auto* Blackboard=It->GetBlackboardComponent()) AnyChase|=Blackboard->GetValueAsBool(TEXT("IsChaseMode"));
        if (Invulnerability<=0 && FVector::Dist2D(Player()->GetActorLocation(),Enemy->GetActorLocation())<110 && FMath::Abs(Player()->GetActorLocation().Z-Enemy->GetActorLocation().Z)<120)
        {
            bool IsStunned=false; for (const auto& Item:Stunned) if (Item.Key.Get()==Enemy) IsStunned=true;
            if (!IsStunned) TakeHit(Enemy);
        }
    }
    if (AnyChase && !Alerted && AlertSoundCooldown<=0) { Play(Audio?Audio->Alert:nullptr,0.45f); AlertSoundCooldown=5; }
    Alerted=AnyChase;
    if (Music) Music->SetVolumeMultiplier(Alerted?0.32f:0.22f);
    UpdateExploration();
    if (HUD) HUD->Refresh();
}
