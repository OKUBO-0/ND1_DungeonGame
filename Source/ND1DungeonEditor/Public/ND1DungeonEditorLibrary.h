#pragma once
#include "CoreMinimal.h"
#include "Kismet/BlueprintFunctionLibrary.h"
#include "EdGraph/EdGraphPin.h"
#include "ND1DungeonEditorLibrary.generated.h"

class UEdGraph;
class UEdGraphNode;
class UBlueprint;
class USoundCue;
class USoundWave;
class UBehaviorTree;
class UBlackboardData;
class UUserDefinedEnum;
class USkeletalMesh;
class USkeleton;

/** Editor-only graph primitives used by the project's MCP lesson tools. */
UCLASS()
class ND1DUNGEONEDITOR_API UND1DungeonEditorLibrary : public UBlueprintFunctionLibrary
{
    GENERATED_BODY()
public:
    UFUNCTION(BlueprintCallable, Category="ND1|Editor")
    static UEdGraphNode* SpawnGraphNode(UEdGraph* Graph, TSubclassOf<UEdGraphNode> NodeClass, FVector2D Position);
    UFUNCTION(BlueprintCallable, Category="ND1|Editor")
    static TArray<UEdGraphNode*> GetGraphNodes(UEdGraph* Graph);
    UFUNCTION(BlueprintCallable, Category="ND1|Editor")
    static bool ConnectGraphNodes(UEdGraphNode* From, FName OutputPin, UEdGraphNode* To, FName InputPin);
    UFUNCTION(BlueprintCallable, Category="ND1|Editor")
    static void RenameGraphNode(UEdGraphNode* Node, const FString& Name);
    UFUNCTION(BlueprintCallable, Category="ND1|Editor")
    static void MarkBlueprintChanged(UBlueprint* Blueprint);
    UFUNCTION(BlueprintCallable, Category="ND1|Editor")
    static AActor* AddBoxBrush(const FString& Label, FVector Location, FVector Size, bool bSubtractive, bool bNavigationBounds);
    UFUNCTION(BlueprintCallable, Category="ND1|Editor")
    static void RebuildLevel();
    UFUNCTION(BlueprintCallable, Category="ND1|Editor")
    static USoundCue* BuildFootstepCue(const TArray<USoundWave*>& Waves);
    UFUNCTION(BlueprintCallable, Category="ND1|Editor")
    static bool BuildSlimeTree(UBehaviorTree* Tree, UBlackboardData* Blackboard, UClass* PatrolTaskClass, UClass* ChaseTaskClass);
    UFUNCTION(BlueprintCallable, Category="ND1|Editor")
    static UUserDefinedEnum* CreateMoveModeEnum();
    UFUNCTION(BlueprintCallable, Category="ND1|Editor")
    static FEdGraphPinType EnumPinType(UEnum* Enum);
    UFUNCTION(BlueprintCallable, Category="ND1|Editor")
    static bool AssignMeshSkeleton(USkeletalMesh* Mesh, USkeleton* Skeleton);
    UFUNCTION(BlueprintCallable, Category="ND1|Editor")
    static FString CapturePlayViewport();
};
