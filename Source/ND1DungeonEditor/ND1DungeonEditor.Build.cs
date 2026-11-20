using UnrealBuildTool;
public class ND1DungeonEditor : ModuleRules
{
    public ND1DungeonEditor(ReadOnlyTargetRules Target) : base(Target)
    {
        PCHUsage = PCHUsageMode.UseExplicitOrSharedPCHs;
        PrivateDependencyModuleNames.AddRange(new[] {
            "Core", "CoreUObject", "Engine", "UnrealEd", "BlueprintGraph", "Kismet", "KismetCompiler",
            "AnimGraph", "AnimGraphRuntime", "AIModule", "NavigationSystem", "AssetTools", "AudioEditor",
            "BehaviorTreeEditor", "AIGraph", "Slate", "SlateCore", "InputCore", "EnhancedInput", "EngineSettings", "AssetRegistry", "ImageWrapper"
        });
        PrivateIncludePaths.Add(System.IO.Path.Combine(EngineDirectory, "Source/Editor/BehaviorTreeEditor/Classes"));
    }
}
