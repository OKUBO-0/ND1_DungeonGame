#include "ND1DungeonEditorLibrary.h"
#include "Editor.h"
#include "EdGraph/EdGraph.h"
#include "EdGraph/EdGraphNode.h"
#include "EdGraph/EdGraphSchema.h"
#include "Kismet2/BlueprintEditorUtils.h"
#include "Engine/Blueprint.h"
#include "Engine/Brush.h"
#include "Components/BrushComponent.h"
#include "Model.h"
#include "Builders/CubeBuilder.h"
#include "NavMesh/NavMeshBoundsVolume.h"
#include "NavigationSystem.h"
#include "Sound/SoundCue.h"
#include "Sound/SoundWave.h"
#include "Sound/SoundNodeRandom.h"
#include "Sound/SoundNodeWavePlayer.h"
#include "SoundCueEditorUtilities.h"
#include "BehaviorTree/BehaviorTree.h"
#include "BehaviorTree/BlackboardData.h"
#include "BehaviorTree/Composites/BTComposite_Selector.h"
#include "BehaviorTree/Composites/BTComposite_Sequence.h"
#include "BehaviorTree/Decorators/BTDecorator_Blackboard.h"
#include "BehaviorTree/Tasks/BTTask_MoveTo.h"
#include "BehaviorTree/Tasks/BTTask_Wait.h"
#include "BehaviorTreeGraph.h"
#include "BehaviorTreeGraphNode_Composite.h"
#include "BehaviorTreeGraphNode_Task.h"
#include "BehaviorTreeGraphNode_Decorator.h"
#include "BehaviorTreeGraphNode_Root.h"
#include "EdGraphSchema_BehaviorTree.h"
#include "Kismet2/EnumEditorUtils.h"
#include "Engine/UserDefinedEnum.h"
#include "AssetRegistry/AssetRegistryModule.h"
#include "ImageUtils.h"
#include "UnrealClient.h"
#include "Engine/GameViewportClient.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Engine/SkeletalMesh.h"
#include "Animation/Skeleton.h"

UEdGraphNode* UND1DungeonEditorLibrary::SpawnGraphNode(UEdGraph* Graph, TSubclassOf<UEdGraphNode> NodeClass, FVector2D Position)
{
    if (!Graph || !NodeClass) return nullptr;
    Graph->Modify();
    UEdGraphNode* Node = NewObject<UEdGraphNode>(Graph, NodeClass, NAME_None, RF_Transactional);
    Graph->AddNode(Node, true, false);
    Node->CreateNewGuid();
    Node->NodePosX = Position.X;
    Node->NodePosY = Position.Y;
    Node->PostPlacedNewNode();
    Node->AllocateDefaultPins();
    Graph->NotifyGraphChanged();
    Graph->MarkPackageDirty();
    return Node;
}

TArray<UEdGraphNode*> UND1DungeonEditorLibrary::GetGraphNodes(UEdGraph* Graph)
{
    TArray<UEdGraphNode*> Result;
    if (Graph) for (UEdGraphNode* Node : Graph->Nodes) if (Node) Result.Add(Node);
    return Result;
}

bool UND1DungeonEditorLibrary::ConnectGraphNodes(UEdGraphNode* From, FName OutputPin, UEdGraphNode* To, FName InputPin)
{
    if (!From || !To || From->GetGraph() != To->GetGraph()) return false;
    UEdGraphPin* A = nullptr; UEdGraphPin* B = nullptr;
    for (UEdGraphPin* Pin : From->Pins) if (Pin->Direction == EGPD_Output && (OutputPin.IsNone() || Pin->PinName == OutputPin)) { A = Pin; break; }
    for (UEdGraphPin* Pin : To->Pins) if (Pin->Direction == EGPD_Input && (InputPin.IsNone() || Pin->PinName == InputPin)) { B = Pin; break; }
    if (!A || !B) return false;
    return From->GetGraph()->GetSchema()->TryCreateConnection(A, B);
}

void UND1DungeonEditorLibrary::RenameGraphNode(UEdGraphNode* Node, const FString& Name)
{
    if (Node) { Node->Modify(); Node->OnRenameNode(Name); Node->MarkPackageDirty(); }
}

void UND1DungeonEditorLibrary::MarkBlueprintChanged(UBlueprint* Blueprint)
{
    if (Blueprint) FBlueprintEditorUtils::MarkBlueprintAsModified(Blueprint);
}

AActor* UND1DungeonEditorLibrary::AddBoxBrush(const FString& Label, FVector Location, FVector Size, bool bSubtractive, bool bNavigationBounds)
{
    UWorld* World = GEditor ? GEditor->GetEditorWorldContext().World() : nullptr;
    if (!World) return nullptr;
    UClass* Class = bNavigationBounds ? ANavMeshBoundsVolume::StaticClass() : ABrush::StaticClass();
    ABrush* Brush = World->SpawnActor<ABrush>(Class, Location, FRotator::ZeroRotator);
    Brush->SetActorLabel(Label);
    Brush->BrushType = bSubtractive ? Brush_Subtract : Brush_Add;
    Brush->Brush = NewObject<UModel>(Brush, NAME_None, RF_Transactional);
    Brush->Brush->Initialize(Brush, true);
    Brush->GetBrushComponent()->Brush = Brush->Brush;
    Brush->BrushBuilder = NewObject<UCubeBuilder>(Brush, NAME_None, RF_Transactional);
    UCubeBuilder* Builder = CastChecked<UCubeBuilder>(Brush->BrushBuilder);
    Builder->X = Size.X; Builder->Y = Size.Y; Builder->Z = Size.Z;
    Builder->Build(World, Brush);
    Brush->GetBrushComponent()->BuildSimpleBrushCollision();
    Brush->SetActorLocation(Location);
    Brush->PostEditChange();
    Brush->MarkPackageDirty();
    return Brush;
}

void UND1DungeonEditorLibrary::RebuildLevel()
{
    if (!GEditor) return;
    UWorld* World = GEditor->GetEditorWorldContext().World();
    GEditor->Exec(World, TEXT("MAP REBUILD"));
    if (UNavigationSystemV1* Nav = FNavigationSystem::GetCurrent<UNavigationSystemV1>(World)) Nav->Build();
    if (World) World->MarkPackageDirty();
}

USoundCue* UND1DungeonEditorLibrary::BuildFootstepCue(const TArray<USoundWave*>& Waves)
{
    if (Waves.IsEmpty()) return nullptr;
    UPackage* Package = CreatePackage(TEXT("/Game/SC_Footsteps"));
    USoundCue* Cue = FindObject<USoundCue>(Package, TEXT("SC_Footsteps"));
    if (Cue) return Cue;
    Cue = NewObject<USoundCue>(Package, TEXT("SC_Footsteps"), RF_Public | RF_Standalone | RF_Transactional);
    USoundNodeRandom* Random = Cue->ConstructSoundNode<USoundNodeRandom>();
    Random->ChildNodes.Reset(); Random->Weights.Reset();
    for (USoundWave* Wave : Waves)
    {
        USoundNodeWavePlayer* Player = Cue->ConstructSoundNode<USoundNodeWavePlayer>();
        Player->SetSoundWave(Wave);
        Random->ChildNodes.Add(Player); Random->Weights.Add(1.0f);
    }
    Random->bRandomizeWithoutReplacement = true;
    Cue->FirstNode = Random;
    Cue->VolumeMultiplier = 0.2f;
    Random->GetGraphNode()->ReconstructNode();
    Random->GetGraphNode()->NodePosX = -250;
    int32 SoundRow = 0;
    for (USoundNode* Child : Random->ChildNodes)
    {
        Child->GetGraphNode()->NodePosX = -650;
        Child->GetGraphNode()->NodePosY = SoundRow++ * 180;
    }
    Cue->LinkGraphNodesFromSoundNodes();
    Cue->PostEditChange(); Cue->MarkPackageDirty();
    FAssetRegistryModule::AssetCreated(Cue);
    return Cue;
}

bool UND1DungeonEditorLibrary::BuildSlimeTree(UBehaviorTree* Tree, UBlackboardData* Blackboard, UClass* PatrolTaskClass, UClass* ChaseTaskClass)
{
    if (!Tree || !Blackboard || !PatrolTaskClass) return false;
    Tree->Modify();
    Tree->BlackboardAsset = Blackboard;
    UBehaviorTreeGraph* Graph = NewObject<UBehaviorTreeGraph>(Tree, NAME_None, RF_Transactional);
    Graph->Schema = UEdGraphSchema_BehaviorTree::StaticClass();
    Tree->BTGraph = Graph;
    Graph->GetSchema()->CreateDefaultNodesForGraph(*Graph);
    auto Composite = [&](UClass* Class, const TCHAR* Name, int X, int Y)
    {
        UBehaviorTreeGraphNode_Composite* Node = CastChecked<UBehaviorTreeGraphNode_Composite>(SpawnGraphNode(Graph, UBehaviorTreeGraphNode_Composite::StaticClass(), FVector2D(X,Y)));
        UBTCompositeNode* Instance = NewObject<UBTCompositeNode>(Tree, Class);
        Instance->NodeName = Name; Node->NodeInstance = Instance; return Node;
    };
    auto Task = [&](UClass* Class, int X, int Y)
    {
        UBehaviorTreeGraphNode_Task* Node = CastChecked<UBehaviorTreeGraphNode_Task>(SpawnGraphNode(Graph, UBehaviorTreeGraphNode_Task::StaticClass(), FVector2D(X,Y)));
        Node->NodeInstance = NewObject<UBTTaskNode>(Tree, Class); return Node;
    };
    auto Link = [&](UEdGraphNode* A, UEdGraphNode* B) { return ConnectGraphNodes(A, NAME_None, B, NAME_None); };
    UBehaviorTreeGraphNode_Composite* Root = Composite(UBTComposite_Selector::StaticClass(), TEXT("AIRoot"), 0, 200);
    UBehaviorTreeGraphNode_Composite* Patrol = Composite(UBTComposite_Sequence::StaticClass(), TEXT("Patrol"), 400, 400);
    Link(Graph->Nodes[0], Root);
    auto Wait = Task(UBTTask_Wait::StaticClass(), 100, 650);
    CastChecked<UBTTask_Wait>(Wait->NodeInstance)->WaitTime = 3.0f;
    CastChecked<UBTTask_Wait>(Wait->NodeInstance)->RandomDeviation = 1.0f;
    auto Find = Task(PatrolTaskClass, 400, 650);
    auto Move = Task(UBTTask_MoveTo::StaticClass(), 700, 650);
    if (FProperty* Key = Move->NodeInstance->GetClass()->FindPropertyByName(TEXT("BlackboardKey")))
        Key->ImportText_Direct(TEXT("(SelectedKeyName=PatrolLocation)"), Key->ContainerPtrToValuePtr<void>(Move->NodeInstance), Move->NodeInstance, PPF_None);
    Link(Patrol, Wait); Link(Patrol, Find); Link(Patrol, Move);
    if (ChaseTaskClass)
    {
    UBehaviorTreeGraphNode_Composite* Chase = Composite(UBTComposite_Sequence::StaticClass(), TEXT("ChasePlayer"), -400, 400);
    Link(Root, Chase);
    auto ChaseMode = Task(ChaseTaskClass, -550, 650);
    auto ChaseMove = Task(UBTTask_MoveTo::StaticClass(), -250, 650);
    Link(Chase, ChaseMode); Link(Chase, ChaseMove);
    UBTTask_MoveTo* ChaseInstance = CastChecked<UBTTask_MoveTo>(ChaseMove->NodeInstance);
    if (FProperty* Key = ChaseInstance->GetClass()->FindPropertyByName(TEXT("BlackboardKey")))
        Key->ImportText_Direct(TEXT("(SelectedKeyName=TargetActor)"), Key->ContainerPtrToValuePtr<void>(ChaseInstance), ChaseInstance, PPF_None);
    UBehaviorTreeGraphNode_Decorator* Decorator = NewObject<UBehaviorTreeGraphNode_Decorator>(Graph, NAME_None, RF_Transactional);
    UBTDecorator_Blackboard* Condition = NewObject<UBTDecorator_Blackboard>(Tree);
    // Blackboard condition is configured through exported property text because these fields are protected.
    FProperty* KeyProperty = Condition->GetClass()->FindPropertyByName(TEXT("BlackboardKey"));
    if (KeyProperty) KeyProperty->ImportText_Direct(TEXT("(SelectedKeyName=IsChaseMode)"), KeyProperty->ContainerPtrToValuePtr<void>(Condition), Condition, PPF_None);
    FProperty* AbortProperty = Condition->GetClass()->FindPropertyByName(TEXT("FlowAbortMode"));
    if (AbortProperty) AbortProperty->ImportText_Direct(TEXT("Both"), AbortProperty->ContainerPtrToValuePtr<void>(Condition), Condition, PPF_None);
    Decorator->NodeInstance = Condition;
    Chase->AddSubNode(Decorator, Graph);
    }
    Link(Root, Patrol);
    Graph->UpdateAsset(0);
    Tree->PostEditChange(); Tree->MarkPackageDirty();
    return Tree->RootNode != nullptr;
}

UUserDefinedEnum* UND1DungeonEditorLibrary::CreateMoveModeEnum()
{
    UPackage* Package = CreatePackage(TEXT("/Game/E_MoveMode"));
    if (UUserDefinedEnum* Existing = FindObject<UUserDefinedEnum>(Package,TEXT("E_MoveMode"))) return Existing;
    UUserDefinedEnum* Enum = CastChecked<UUserDefinedEnum>(FEnumEditorUtils::CreateUserDefinedEnum(Package,TEXT("E_MoveMode"),RF_Public|RF_Standalone|RF_Transactional));
    FEnumEditorUtils::AddNewEnumeratorForUserDefinedEnum(Enum);
    FEnumEditorUtils::AddNewEnumeratorForUserDefinedEnum(Enum);
    FEnumEditorUtils::SetEnumeratorDisplayName(Enum,0,FText::FromString(TEXT("Walk")));
    FEnumEditorUtils::SetEnumeratorDisplayName(Enum,1,FText::FromString(TEXT("Run")));
    FAssetRegistryModule::AssetCreated(Enum);
    Enum->MarkPackageDirty();
    return Enum;
}

FString UND1DungeonEditorLibrary::CapturePlayViewport()
{
    if (!GEditor || !GEditor->PlayWorld || !GEditor->PlayWorld->GetGameViewport()) return FString();
    FViewport* Viewport = GEditor->PlayWorld->GetGameViewport()->Viewport;
    if (!Viewport) return FString();
    TArray<FColor> Pixels;
    if (!GetViewportScreenShot(Viewport,Pixels)) return FString();
    for (FColor& Color : Pixels) Color.A=255;
    FIntPoint Size=Viewport->GetSizeXY();
    TArray<uint8> Png;
    FImageUtils::CompressImageArray(Size.X,Size.Y,Pixels,Png);
    FString Path=FPaths::ConvertRelativePathToFull(FPaths::ProjectSavedDir()/TEXT("Verification/gameplay.png"));
    IFileManager::Get().MakeDirectory(*FPaths::GetPath(Path),true);
    return FFileHelper::SaveArrayToFile(Png,*Path) ? Path : FString();
}

FEdGraphPinType UND1DungeonEditorLibrary::EnumPinType(UEnum* Enum)
{
    FEdGraphPinType Type;
    Type.PinCategory=TEXT("byte");
    Type.PinSubCategoryObject=Enum;
    return Type;
}

bool UND1DungeonEditorLibrary::AssignMeshSkeleton(USkeletalMesh* Mesh, USkeleton* Skeleton)
{
    if (!Mesh || !Skeleton) return false;
    Mesh->Modify();
    if (!Skeleton->MergeAllBonesToBoneTree(Mesh)) return false;
    Mesh->SetSkeleton(Skeleton);
    Mesh->PostEditChange();
    Mesh->MarkPackageDirty();
    return true;
}
