using UnrealBuildTool;
public class ND1DungeonRuntime : ModuleRules
{
    public ND1DungeonRuntime(ReadOnlyTargetRules Target) : base(Target)
    {
        PCHUsage = PCHUsageMode.UseExplicitOrSharedPCHs;
        PublicDependencyModuleNames.AddRange(new[] { "Core", "CoreUObject", "Engine", "InputCore", "UMG", "Slate", "SlateCore", "AIModule", "NavigationSystem" });
    }
}
