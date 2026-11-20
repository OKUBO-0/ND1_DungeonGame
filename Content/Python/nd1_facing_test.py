"""PIE regression test: compare animated visual facing with actual velocity."""
import json
import pathlib
import traceback
import unreal
from nd1_facing import measure
from nd1_demo import _place

if '_state' not in globals(): _state = {}
CASES = [('W',(0,1),(-650,-1500,90),0), ('D',(1,0),(-650,-1600,90),0),
         ('A',(-1,0),(-650,900,90),0), ('S',(0,-1),(700,-1500,90),0),
         ('W_camera90',(0,1),(-650,-1600,90),90), ('W_D_diagonal',(1,1),(-650,-1600,90),0)]


def report():
    data = {k: v for k, v in _state.items() if k in ['status','checks','error']}
    path = pathlib.Path(unreal.Paths.project_saved_dir()) / 'Verification' / 'facing-tests.json'
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding='utf-8')
    return data


def _begin():
    name, vector, pos, yaw = CASES[_state['index']]
    _place(_state['pawn'], pos, yaw)
    _state['start'] = unreal.GameplayStatics.get_time_seconds(_state['world'])


def _tick(delta):
    try:
        if unreal.EditorLevelLibrary.get_game_world() != _state['world']:
            raise RuntimeError('PIE stopped during facing tests')
        name, vector, pos, yaw = CASES[_state['index']]
        _state['input'].inject_input_vector_for_action(_state['action'], unreal.Vector(vector[0], vector[1], 0), [], [])
        if unreal.GameplayStatics.get_time_seconds(_state['world']) - _state['start'] > 1.4:
            values = measure(_state['pawn'])
            _state['checks'].append({'name':name, 'pass':values['speed']>100 and values['actor_dot_velocity']>0.98 and values['visual_dot_velocity']>0.9, **values})
            _state['index'] += 1
            if _state['index'] == len(CASES):
                _state['status'] = 'passed' if all(c['pass'] for c in _state['checks']) else 'failed'
                unreal.unregister_slate_post_tick_callback(_state['handle'])
                _state['performance'].set_editor_property('bThrottleCPUWhenNotForeground', _state['old_throttle'])
            else: _begin()
            report()
    except Exception:
        _state['status']='error'; _state['error']=traceback.format_exc()
        unreal.unregister_slate_post_tick_callback(_state['handle'])
        _state['performance'].set_editor_property('bThrottleCPUWhenNotForeground', _state['old_throttle'])
        report()


def build():
    world = unreal.EditorLevelLibrary.get_game_world()
    if not world: raise RuntimeError('Start PIE first')
    if _state.get('world') == world: return report()
    _state.clear()
    pc = unreal.GameplayStatics.get_player_controller(world,0)
    library = unreal.get_default_object(unreal.load_class(None,'/Script/Engine.SubsystemBlueprintLibrary'))
    subsystem = library.call_method('GetLocalPlayerSubSystemFromPlayerController',(pc,unreal.EnhancedInputLocalPlayerSubsystem.static_class()))
    performance = unreal.get_default_object(unreal.load_class(None,'/Script/UnrealEd.EditorPerformanceSettings'))
    old = performance.get_editor_property('bThrottleCPUWhenNotForeground')
    performance.set_editor_property('bThrottleCPUWhenNotForeground',False)
    for ai in unreal.GameplayStatics.get_all_actors_of_class(world,unreal.AIController):
        brain=ai.get_editor_property('brain_component')
        if brain: brain.stop_logic('Facing regression test')
        perception=ai.get_component_by_class(unreal.AIPerceptionComponent)
        if perception: perception.set_sense_enabled(unreal.AISense_Sight,False)
    _state.update(world=world,pawn=pc.get_controlled_pawn(),input=subsystem,action=unreal.load_asset('/Game/IA_Move'),
                  index=0,status='running',checks=[],performance=performance,old_throttle=old)
    _begin()
    _state['handle']=unreal.register_slate_post_tick_callback(_tick)
    return report()
