"""Capture actual PIE frames for each lesson's gameplay GIF (no editor UI)."""
import json
import pathlib
import shutil
import traceback
import unreal

if '_demo' not in globals():
    _demo = {}


def _report():
    data = {k: v for k, v in _demo.items() if k in ['stage', 'status', 'frames', 'frame_times', 'duration', 'error', 'player_distance', 'slime_distance', 'chase_seen']}
    (_demo['folder'] / 'capture.json').write_text(json.dumps(data, indent=2), encoding='utf-8')
    return data


def _place(pawn, xyz, yaw=0):
    pawn.set_actor_location(unreal.Vector(*xyz), False, True)
    pawn.set_actor_rotation(unreal.Rotator(yaw=yaw), False)
    pawn.get_component_by_class(unreal.CharacterMovementComponent).stop_movement_immediately()
    if pawn.get_controller():
        pawn.get_controller().set_control_rotation(unreal.Rotator(yaw=yaw))


def _tick(delta):
    try:
        world = unreal.EditorLevelLibrary.get_game_world()
        if world != _demo['world']:
            raise RuntimeError('PIE ended before capture completed')
        elapsed = unreal.GameplayStatics.get_time_seconds(world) - _demo['start']
        stage = _demo['stage']
        move = unreal.Vector()
        camera = 0.0
        if stage == '02-01':
            if 1 < elapsed < 2.4 or 5.2 < elapsed < 6.6: move.y = 1
            if 2.4 <= elapsed < 3.2: move.x = 1
            if 4 <= elapsed < 5.2: camera = 1
        elif stage == '02-02':
            if 1 < elapsed < 2.3 or 4.2 <= elapsed < 5.5: move.y = 1
            if 3 <= elapsed < 4.2: camera = 1
            if 7 <= elapsed < 9: camera = -1
        elif stage == '02-04':
            if 3 < elapsed < 5: move.y = -1
            if 5 <= elapsed < 6: move.x = 1
        subsystem = _demo['input']
        subsystem.inject_input_vector_for_action(_demo['move'], move, [], [])
        subsystem.inject_input_vector_for_action(_demo['camera'], unreal.Vector(camera, 0, 0), [], [])
        _demo['player_distance'] = max(_demo['player_distance'], _demo['player'].get_actor_location().distance(_demo['player_start']))
        if _demo.get('slime'):
            slime = _demo['slime']
            _demo['slime_distance'] = max(_demo['slime_distance'], slime.get_actor_location().distance(_demo['slime_start']))
            bb = slime.get_controller().get_editor_property('blackboard')
            if stage == '02-04': _demo['chase_seen'] |= bb.get_value_as_bool('IsChaseMode')
        if elapsed >= _demo['next_frame']:
            frame = unreal.ND1DungeonEditorLibrary.capture_play_viewport()
            if not frame:
                raise RuntimeError('No active PIE viewport')
            shutil.copyfile(frame, _demo['folder'] / ('frame-%04d.png' % _demo['frames']))
            _demo['frames'] += 1
            _demo['frame_times'].append(elapsed)
            _demo['next_frame'] = elapsed + 0.125
        if elapsed >= _demo['duration']:
            _demo['status'] = 'captured'
            unreal.unregister_slate_post_tick_callback(_demo['handle'])
            _demo['performance'].set_editor_property('bThrottleCPUWhenNotForeground', _demo['old_throttle'])
            _report()
    except Exception:
        _demo['status'] = 'error'
        _demo['error'] = traceback.format_exc()
        unreal.unregister_slate_post_tick_callback(_demo['handle'])
        if _demo.get('performance'):
            _demo['performance'].set_editor_property('bThrottleCPUWhenNotForeground', _demo['old_throttle'])
        _report()


def build():
    world = unreal.EditorLevelLibrary.get_game_world()
    if not world:
        raise RuntimeError('Start PIE before recording')
    if _demo.get('status') == 'recording' and _demo.get('world') == world:
        return _report()
    _demo.clear()
    content = pathlib.Path(unreal.Paths.project_content_dir())
    stage = '02-04' if (content/'BTTask_ChangeToChaseMode.uasset').is_file() else '02-03' if (content/'BP_Slime.uasset').is_file() else '02-02' if (content/'ABP_CubeMan.uasset').is_file() else '02-01'
    folder = pathlib.Path(unreal.Paths.project_saved_dir()) / 'Demos' / stage
    folder.mkdir(parents=True, exist_ok=True)
    for old in folder.glob('frame-*.png'): old.unlink()
    pc = unreal.GameplayStatics.get_player_controller(world, 0)
    player = pc.get_controlled_pawn()
    library = unreal.get_default_object(unreal.load_class(None, '/Script/Engine.SubsystemBlueprintLibrary'))
    subsystem = library.call_method('GetLocalPlayerSubSystemFromPlayerController', (pc, unreal.EnhancedInputLocalPlayerSubsystem.static_class()))
    starts = {'02-01': (0, 0, 90), '02-02': (100, 0, 90), '02-03': (1400, -1600, 90), '02-04': (1000, -1500, 90)}
    _place(player, starts[stage])
    performance = unreal.get_default_object(unreal.load_class(None, '/Script/UnrealEd.EditorPerformanceSettings'))
    old_throttle = performance.get_editor_property('bThrottleCPUWhenNotForeground')
    performance.set_editor_property('bThrottleCPUWhenNotForeground', False)
    _demo.update(stage=stage, status='recording', world=world, folder=folder, player=player, input=subsystem,
                 move=unreal.load_asset('/Game/IA_Move'), camera=unreal.load_asset('/Game/IA_CameraController'), performance=performance, old_throttle=old_throttle,
                 start=unreal.GameplayStatics.get_time_seconds(world), next_frame=0, frames=0, frame_times=[],
                 duration=8 if stage == '02-01' else 10, player_start=player.get_actor_location(),
                 player_distance=0.0, slime_distance=0.0, chase_seen=False)
    if stage in ['02-03', '02-04']:
        slime = next(a for a in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.Character) if a.get_class().get_name() == 'BP_Slime_C')
        _place(slime, (1800, -1500, 58), 180)
        _demo.update(slime=slime, slime_start=slime.get_actor_location())
    _demo['handle'] = unreal.register_slate_post_tick_callback(_tick)
    return _report()

