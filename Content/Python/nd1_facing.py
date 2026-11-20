"""Align the imported CubeMan's visual forward axis with Character movement."""
import unreal
from editor_toolset.toolsets.blueprint import BlueprintTools
from editor_toolset.toolsets.actor import ActorTools


def measure(pawn):
    mesh = pawn.get_component_by_class(unreal.SkeletalMeshComponent)
    # The shoulder line is the visual right axis. Right cross Up is forward.
    right = mesh.get_socket_location('RightShoulder') - mesh.get_socket_location('LeftShoulder')
    span = max((right.x * right.x + right.y * right.y) ** 0.5, 0.00001)
    forward = unreal.Vector(right.y / span, -right.x / span, 0)
    velocity = pawn.get_velocity()
    velocity.z = 0
    speed = velocity.length()
    velocity = unreal.Vector(velocity.x / max(speed, 0.00001), velocity.y / max(speed, 0.00001), 0)
    actor = pawn.get_actor_forward_vector()
    return {'speed': speed, 'actor_yaw': pawn.get_actor_rotation().yaw,
            'mesh_relative_yaw': mesh.get_editor_property('relative_rotation').yaw,
            'visual_forward': [forward.x, forward.y, forward.z],
            'velocity_direction': [velocity.x, velocity.y, velocity.z],
            'visual_dot_velocity': forward.dot(velocity),
            'actor_dot_velocity': actor.dot(velocity)}


def build():
    if unreal.EditorLevelLibrary.get_game_world():
        return measure(unreal.GameplayStatics.get_player_controller(unreal.EditorLevelLibrary.get_game_world(), 0).get_controlled_pawn())
    player = unreal.load_asset('/Game/BP_CubeMan')
    mesh = next(c for c in ActorTools.get_components(BlueprintTools.get_default_object(player)) if isinstance(c, unreal.SkeletalMeshComponent))
    old = mesh.get_editor_property('relative_rotation')
    old_yaw = float(old.yaw)
    mesh.set_editor_property('relative_rotation', unreal.Rotator(pitch=old.pitch, yaw=0, roll=old.roll))
    unreal.ND1DungeonEditorLibrary.mark_blueprint_changed(player)
    BlueprintTools.compile_blueprint(player)
    unreal.EditorAssetLibrary.save_loaded_asset(player, False)
    return {'old_yaw': old_yaw, 'new_yaw': 0, 'reason': 'FBX import already applies yaw 270; imported visual forward is +X'}
