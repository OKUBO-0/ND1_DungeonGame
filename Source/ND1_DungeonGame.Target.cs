using UnrealBuildTool;
public class ND1_DungeonGameTarget : TargetRules
{
    public ND1_DungeonGameTarget(TargetInfo Target) : base(Target)
    {
        Type = TargetType.Game;
        DefaultBuildSettings = BuildSettingsVersion.Latest;
        IncludeOrderVersion = EngineIncludeOrderVersion.Latest;
        ExtraModuleNames.Add("ND1DungeonRuntime");
    }
}
