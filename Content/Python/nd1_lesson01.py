"""Import the three animations already introduced in lesson 2-1 slides 30-35."""
import unreal
from nd1_foundation import import_fbx


def build():
    if unreal.EditorAssetLibrary.does_asset_exist('/Game/ABP_CubeMan'):
        raise RuntimeError('Use this stage on the 02-01 branch only')
    skeleton = unreal.load_asset('/Game/SKEL_CubeMan')
    imported = []
    for action in ['Idle', 'Run', 'Walk']:
        sequence = import_fbx('CubeMan_' + action + '.fbx', 'AS_CubeMan_' + action, skeleton=skeleton, animation=True)
        unreal.AnimationLibrary.remove_animation_notify_events_by_track(sequence, 'Footsteps')
        unreal.EditorAssetLibrary.save_loaded_asset(sequence, False)
        imported.append(sequence.get_path_name())
    return {'animations': imported, 'animation_blueprint': None, 'footsteps': None}
