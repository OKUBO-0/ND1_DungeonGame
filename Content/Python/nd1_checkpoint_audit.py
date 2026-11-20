"""Check a reconstructed lesson branch after reopening the editor."""
import unreal
from editor_toolset.toolsets.blueprint import BlueprintTools
from editor_toolset.toolsets.actor import ActorTools


def build():
    exists = unreal.EditorAssetLibrary.does_asset_exist
    stage = '02-04' if exists('/Game/BTTask_ChangeToChaseMode') else '02-03' if exists('/Game/BP_Slime') else '02-02' if exists('/Game/ABP_CubeMan') else '02-01'
    checks = []
    def check(name, condition):
        checks.append({'name': name, 'pass': bool(condition)})
    paths = unreal.EditorAssetLibrary.list_assets('/Game', True, False)
    registry = unreal.AssetRegistryHelpers.get_asset_registry()
    missing = []
    options = unreal.AssetRegistryDependencyOptions(include_soft_package_references=True, include_hard_package_references=True)
    for path in paths:
        obj = unreal.load_asset(path)
        if isinstance(obj, unreal.Blueprint):
            BlueprintTools.compile_blueprint(obj)
            check(obj.get_name() + ' compiles', True)
        for dep in registry.get_dependencies(path.split('.')[0], options):
            if str(dep).startswith('/Game/') and not exists(str(dep)):
                missing.append({'asset': path, 'dependency': str(dep)})
    check('all project dependencies exist', not missing)
    player = unreal.load_asset('/Game/BP_CubeMan')
    cdo = BlueprintTools.get_default_object(player)
    mesh = next(c for c in ActorTools.get_components(cdo) if isinstance(c, unreal.SkeletalMeshComponent))
    check('player skeleton exists', mesh.get_editor_property('skeletal_mesh').get_editor_property('skeleton') is not None)
    check('animation assignment matches lesson', bool(mesh.get_editor_property('anim_class')) == (stage != '02-01'))
    check('Player tag matches lesson', ('Player' in [str(t) for t in cdo.get_editor_property('tags')]) == (stage == '02-04'))
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
    has_slime = any(a.get_class().get_name() == 'BP_Slime_C' for a in actors)
    check('level Slime matches lesson', has_slime == (stage in ['02-03', '02-04']))
    check('maze matches lesson', any(a.actor_has_tag('ND1Geometry') for a in actors) == (stage != '02-01'))
    if stage == '02-03':
        controller = unreal.load_asset('/Game/AIC_Slime')
        components = ActorTools.get_components(BlueprintTools.get_default_object(controller))
        check('patrol controller has no perception', not any(isinstance(c, unreal.AIPerceptionComponent) for c in components))
        keys = [str(k.get_editor_property('entry_name')) for k in unreal.load_asset('/Game/BB_SlimeAI').get_editor_property('keys')]
        check('patrol blackboard has only PatrolLocation', keys == ['PatrolLocation'])
    world = unreal.EditorLevelLibrary.get_game_world()
    if world:
        pc = unreal.GameplayStatics.get_player_controller(world, 0)
        check('PIE player controller', pc is not None and pc.get_class().get_name() == 'BP_DungeonPlayerController_C')
        check('PIE player pawn', pc is not None and pc.get_controlled_pawn() is not None and pc.get_controlled_pawn().get_class().get_name() == 'BP_CubeMan_C')
        if stage in ['02-03', '02-04']:
            enemies = [a for a in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.Character) if a.get_class().get_name() == 'BP_Slime_C']
            check('PIE Slime AI controller', len(enemies) == 1 and enemies[0].get_controller().get_class().get_name() == 'AIC_Slime_C')
            check('PIE navigation query', unreal.NavigationSystemV1.get_random_reachable_point_in_radius(world, enemies[0].get_actor_location(), 500) is not None)
    result = {'stage': stage, 'pass': all(c['pass'] for c in checks), 'checks': checks, 'missing_dependencies': missing}
    if not result['pass']:
        raise RuntimeError(str(result))
    return result
