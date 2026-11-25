using UnrealBuildTool;
public class ND1_DungeonGameEditorTarget : TargetRules
{
    public ND1_DungeonGameEditorTarget(TargetInfo Target) : base(Target)
    {
        Type = TargetType.Editor;
        DefaultBuildSettings = BuildSettingsVersion.Latest;
        IncludeOrderVersion = EngineIncludeOrderVersion.Latest;
        ExtraModuleNames.Add("ND1DungeonEditor");
        ExtraModuleNames.Add("ND1DungeonRuntime");
    }
}
