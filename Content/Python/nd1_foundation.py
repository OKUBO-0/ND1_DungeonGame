"""Lesson 2-1: import the supplied CubeMan and build the player assets."""
import unreal
from editor_toolset.toolsets.blueprint import BlueprintTools
from editor_toolset.toolsets.actor import ActorTools

SOURCE = 'C:/Users/k023g/Downloads/ND1_02_DungeonGameResources/'


def asset(name, cls, factory):
    existing = unreal.load_asset('/Game/' + name)
    return existing or unreal.AssetToolsHelpers.get_asset_tools().create_asset(name, '/Game', cls, factory)


def import_fbx(filename, name, skeleton=None, animation=False, embedded=False):
    existing = unreal.load_asset('/Game/' + name)
    resample = isinstance(existing,unreal.AnimSequence) and unreal.AnimationLibrary.get_num_frames(existing) > existing.get_play_length()*31
    resample = resample or (isinstance(existing,unreal.SkeletalMesh) and not existing.get_editor_property('skeleton'))
    if existing and not resample:
        return existing
    options = unreal.FbxImportUI()
    options.set_editor_property('automated_import_should_detect_type', False)
    options.set_editor_property('import_as_skeletal', True)
    options.set_editor_property('mesh_type_to_import', unreal.FBXImportType.FBXIT_ANIMATION if animation else unreal.FBXImportType.FBXIT_SKELETAL_MESH)
    options.set_editor_property('original_import_type', unreal.FBXImportType.FBXIT_ANIMATION if animation else unreal.FBXImportType.FBXIT_SKELETAL_MESH)
    options.set_editor_property('import_mesh', not animation)
    options.set_editor_property('import_animations', animation or embedded)
    if embedded:
        options.set_editor_property('override_animation_name', 'AS_Slime')
    options.set_editor_property('create_physics_asset', False)
    options.set_editor_property('import_materials', False)
    options.set_editor_property('import_textures', False)
    if skeleton:
        options.set_editor_property('skeleton', skeleton)
    data = options.get_editor_property('anim_sequence_import_data' if animation else 'skeletal_mesh_import_data')
    data.set_editor_property('import_rotation', unreal.Rotator(pitch=0, yaw=270, roll=0))
    if animation:
        data.set_editor_property('use_default_sample_rate',True)
        if existing:
            existing.get_editor_property('asset_import_data').set_editor_property('use_default_sample_rate',True)
    if not animation:
        data.set_editor_property('normal_import_method', unreal.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS)
    task = unreal.AssetImportTask()
    for key, value in {'filename': SOURCE + filename, 'destination_path': '/Game', 'destination_name': name,
                       'automated': True, 'save': True, 'replace_existing': resample, 'replace_existing_settings':True, 'options': options,
                       'factory': unreal.FbxFactory()}.items():
        task.set_editor_property(key, value)
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    paths = list(task.get_editor_property('imported_object_paths'))
    result = unreal.load_asset('/Game/' + name)
    if not result:
        raise RuntimeError('FBX import did not create ' + name + ': ' + str(paths))
    return result


def bp(name, parent):
    existing = unreal.load_asset('/Game/' + name)
    return existing or BlueprintTools.create('/Game', name, parent.static_class())


def apply_default_material(mesh):
    material=unreal.load_asset('/Engine/EngineMaterials/WorldGridMaterial')
    if not material:raise RuntimeError('Missing engine grid material')
    slots=list(mesh.get_editor_property('materials'))
    for i,old in enumerate(slots):
        slots[i]=unreal.SkeletalMaterial(material_interface=material,material_slot_name=old.material_slot_name,uv_channel_data=old.uv_channel_data)
    mesh.set_editor_property('materials',slots)


def build():
    # Save the original level before the lesson modifies it.
    mesh = import_fbx('CubeMan.fbx', 'SK_CubeMan',unreal.load_asset('/Game/SKEL_CubeMan'))
    skeleton = unreal.load_asset('/Game/SKEL_CubeMan') or mesh.get_editor_property('skeleton')
    if not skeleton:
        skeleton=unreal.load_asset('/Game/SKEL_CubeMan')
        if not skeleton:
            raise RuntimeError('Missing CubeMan skeleton')
        raise RuntimeError('CubeMan mesh did not retain its assigned skeleton after import')
    if skeleton.get_name() != 'SKEL_CubeMan':
        if not unreal.EditorAssetLibrary.rename_asset(skeleton.get_path_name(), '/Game/SKEL_CubeMan'):
            raise RuntimeError('Could not rename CubeMan skeleton')
        skeleton = unreal.load_asset('/Game/SKEL_CubeMan')
    if mesh.get_editor_property('skeleton') != skeleton:
        if not unreal.ND1DungeonEditorLibrary.assign_mesh_skeleton(mesh,skeleton):
            raise RuntimeError('Could not bind SK_CubeMan to SKEL_CubeMan')
    apply_default_material(mesh)
    animations = []
    for mode in ['Idle', 'Run', 'Walk']:
        anim = import_fbx('CubeMan_' + mode + '.fbx', 'AS_CubeMan_' + mode, skeleton, True)
        anim.set_editor_property('loop', True)
        unreal.EditorAssetLibrary.save_loaded_asset(anim)
        animations.append(anim.get_path_name())
    action_factory = unreal.DataAssetFactory()
    action_factory.set_editor_property('data_asset_class', unreal.InputAction)
    move = asset('IA_Move', unreal.InputAction, action_factory)
    move.set_editor_property('value_type', unreal.InputActionValueType.AXIS2D)
    camera = asset('IA_CameraController', unreal.InputAction, action_factory)
    camera.set_editor_property('value_type', unreal.InputActionValueType.AXIS1D)
    context_factory = unreal.DataAssetFactory()
    context_factory.set_editor_property('data_asset_class', unreal.InputMappingContext)
    context = asset('IMC_Game', unreal.InputMappingContext, context_factory)
    context.unmap_all()
    mappings = []
    for key, action, negate, swizzle in [('D', move, False, False), ('A', move, True, False), ('W', move, False, True),
                                          ('S', move, True, True), ('Left', camera, True, False), ('Right', camera, False, False)]:
        input_key = unreal.Key()
        input_key.set_editor_property('key_name', key)
        mapping = context.map_key(action, input_key)
        modifiers = []
        if negate:
            modifiers.append(unreal.new_object(unreal.InputModifierNegate, outer=context))
        if swizzle:
            mod = unreal.new_object(unreal.InputModifierSwizzleAxis, outer=context)
            mod.set_editor_property('order', unreal.InputAxisSwizzle.YXZ)
            modifiers.append(mod)
        mapping.set_editor_property('modifiers', modifiers)
        mappings.append(mapping)
    mapping_data=context.get_editor_property('default_key_mappings')
    mapping_data.set_editor_property('mappings',mappings)
    context.set_editor_property('default_key_mappings',mapping_data)
    player = bp('BP_CubeMan', unreal.Character)
    controller = bp('BP_DungeonPlayerController', unreal.PlayerController)
    mode = bp('BP_DungeonGameMode', unreal.GameModeBase)
    cdo = BlueprintTools.get_default_object(player)
    cdo.set_editor_property('use_controller_rotation_yaw', False)
    components = ActorTools.get_components(cdo)
    capsule = next(c for c in components if isinstance(c, unreal.CapsuleComponent))
    capsule.set_editor_property('capsule_half_height', 88.0)
    capsule.set_editor_property('capsule_radius', 25.0)
    char_mesh = next(c for c in components if isinstance(c, unreal.SkeletalMeshComponent))
    char_mesh.set_editor_property('skeletal_mesh', mesh)
    char_mesh.set_editor_property('relative_location', unreal.Vector(0, 0, -88))
    char_mesh.set_editor_property('relative_rotation', unreal.Rotator(pitch=0, yaw=270, roll=0))
    movement = next(c for c in components if isinstance(c, unreal.CharacterMovementComponent))
    movement.set_editor_property('orient_rotation_to_movement', True)
    movement.set_editor_property('rotation_rate', unreal.Rotator(pitch=0, yaw=1080, roll=0))
    arm = next((c for c in components if isinstance(c, unreal.SpringArmComponent)), None)
    if not arm:
        arm = ActorTools.add_component(player, unreal.SpringArmComponent.static_class(), 'SpringArm')
    arm.set_editor_property('relative_rotation', unreal.Rotator(pitch=-50, yaw=0, roll=0))
    arm.set_editor_property('target_arm_length', 500.0)
    arm.set_editor_property('use_pawn_control_rotation', True)
    arm.set_editor_property('inherit_pitch', False)
    arm.set_editor_property('inherit_roll', False)
    arm.set_editor_property('enable_camera_lag', True)
    arm.set_editor_property('enable_camera_rotation_lag', True)
    components = ActorTools.get_components(BlueprintTools.get_default_object(player))
    if not any(isinstance(c, unreal.CameraComponent) for c in components):
        ActorTools.add_component(arm, unreal.CameraComponent.static_class(), 'Camera')
    for item in [player, controller, mode]:
        BlueprintTools.compile_blueprint(item)
    defaults = BlueprintTools.get_default_object(mode)
    defaults.set_editor_property('default_pawn_class', player.generated_class())
    defaults.set_editor_property('player_controller_class', controller.generated_class())
    BlueprintTools.compile_blueprint(mode)
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    world.get_world_settings().set_editor_property('default_game_mode', mode.generated_class())
    for item in [mesh, skeleton, move, camera, context, player, controller, mode]:
        unreal.EditorAssetLibrary.save_loaded_asset(item,False)
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
    return {'mesh': mesh.get_path_name(), 'animations': animations, 'player': player.get_path_name(), 'components': [c.get_name() for c in components]}
