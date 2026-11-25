"""Prepare one map per MCP call; save after asynchronous navigation completes."""
import json
import pathlib
import unreal
if '_prep' not in globals(): _prep={}

def write():
    result={k:v for k,v in _prep.items() if k not in ['performance','old_throttle']}
    (pathlib.Path(unreal.Paths.project_saved_dir())/'Assessment'/'map-preparation.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    return result

def load_map(name):
    unreal.EditorLoadingAndSavingUtils.load_map('/Game/Maps/'+name)
    actors=unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
    world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    for actor in actors:
        if isinstance(actor,unreal.RecastNavMesh):
            actor.set_editor_property('runtime_generation',unreal.RuntimeGenerationType.DYNAMIC)
            actor.set_editor_property('can_be_main_nav_data',True)
        if actor.get_actor_label().startswith('Vault_Lantern'):
            actor.get_component_by_class(unreal.PointLightComponent).set_editor_property('intensity',36)
        if actor.get_class().get_name() in ['ND1VaultPickup','ND1VaultGate']:
            actor.get_component_by_class(unreal.PointLightComponent).set_editor_property('intensity',3 if actor.get_class().get_name()=='ND1VaultPickup' else 6)
    from nd1_assessment_test import navigation
    system=navigation(world)
    for actor in actors:
        if isinstance(actor,unreal.NavMeshBoundsVolume): system.on_navigation_bounds_updated(actor)
    _prep.update(map=name,status='waiting')

def build():
    if not _prep or _prep.get('status')=='passed':
        _prep.clear()
        for name in ['Hero','Slime']:
            material=unreal.load_asset('/Game/Adventure/Materials/M_Vault_'+name)
            material.set_editor_property('bUsedWithSkeletalMesh',True)
            unreal.MaterialEditingLibrary.recompile_material(material)
            unreal.EditorAssetLibrary.save_loaded_asset(material,False)
        performance=unreal.get_default_object(unreal.load_class(None,'/Script/UnrealEd.EditorPerformanceSettings'))
        _prep.update(performance=performance,old_throttle=performance.get_editor_property('bThrottleCPUWhenNotForeground'),checks=[])
        performance.set_editor_property('bThrottleCPUWhenNotForeground',False)
        load_map('L_Vault02'); return write()
    world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    from nd1_assessment_test import navigation
    system=navigation(world)
    path=system.call_method('FindPathToLocationSynchronously',(world,unreal.Vector(360,360,0),unreal.Vector(1080,360,0),None,None))
    ready=path is not None and path.is_valid() and not path.is_partial()
    building=system.call_method('IsNavigationBeingBuiltOrLocked',(world,))
    _prep.update(ready=ready,building=building,nav=[{'name':a.get_name(),'runtime':str(a.get_editor_property('runtime_generation'))} for a in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors() if isinstance(a,unreal.RecastNavMesh)])
    if not ready and not building:
        unreal.ND1DungeonEditorLibrary.rebuild_level()
    if ready and not building:
        saved=unreal.EditorLoadingAndSavingUtils.save_packages([world.get_outermost()],False)
        if not saved: raise RuntimeError('Map save failed: '+_prep['map'])
        _prep['checks'].append({'map':_prep['map'],'navigation_ready':True,'saved':saved})
        if _prep['map']=='L_Vault02': load_map('L_Vault01')
        else:
            _prep['status']='passed'
            _prep['performance'].set_editor_property('bThrottleCPUWhenNotForeground',_prep['old_throttle'])
    return write()
