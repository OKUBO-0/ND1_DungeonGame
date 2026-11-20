"""PIE integration checks driven by editor ticks, using the real Enhanced Input and AI graphs."""
import json
import pathlib
import shutil
import traceback
import unreal

if '_state' not in globals():
    _state = {}


def _write():
    root=pathlib.Path(unreal.Paths.project_saved_dir())/'Verification'
    root.mkdir(parents=True,exist_ok=True)
    data={k:v for k,v in _state.items() if k in ['status','phase','checks','error','samples']}
    (root/'runtime-tests.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')


def _check(name,passed,details):
    _state['checks'].append({'name':name,'pass':bool(passed),'details':details})
    _write()


def _time():
    return unreal.GameplayStatics.get_time_seconds(_state['world'])


def _phase(name):
    _state['phase']=name
    _state['phase_start']=_time()
    _write()


def _teleport(pawn,xyz,yaw=0):
    pawn.set_actor_location(unreal.Vector(*xyz),False,True)
    pawn.set_actor_rotation(unreal.Rotator(yaw=yaw),False)
    controller=pawn.get_controller()
    if controller:
        controller.set_control_rotation(unreal.Rotator(yaw=yaw))
    movement=pawn.get_component_by_class(unreal.CharacterMovementComponent)
    if movement:movement.stop_movement_immediately()


def _input(action,xyz):
    _state['input'].inject_input_vector_for_action(_state[action],unreal.Vector(*xyz),[],[])


def _key(name):
    mapping=_state['mappings'][name]
    _state['input'].inject_input_vector_for_action(mapping.get_editor_property('action'),unreal.Vector(1,0,0),mapping.get_editor_property('modifiers'),[])


def _snapshot(name):
    saved=unreal.ND1DungeonEditorLibrary.capture_play_viewport()
    if saved:
        target=pathlib.Path(saved).parent/(name+'.png')
        shutil.copyfile(saved,target)


def _chasing():
    return _state['blackboard'].get_value_as_bool('IsChaseMode')


def _tick(delta):
    try:
        p=_state['player']; pc=_state['pc']; s=_state['slime']; ai=_state['ai']; bb=_state['blackboard']
        elapsed=_time()-_state['phase_start']; phase=_state['phase']
        if phase=='move':
            _key('W')
            if elapsed>1.2:
                loc=p.get_actor_location(); speed=p.get_velocity().length()
                anim=p.get_component_by_class(unreal.SkeletalMeshComponent).get_anim_instance()
                reported=float(anim.get_editor_property('Speed'))
                _check('camera-relative movement',loc.x>_state['move_start'].x+100 and abs(loc.y-_state['move_start'].y)<50,{'location':[loc.x,loc.y,loc.z]})
                _check('Run animation speed',speed>100 and reported>100,{'velocity':speed,'animation_speed':reported})
                _snapshot('running')
                _phase('idle')
        elif phase=='idle':
            _input('move',(0,0,0))
            if elapsed>1.2:
                anim=p.get_component_by_class(unreal.SkeletalMeshComponent).get_anim_instance()
                speed=float(anim.get_editor_property('Speed'))
                _check('return to Idle',speed<=100,{'animation_speed':speed})
                _snapshot('idle')
                _teleport(p,(-650,-1500,90),0)
                _phase('key_d')
        elif phase in ['key_d','key_a','key_s']:
            _key({'key_d':'D','key_a':'A','key_s':'S'}[phase])
            # Allow acceleration and a queued input frame after teleport, including
            # when an unfocused editor ticks at a reduced frame rate.
            if elapsed>1.2:
                loc=p.get_actor_location()
                ok=loc.y>-1450 if phase=='key_d' else loc.y<-1550 if phase=='key_a' else loc.x<-700
                _check(phase+' input mapping and modifiers',ok,{'location':[loc.x,loc.y,loc.z]})
                _teleport(p,(-650,-1500,90),0)
                if phase=='key_d':_phase('key_a')
                elif phase=='key_a':_phase('key_s')
                else:
                    _state['yaw_start']=pc.get_control_rotation().yaw
                    _phase('orbit')
        elif phase=='orbit':
            _key('Right')
            if elapsed>1:
                diff=unreal.MathLibrary.normalized_delta_rotator(pc.get_control_rotation(),unreal.Rotator(yaw=_state['yaw_start'])).yaw
                _check('camera arrow rotation',diff>0.1,{'yaw_delta':diff})
                _state['yaw_start']=pc.get_control_rotation().yaw
                _phase('orbit_left')
        elif phase=='orbit_left':
            _key('Left')
            if elapsed>1:
                diff=unreal.MathLibrary.normalized_delta_rotator(pc.get_control_rotation(),unreal.Rotator(yaw=_state['yaw_start'])).yaw
                _check('left arrow Negate modifier',diff < -0.1,{'yaw_delta':diff})
                pc.set_editor_property('CameraYawInverse',True)
                _state['yaw_start']=pc.get_control_rotation().yaw
                _phase('inverse')
        elif phase=='inverse':
            _key('Right')
            if elapsed>1:
                diff=unreal.MathLibrary.normalized_delta_rotator(pc.get_control_rotation(),unreal.Rotator(yaw=_state['yaw_start'])).yaw
                _check('camera inverse setting',diff < -0.1,{'yaw_delta':diff})
                pc.set_editor_property('CameraYawInverse',False)
                _teleport(p,(100,0,90),0)
                _phase('door_settle')
        elif phase=='door_settle':
            _input('camera',(0,0,0))
            if elapsed>1:_phase('door_pass')
        elif phase=='door_pass':
            _key('W')
            if elapsed>1.2:
                loc=p.get_actor_location()
                _check('subtractive doorway is passable',loc.x>520,{'x':loc.x,'y':loc.y,'z':loc.z})
                _snapshot('doorway')
                _teleport(p,(100,300,90),0)
                _phase('wall_block')
        elif phase=='wall_block':
            _key('W')
            if elapsed>1.2:
                loc=p.get_actor_location()
                _check('additive wall blocks player',200<loc.x<300,{'x':loc.x,'y':loc.y,'z':loc.z})
                _input('move',(0,0,0))
                _teleport(p,(-650,-1500,90),0)
                _teleport(s,(1800,-1500,57),180)
                _state['perception'].set_sense_enabled(unreal.AISense_Sight,True)
                _state['brain'].restart_logic()
                _phase('detect')
        elif phase=='detect':
            if elapsed>2:
                _check('Slime detects Player tag',_chasing() and bb.get_value_as_object('TargetActor')==p,{'chasing':_chasing()})
                _check('chase uses RunSpeed',abs(s.get_component_by_class(unreal.CharacterMovementComponent).get_editor_property('max_walk_speed')-500)<0.1,{'speed':s.get_velocity().length()})
                _snapshot('chasing')
                _teleport(p,(-650,1500,90),0)
                _phase('lost_wait')
        elif phase=='lost_wait':
            if elapsed>1:
                _check('lost sight keeps chasing during grace period',_chasing(),{'seconds':elapsed})
                _phase('lost_end')
        elif phase=='lost_end':
            if elapsed>3.2:
                _check('lost sight clears chase after 3 seconds',not _chasing(),{'chasing':_chasing()})
                _teleport(s,(1000,-1500,57),180)
                _teleport(p,(0,-1500,90),0)
                _phase('reacquire_setup')
        elif phase=='reacquire_setup':
            if elapsed>1.5:
                _check('Slime reacquires visible player',_chasing(),{'chasing':_chasing()})
                _teleport(p,(-650,1500,90),0)
                _phase('reacquire_loss')
        elif phase=='reacquire_loss':
            if elapsed>1:
                _teleport(s,(1000,-1500,57),180)
                _teleport(p,(0,-1500,90),0)
                _phase('reacquire_hold')
        elif phase=='reacquire_hold':
            if elapsed>3.5:
                _check('reacquisition cancels stale LoseSight timer',_chasing(),{'chasing':_chasing()})
                _state['perception'].set_sense_enabled(unreal.AISense_Sight,False)
                unreal.SystemLibrary.clear_and_invalidate_timer_handle(_state['world'],ai.get_editor_property('LoseSightTimer'))
                bb.set_value_as_bool('IsChaseMode',False)
                _teleport(s,(1800,-1500,57),180)
                _state['patrol_start']=s.get_actor_location()
                _state['patrol_max_distance']=0.0
                _state['patrol_has_destination']=False
                _state['brain'].restart_logic()
                _phase('patrol')
        elif phase=='patrol':
            distance=s.get_actor_location().distance(_state['patrol_start'])
            _state['patrol_max_distance']=max(_state['patrol_max_distance'],distance)
            destination=bb.get_value_as_vector('PatrolLocation')
            if abs(destination.x)<100000:_state['patrol_has_destination']=True
            if elapsed>8:
                speed=s.get_component_by_class(unreal.CharacterMovementComponent).get_editor_property('max_walk_speed')
                _check('random reachable patrol destination',_state['patrol_has_destination'],{'destination':[destination.x,destination.y,destination.z]})
                _check('patrol uses WalkSpeed and moves',abs(speed-100)<0.1 and _state['patrol_max_distance']>20,{'max_walk_speed':speed,'distance':_state['patrol_max_distance']})
                _snapshot('patrolling')
                _teleport(s,(-650,-1500,57),0)
                _teleport(p,(1800,1500,90),0)
                path=unreal.NavigationSystemV1.find_path_to_location_synchronously(_state['world'],s.get_actor_location(),p.get_actor_location(),s)
                points=list(path.get_editor_property('path_points')) if path else []
                _check('obstacle route is valid and bends around walls',bool(path) and path.is_valid() and not path.is_partial() and len(points)>=3,{'points':[[v.x,v.y,v.z] for v in points]})
                bb.set_value_as_object('TargetActor',p)
                bb.set_value_as_bool('IsChaseMode',True)
                _phase('obstacle_route')
        elif phase=='obstacle_route':
            if elapsed>18:
                distance=s.get_actor_location().distance(p.get_actor_location())
                _check('Slime follows a route around obstacles',distance<200,{'distance_to_target':distance})
                _snapshot('obstacle-route')
                _state['status']='passed' if all(c['pass'] for c in _state['checks']) else 'failed'
                unreal.unregister_slate_post_tick_callback(_state['handle'])
                _write()
    except Exception:
        _state['status']='error';_state['error']=traceback.format_exc()
        if _state.get('handle'):unreal.unregister_slate_post_tick_callback(_state['handle'])
        _write()


def build():
    current_world=unreal.EditorLevelLibrary.get_game_world()
    if _state.get('world') is not None and _state.get('world')!=current_world:
        _state.clear()
    if _state.get('status'):
        return {k:v for k,v in _state.items() if k in ['status','phase','checks','error']}
    world=current_world
    if not world:raise RuntimeError('Start PIE before running integration checks')
    pc=unreal.GameplayStatics.get_player_controller(world,0)
    player=pc.get_controlled_pawn()
    slime=next(p for p in unreal.GameplayStatics.get_all_actors_of_class(world,unreal.Character) if p.get_class().get_name()=='BP_Slime_C')
    ai=slime.get_controller()
    perception=ai.get_component_by_class(unreal.AIPerceptionComponent)
    brain=ai.get_editor_property('brain_component')
    brain.stop_logic('Integration checks: player movement first')
    perception.set_sense_enabled(unreal.AISense_Sight,False)
    subsystem_library=unreal.get_default_object(unreal.load_class(None,'/Script/Engine.SubsystemBlueprintLibrary'))
    input_system=subsystem_library.call_method('GetLocalPlayerSubSystemFromPlayerController',(pc,unreal.EnhancedInputLocalPlayerSubsystem.static_class()))
    _state.update(status='running',checks=[],samples=[],world=world,pc=pc,player=player,slime=slime,ai=ai,perception=perception,brain=brain,
                  blackboard=ai.get_editor_property('blackboard'),input=input_system,move=unreal.load_asset('/Game/IA_Move'),camera=unreal.load_asset('/Game/IA_CameraController'))
    data=unreal.load_asset('/Game/IMC_Game').get_editor_property('default_key_mappings')
    _state['mappings']={str(m.get_editor_property('key').get_editor_property('key_name')):m for m in data.get_editor_property('mappings')}
    _check('IMC_Game key bindings',set(_state['mappings'])=={'W','A','S','D','Left','Right'},list(_state['mappings']))
    _teleport(player,(-650,-1500,90),0)
    _teleport(slime,(1800,1500,57),180)
    _state['move_start']=player.get_actor_location()
    _phase('move')
    _state['handle']=unreal.register_slate_post_tick_callback(_tick)
    return {'status':'running','phase':'move'}
