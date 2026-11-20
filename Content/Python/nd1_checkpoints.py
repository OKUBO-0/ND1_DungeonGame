"""Reconstruct lesson-end assets through the editor; write copies only under Saved.

Run on the completed 02-04 project after backing up Content. Restart the editor
after restoring that backup: loaded UObjects must never be used after restoration.
"""
import json
import pathlib
import shutil
import unreal
from editor_toolset.toolsets.blueprint import BlueprintTools
from editor_toolset.toolsets.actor import ActorTools
from nd1_ai import save_bp
from nd1_graph import clear_graph, call, link, value


AI_ASSETS = {'ABP_Slime', 'AIC_Slime', 'AS_Slime', 'BB_SlimeAI', 'BP_Slime',
             'BT_SlimeAI', 'BTTask_ChangeToChaseMode', 'BTTask_FindRandomPatrol',
             'E_MoveMode', 'SK_Slime', 'SKEL_Slime'}
ANIMATION_ASSETS = {'ABP_CubeMan', 'SC_Footsteps',
                    'WS_Footstep_01', 'WS_Footstep_02', 'WS_Footstep_03', 'WS_Footstep_04'}


def snapshot(name, excluded):
    source = pathlib.Path(unreal.Paths.project_content_dir())
    target = pathlib.Path(unreal.Paths.project_saved_dir()) / 'BranchSnapshots' / name / 'Content'
    if target.exists():
        raise RuntimeError('Snapshot already exists: ' + str(target))
    target.mkdir(parents=True)
    for item in source.rglob('*'):
        if not item.is_file() or '__pycache__' in item.parts or item.stem in excluded:
            continue
        dest = target / item.relative_to(source)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(item, dest)
    return target


def build():
    saved = pathlib.Path(unreal.Paths.project_saved_dir())
    original = saved / 'BeforeLessons' / 'GameLevel.umap'
    backup = saved / 'BranchSnapshots' / 'final' / 'Content'
    if not original.is_file() or not (backup / 'GameLevel.umap').is_file():
        raise RuntimeError('Original level and complete final Content backup are required before reconstruction')
    if any((saved / 'BranchSnapshots' / name).exists() for name in ['02-01', '02-02', '02-03']):
        raise RuntimeError('Lesson snapshots already exist; no assets were changed')
    level = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    player = unreal.load_asset('/Game/BP_CubeMan')
    BlueprintTools.get_default_object(player).set_editor_property('tags', [])
    save_bp(player)

    # 02-03 has patrol only: no perception, timer, chase keys or chase task.
    controller = unreal.load_asset('/Game/AIC_Slime')
    graph, editor = clear_graph(controller)
    for comp in ActorTools.get_components(BlueprintTools.get_default_object(controller)):
        if isinstance(comp, unreal.AIPerceptionComponent):
            if not ActorTools.remove_component(comp):
                raise RuntimeError('Could not remove perception component')
    for name in ['PlayerTagName', 'IsChaseModeKeyName', 'TargetActorKeyName', 'LoseSightTimer']:
        if name in BlueprintTools.list_variables(controller):
            BlueprintTools.remove_variable(controller, name)
    begin = BlueprintTools.add_event(controller, 'ReceiveBeginPlay', unreal.IntPoint(0, 0))
    run = call(editor, '/Script/AIModule.AIController.RunBehaviorTree', 350, 0)
    value(run, 'BTAsset', '/Game/BT_SlimeAI.BT_SlimeAI')
    link(begin, 'then', run, 'execute')
    save_bp(controller)
    bb = unreal.load_asset('/Game/BB_SlimeAI')
    bb.set_editor_property('keys', [k for k in bb.get_editor_property('keys') if str(k.get_editor_property('entry_name')) == 'PatrolLocation'])
    unreal.EditorAssetLibrary.save_loaded_asset(bb, False)
    tree = unreal.load_asset('/Game/BT_SlimeAI')
    patrol = unreal.load_asset('/Game/BTTask_FindRandomPatrol')
    if not unreal.ND1DungeonEditorLibrary.build_slime_tree(tree, bb, patrol.generated_class(), None):
        raise RuntimeError('Could not build patrol-only tree')
    unreal.EditorAssetLibrary.save_loaded_asset(tree, False)
    level.save_current_level()
    out3 = snapshot('02-03', {'BTTask_ChangeToChaseMode'})

    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    for actor in actors.get_all_level_actors():
        if actor.actor_has_tag('ND1AI') or actor.actor_has_tag('ND1Navigation') or isinstance(actor, unreal.RecastNavMesh):
            actors.destroy_actor(actor)
    level.save_current_level()
    out2 = snapshot('02-02', AI_ASSETS)

    mesh = next(c for c in ActorTools.get_components(BlueprintTools.get_default_object(player)) if isinstance(c, unreal.SkeletalMeshComponent))
    mesh.set_editor_property('anim_class', None)
    save_bp(player)
    # 2-1 already imports Idle/Run/Walk; sound notifications start in 2-2.
    run = unreal.load_asset('/Game/AS_CubeMan_Run')
    unreal.AnimationLibrary.remove_animation_notify_events_by_track(run, 'Footsteps')
    unreal.EditorAssetLibrary.save_loaded_asset(run, False)
    out1 = snapshot('02-01', AI_ASSETS | ANIMATION_ASSETS)
    shutil.copy2(original, out1 / 'GameLevel.umap')
    report = {'02-01': str(out1), '02-02': str(out2), '02-03': str(out3),
              'note': 'Reconstructed from final assets through Unreal Editor, not historical commits.'}
    return report
