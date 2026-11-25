"""Exercise the real two-floor game flow and overlap-based scoring in PIE."""
import json
import pathlib
import shutil
import time
import traceback
import unreal

if '_test' not in globals(): _test={}
def native(name): return unreal.load_class(None,'/Script/ND1DungeonRuntime.'+name)
def state_enum(): return getattr(unreal,'VaultState',None) or getattr(unreal,'EVaultState')
def kind_enum(): return getattr(unreal,'VaultPickup',None) or getattr(unreal,'EVaultPickup')
def report():
    result={key:value for key,value in _test.items() if key in ['status','phase','checks','error']}
    folder=pathlib.Path(unreal.Paths.project_saved_dir())/'Assessment'; folder.mkdir(parents=True,exist_ok=True)
    (folder/'runtime-tests.json').write_text(json.dumps(result,indent=2),encoding='utf-8'); return result
def check(name,passed,details=None):
    _test['checks'].append({'name':name,'pass':bool(passed),'details':details}); report()
def phase(name): _test.update(phase=name,phase_start=time.perf_counter()); report()
def capture(name):
    image=unreal.ND1DungeonEditorLibrary.capture_play_viewport()
    if image: shutil.copyfile(image,pathlib.Path(unreal.Paths.project_saved_dir())/'Assessment'/(name+'.png'))
def place(actor,location):
    actor.set_actor_location(location,False,True)
    component=actor.get_component_by_class(unreal.CharacterMovementComponent)
    if component: component.stop_movement_immediately()
def all_kind(world,kind): return [a for a in unreal.GameplayStatics.get_all_actors_of_class(world,native('ND1VaultPickup')) if a.get_editor_property('Kind')==kind]
def enemies(world): return [a for a in unreal.GameplayStatics.get_all_actors_of_class(world,unreal.Character) if a.get_class().get_name()=='BP_Slime_C']
def navigation(world):
    return next(obj for obj in unreal.ObjectIterator(unreal.NavigationSystemV1) if obj.get_outer()==world)
def nav_point(world,position):
    nav=navigation(world)
    path=nav.call_method('FindPathToLocationSynchronously',(world,unreal.Vector(360,360,0),unreal.Vector(1080,360,0),None,None))
    return path if path and path.is_valid() and not path.is_partial() else None
def freeze(world):
    for actor in enemies(world):
        brain=actor.get_controller().get_editor_property('brain_component')
        if brain: brain.stop_logic('Assessment gameplay tests')
        actor.get_component_by_class(unreal.CharacterMovementComponent).stop_movement_immediately()
def context():
    world=unreal.EditorLevelLibrary.get_game_world()
    if not world: return None
    gm=unreal.GameplayStatics.get_game_mode(world)
    if not gm or gm.get_class().get_name()!='BP_VaultGameMode_C': return None
    return world,gm,unreal.GameplayStatics.get_game_instance(world),unreal.GameplayStatics.get_player_character(world,0)
def _tick(delta):
    try:
        values=context()
        if not values: return
        world,gm,run,player=values; elapsed=time.perf_counter()-_test['phase_start']; current=_test['phase']; states=state_enum(); kinds=kind_enum()
        status=gm.get_editor_property('State')
        if current=='title' and elapsed>.5:
            check('title flow',status==states.TITLE); check('HUD in viewport',gm.get_editor_property('HUD').is_in_viewport())
            check('custom GameInstance',run.get_class().get_name()=='ND1VaultInstance')
            capture('title'); gm.show_controls(); phase('controls')
        elif current=='controls' and elapsed>.4:
            check('controls flow',status==states.CONTROLS); capture('controls'); gm.back_from_controls(); gm.start_run(); phase('floor1')
        elif current=='floor1' and status==states.PLAYING and elapsed>2:
            info=gm.get_editor_property('LevelInfo'); check('floor 1 starts',info.get_editor_property('FloorNumber')==1)
            check('three sigils in first floor',len(all_kind(world,kinds.SIGIL))==3)
            check('three patrolling slimes',len(enemies(world))==3)
            music=info.get_editor_property('Music')
            playing=any(component.get_editor_property('sound')==music and component.is_playing() for component in unreal.ObjectIterator(unreal.AudioComponent))
            check('BGM playing',playing)
            check('first-floor navigation',nav_point(world,player.get_actor_location()) is not None,str(player.get_actor_location()))
            freeze(world); capture('playing-floor1'); _test['score_before']=run.get_editor_property('Score')
            target=all_kind(world,kinds.TREASURE)[0]; _test['treasure_location']=target.get_actor_location(); place(player,target.get_actor_location()+unreal.Vector(0,0,12)); phase('treasure1')
        elif current=='treasure1' and elapsed>.25:
            check('touching treasure adds 100',run.get_editor_property('Score')==_test['score_before']+100)
            _test['score_before']=run.get_editor_property('Score'); place(player,_test['treasure_location']+unreal.Vector(0,0,12));
            target=all_kind(world,kinds.TREASURE)[0]; place(player,target.get_actor_location()+unreal.Vector(0,0,12)); phase('treasure2')
        elif current=='treasure2' and elapsed>.25:
            check('chain bonus x2',run.get_editor_property('Score')==_test['score_before']+200)
            check('gate starts sealed',not gm.gate_open()); _test['score_before']=run.get_editor_property('Score')
            place(player,all_kind(world,kinds.SIGIL)[0].get_actor_location()+unreal.Vector(0,0,12)); phase('sigil')
        elif current=='sigil' and elapsed>.25:
            check('sigil overlap increments progress',gm.get_editor_property('Sigils')==1)
            check('sigil adds 250',run.get_editor_property('Score')==_test['score_before']+250)
            for target in list(all_kind(world,kinds.SIGIL)): place(player,target.get_actor_location()+unreal.Vector(0,0,12))
            phase('gate-ready')
        elif current=='gate-ready' and elapsed>.3:
            check('three sigils unlock gate',gm.gate_open())
            gate=unreal.GameplayStatics.get_all_actors_of_class(world,native('ND1VaultGate'))[0]
            check('gate collision disabled',gate.get_editor_property('Blocker').get_collision_enabled()==unreal.CollisionEnabled.NO_COLLISION)
            enemy=enemies(world)[0]; _test['enemy']=enemy; place(enemy,player.get_actor_location()-unreal.Vector(180,0,30))
            gm.try_pulse(); phase('pulse')
        elif current=='pulse' and elapsed>.15:
            enemy=_test['enemy']; movement=enemy.get_component_by_class(unreal.CharacterMovementComponent)
            check('pulse disables enemy movement',movement.get_editor_property('movement_mode')==unreal.MovementMode.MOVE_NONE)
            check('pulse consumes stamina',35<gm.get_editor_property('Stamina')<78)
            before=gm.get_editor_property('Stamina'); gm.try_pulse(); check('pulse cooldown blocks repeated use',abs(gm.get_editor_property('Stamina')-before)<.01)
            capture('pulse'); phase('pulse-end')
        elif current=='pulse-end' and elapsed>2.5:
            movement=_test['enemy'].get_component_by_class(unreal.CharacterMovementComponent)
            check('stunned enemy resumes movement',movement.get_editor_property('movement_mode')==unreal.MovementMode.MOVE_WALKING)
            gm.toggle_pause(); _test['pause_seconds']=run.get_editor_property('Seconds'); phase('pause')
        elif current=='pause' and elapsed>.6:
            check('pause menu',status==states.PAUSED); check('pause stops run clock',abs(run.get_editor_property('Seconds')-_test['pause_seconds'])<.01)
            capture('paused'); gm.toggle_pause(); _test['health_before']=run.get_editor_property('Health')
            place(_test['enemy'],player.get_actor_location()-unreal.Vector(85,0,30)); phase('damage')
        elif current=='damage' and elapsed>.2:
            check('slime contact costs one vitality',run.get_editor_property('Health')==_test['health_before']-1)
            _test['health_before']=run.get_editor_property('Health'); place(_test['enemy'],player.get_actor_location()-unreal.Vector(85,0,30)); phase('invulnerable')
        elif current=='invulnerable' and elapsed>.2:
            check('damage invulnerability prevents repeated hit',run.get_editor_property('Health')==_test['health_before'])
            run.set_editor_property('Health',1); gm.set_editor_property('Invulnerability',0.0)
            place(_test['enemy'],player.get_actor_location()-unreal.Vector(85,0,30)); phase('game-over')
        elif current=='game-over' and elapsed>.3:
            check('zero vitality causes game over',status==states.GAME_OVER); capture('game-over'); gm.restart_floor(); phase('retry')
        elif current=='retry' and status==states.PLAYING and elapsed>.6:
            check('retry restores vitality',run.get_editor_property('Health')==3)
            check('retry rolls back current-floor score',run.get_editor_property('Score')==0)
            freeze(world)
            for target in list(all_kind(world,kinds.SIGIL)): place(player,target.get_actor_location()+unreal.Vector(0,0,12))
            phase('enter-floor1')
        elif current=='enter-floor1' and elapsed>.3:
            gate=unreal.GameplayStatics.get_all_actors_of_class(world,native('ND1VaultGate'))[0]
            place(player,gate.get_actor_location()-unreal.Vector(0,0,35)); phase('floor-clear')
        elif current=='floor-clear' and elapsed>.3:
            check('exit overlap causes floor clear',status==states.FLOOR_CLEAR)
            check('time and vitality bonuses added',run.get_editor_property('Score')>750)
            _test['floor_score']=run.get_editor_property('Score'); capture('floor-clear'); gm.continue_floor(); phase('floor2')
        elif current=='floor2' and status==states.PLAYING and elapsed>2:
            check('second playable level loads',gm.get_editor_property('LevelInfo').get_editor_property('FloorNumber')==2)
            check('score persists between levels',run.get_editor_property('Score')==_test['floor_score'])
            check('four slimes in harder floor',len(enemies(world))==4)
            check('second-floor navigation',nav_point(world,player.get_actor_location()) is not None,str(player.get_actor_location()))
            freeze(world); capture('playing-floor2'); _test['enemy']=enemies(world)[0]
            place(player,unreal.Vector(360,360,90)); place(_test['enemy'],unreal.Vector(1080,360,58))
            _test['enemy'].set_actor_rotation(unreal.Rotator(yaw=180),False); _test['enemy'].get_controller().set_control_rotation(unreal.Rotator(yaw=180))
            _test['enemy'].get_controller().get_editor_property('brain_component').restart_logic(); phase('chase')
        elif current=='chase' and elapsed>.9:
            ai=_test['enemy'].get_controller(); check('new level supports sight chase',ai.get_editor_property('blackboard').get_value_as_bool('IsChaseMode'))
            check('chase selects run speed',abs(_test['enemy'].get_component_by_class(unreal.CharacterMovementComponent).get_editor_property('max_walk_speed')-500)<.1)
            check('slime actually follows navigation path',_test['enemy'].get_actor_location().x<1000,str(_test['enemy'].get_actor_location()))
            capture('chase'); place(player,unreal.Vector(360,3960,90)); phase('lose-sight')
        elif current=='lose-sight' and elapsed>4:
            check('new level returns from chase to patrol',not _test['enemy'].get_controller().get_editor_property('blackboard').get_value_as_bool('IsChaseMode'))
            _test['patrol_start']=_test['enemy'].get_actor_location(); _test['patrol_distance']=0; phase('patrol')
        elif current=='patrol':
            _test['patrol_distance']=max(_test['patrol_distance'],_test['enemy'].get_actor_location().distance(_test['patrol_start']))
            if elapsed<8: return
            check('new level patrol actually moves',_test['patrol_distance']>20,_test['patrol_distance'])
            freeze(world)
            for target in list(all_kind(world,kinds.SIGIL)): place(player,target.get_actor_location()+unreal.Vector(0,0,12))
            phase('enter-floor2')
        elif current=='enter-floor2' and elapsed>.3:
            gate=unreal.GameplayStatics.get_all_actors_of_class(world,native('ND1VaultGate'))[0]
            place(player,gate.get_actor_location()-unreal.Vector(0,0,35)); phase('victory')
        elif current=='victory' and elapsed>.3:
            check('second exit produces victory',status==states.VICTORY); capture('victory')
            saved=unreal.GameplayStatics.load_game_from_slot('EchoVaultRecord_Automation',0)
            check('best score persisted to disk',saved is not None and saved.get_editor_property('BestScore')>=run.get_editor_property('Score'))
            gm.return_to_title(); phase('title-return')
        elif current=='title-return' and status==states.TITLE and elapsed>.6:
            check('victory returns to title',True); capture('title-record')
            _test['status']='passed' if all(item['pass'] for item in _test['checks']) else 'failed'
            unreal.unregister_slate_post_tick_callback(_test['handle'])
            _test['performance'].set_editor_property('bThrottleCPUWhenNotForeground',_test['old_throttle']); report()
        elif elapsed>25: raise RuntimeError('Phase timed out: '+current+' / '+str(status))
    except Exception:
        _test['status']='error'; _test['error']=traceback.format_exc()
        unreal.unregister_slate_post_tick_callback(_test['handle'])
        _test['performance'].set_editor_property('bThrottleCPUWhenNotForeground',_test['old_throttle']); report()


def build():
    if not unreal.EditorLevelLibrary.get_game_world():
        import nd1_assessment_prepare
        import importlib
        importlib.reload(nd1_assessment_prepare)
        return nd1_assessment_prepare.build()
    if _test.get('status')=='running': return report()
    _test.clear()
    performance=unreal.get_default_object(unreal.load_class(None,'/Script/UnrealEd.EditorPerformanceSettings'))
    old=performance.get_editor_property('bThrottleCPUWhenNotForeground'); performance.set_editor_property('bThrottleCPUWhenNotForeground',False)
    _test.update(status='running',checks=[],performance=performance,old_throttle=old)
    phase('title'); _test['handle']=unreal.register_slate_post_tick_callback(_tick)
    return report()
