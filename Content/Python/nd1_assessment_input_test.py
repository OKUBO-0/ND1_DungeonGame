"""Regression checks through PIE player input on the new dungeon geometry."""
import json
import pathlib
import time
import traceback
import unreal
from nd1_facing import measure
from nd1_assessment_test import context,freeze,place,capture,navigation

if '_state' not in globals(): _state={}
CASES=[('W',0,(360,360,90),(1,0)),('S',0,(1080,360,90),(-1,0)),
       ('D',0,(360,360,90),(0,1)),('A',0,(360,1080,90),(0,-1)),
       ('W',90,(360,360,90),(0,1))]

def key(name,pressed): unreal.ND1DungeonEditorLibrary.set_play_key(name,pressed)
def report():
    data={k:v for k,v in _state.items() if k in ['status','phase','checks','error']}
    (pathlib.Path(unreal.Paths.project_saved_dir())/'Assessment'/'input-tests.json').write_text(json.dumps(data,indent=2),encoding='utf-8')
    return data
def check(name,passed,details=None): _state['checks'].append({'name':name,'pass':bool(passed),'details':details}); report()
def phase(name): _state.update(phase=name,start=time.perf_counter()); report()
def begin_case(player):
    name,yaw,position,direction=CASES[_state['index']]
    place(player,unreal.Vector(*position)); player.set_actor_rotation(unreal.Rotator(yaw=yaw),False)
    player.get_controller().set_control_rotation(unreal.Rotator(yaw=yaw)); key(name,True); phase('move')
def finish():
    for name in ['W','A','S','D','LeftShift','SpaceBar','Left','Right','P']: key(name,False)
    unreal.unregister_slate_post_tick_callback(_state['handle'])
    _state['performance'].set_editor_property('bThrottleCPUWhenNotForeground',_state['old_throttle']); report()
def tick(delta):
    try:
        world,gm,run,player=context(); elapsed=time.perf_counter()-_state['start']; current=_state['phase']
        if current=='start' and gm.get_editor_property('State')==unreal.VaultState.PLAYING and elapsed>.6:
            freeze(world); _state['index']=0; begin_case(player)
        elif current=='move' and elapsed>.42:
            name,yaw,position,direction=CASES[_state['index']]; values=measure(player)
            check('camera-relative '+name+' yaw '+str(yaw),values['speed']>100 and values['velocity_direction'][0]*direction[0]+values['velocity_direction'][1]*direction[1]>.98,values)
            check('visual facing '+name+' yaw '+str(yaw),values['visual_dot_velocity']>.9 and values['actor_dot_velocity']>.98)
            speed=player.get_component_by_class(unreal.SkeletalMeshComponent).get_anim_instance().get_editor_property('Speed')
            check('Run animation '+name+' yaw '+str(yaw),speed>100)
            key(name,False); _state['index']+=1
            if _state['index']<len(CASES): begin_case(player)
            else: phase('idle')
        elif current=='idle' and elapsed>.7:
            check('player stands on dungeon floor',80<player.get_actor_location().z<100,str(player.get_actor_location()))
            nav=navigation(world)
            path=nav.call_method('FindPathToLocationSynchronously',(world,unreal.Vector(360,360,0),unreal.Vector(1080,360,0),player,None))
            check('navigation path across corridor',path is not None and path.is_valid() and not path.is_partial(),str(list(path.get_editor_property('path_points'))) if path else None)
            check('Idle after release',player.get_component_by_class(unreal.SkeletalMeshComponent).get_anim_instance().get_editor_property('Speed')<=100)
            check('Hero material applied',player.get_component_by_class(unreal.SkeletalMeshComponent).get_material(0)==gm.get_editor_property('HeroMaterial'))
            _state['yaw']=player.get_controller().get_control_rotation().yaw; key('Right',True); phase('camera')
        elif current=='camera' and elapsed>.4:
            check('camera key rotates view',abs(player.get_controller().get_control_rotation().yaw-_state['yaw'])>10)
            key('Right',False); place(player,unreal.Vector(360,360,90)); player.get_controller().set_control_rotation(unreal.Rotator())
            key('W',True); key('LeftShift',True); phase('sprint')
        elif current=='sprint' and elapsed>.5:
            check('Shift sprint speed',player.get_component_by_class(unreal.CharacterMovementComponent).get_editor_property('max_walk_speed')==850)
            check('sprint drains stamina',gm.get_editor_property('Stamina')<99)
            key('W',False); key('LeftShift',False); _state['stamina']=gm.get_editor_property('Stamina'); phase('recover')
        elif current=='recover' and elapsed>.5:
            check('stamina recovers',gm.get_editor_property('Stamina')>_state['stamina'])
            key('SpaceBar',True); phase('pulse')
        elif current=='pulse' and elapsed>.15:
            check('Space triggers pulse',gm.get_editor_property('PulseCooldown')>5)
            key('SpaceBar',False); key('P',True); phase('pause')
        elif current=='pause' and elapsed>.2:
            check('P opens pause',gm.get_editor_property('State')==unreal.VaultState.PAUSED)
            key('P',False); capture('input-verified-pause'); gm.toggle_pause(); phase('finish')
        elif current=='finish' and elapsed>.3:
            gm.return_to_title(); _state['status']='passed' if all(c['pass'] for c in _state['checks']) else 'failed'; finish()
        elif elapsed>15: raise RuntimeError('Input test timed out: '+current)
    except Exception:
        _state.update(status='error',error=traceback.format_exc()); finish()
def build():
    if _state.get('status')=='running': return report()
    world,gm,run,player=context()
    performance=unreal.get_default_object(unreal.load_class(None,'/Script/UnrealEd.EditorPerformanceSettings'))
    _state.clear(); _state.update(status='running',checks=[],performance=performance,old_throttle=performance.get_editor_property('bThrottleCPUWhenNotForeground'))
    performance.set_editor_property('bThrottleCPUWhenNotForeground',False)
    check('audio data assigned',gm.get_editor_property('Audio') is not None,str(gm.get_editor_property('Audio')))
    check('hero material assigned',gm.get_editor_property('HeroMaterial') is not None,str(gm.get_editor_property('HeroMaterial')))
    check('four footstep variations retained',all(unreal.load_asset('/Game/WS_Footstep_%02d'%i) is not None for i in range(1,5)))
    events=unreal.AnimationLibrary.get_animation_notify_events_for_track(unreal.load_asset('/Game/AS_CubeMan_Run'),'Footsteps')
    check('footsteps timed to animation contacts',sorted(round(unreal.AnimationLibrary.get_anim_notify_event_trigger_time(e),5) for e in events)==[.23333,.62])
    gm.start_run(); phase('start'); _state['handle']=unreal.register_slate_post_tick_callback(tick); return report()
