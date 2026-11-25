"""Import four stone-footstep variants without changing the player animation graph."""
import json
import pathlib
import unreal


def build():
    world = unreal.EditorLevelLibrary.get_game_world()
    if world:
        cue = unreal.load_asset('/Game/SC_Footsteps')
        component = unreal.GameplayStatics.spawn_sound2d(world, cue)
        if not component or not component.is_playing(): raise RuntimeError('Footstep cue did not start playing')
        return {'audition_started':True, 'cue':cue.get_path_name(), 'cue_volume':cue.get_editor_property('volume_multiplier')}
    project = pathlib.Path(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir()))
    sources = project / 'SourceAssets' / 'Audio' / 'Footsteps'
    waves = []
    for index in range(1, 5):
        filename = sources / ('footstep-stone-%02d.wav' % index)
        if not filename.is_file(): raise RuntimeError('Missing source: ' + str(filename))
        factory = unreal.new_object(unreal.load_class(None, '/Script/AudioEditor.SoundFactory'))
        factory.set_editor_property('bAutoCreateCue', False)
        task = unreal.AssetImportTask()
        for prop, value in {'filename':str(filename), 'destination_path':'/Game', 'destination_name':'WS_Footstep_%02d' % index,
                            'automated':True, 'save':True, 'replace_existing':True, 'replace_existing_settings':True, 'factory':factory}.items():
            task.set_editor_property(prop, value)
        unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
        wave = unreal.load_asset('/Game/WS_Footstep_%02d' % index)
        if not isinstance(wave, unreal.SoundWave): raise RuntimeError('Sound import failed')
        wave.set_editor_property('volume', 1.0)
        wave.set_editor_property('pitch', 1.0)
        wave.set_editor_property('sound_class_object', None)
        unreal.EditorAssetLibrary.save_loaded_asset(wave, False)
        waves.append(wave)
    cue = unreal.ND1DungeonEditorLibrary.build_footstep_cue(waves)
    cue.set_editor_property('volume_multiplier', 0.2)
    cue.set_editor_property('pitch_multiplier', 1.0)
    unreal.EditorAssetLibrary.save_loaded_asset(cue, False)
    run = unreal.load_asset('/Game/AS_CubeMan_Run')
    lib = unreal.AnimationLibrary
    track = 'Footsteps'
    if track not in [str(t) for t in lib.get_animation_notify_track_names(run)]:
        lib.add_animation_notify_track(run, track, unreal.LinearColor(0.9, 0.6, 0.2, 1))
    lib.remove_animation_notify_events_by_track(run, track)
    times = [lib.get_time_at_frame(run, 7), min(0.62, run.get_play_length() - 0.001)]
    for time in times:
        notify = lib.add_animation_notify_event(run, track, time, unreal.AnimNotify_PlaySound)
        notify.set_editor_property('sound', cue)
    unreal.EditorAssetLibrary.save_loaded_asset(run, False)
    output = project / 'Saved' / 'FootstepsUpgrade'
    output.mkdir(parents=True, exist_ok=True)
    report = {'cue':cue.get_path_name(), 'cue_volume':cue.get_editor_property('volume_multiplier'),
              'run_length':run.get_play_length(), 'notify_times':times, 'waves':[]}
    for index, wave in enumerate(waves, 1):
        filename = str(output / ('footstep-%02d.wav' % index))
        task = unreal.AssetExportTask()
        for prop, value in {'object':wave, 'filename':filename, 'automated':True, 'prompt':False, 'replace_identical':True,
                            'exporter':unreal.new_object(unreal.load_class(None, '/Script/UnrealEd.SoundExporterWAV'))}.items():
            task.set_editor_property(prop, value)
        if not unreal.Exporter.run_asset_export_task(task): raise RuntimeError('Could not export preview wave')
        report['waves'].append({'asset':wave.get_path_name(), 'file':filename, 'volume':wave.get_editor_property('volume'),
                                'pitch':wave.get_editor_property('pitch'), 'duration':wave.get_editor_property('duration')})
    (output/'audio-settings.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    return report
