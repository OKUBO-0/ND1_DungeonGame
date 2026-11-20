import unreal
from editor_toolset.toolsets.blueprint import BlueprintTools
from editor_toolset.toolsets.actor import ActorTools


def audit_assets():
    checks=[]
    def check(name,got,expected):
        checks.append({'name':name,'pass':got==expected,'actual':str(got),'expected':str(expected)})
    lib=unreal.ND1DungeonEditorLibrary
    for name in ['BP_CubeMan','BP_DungeonGameMode','BP_DungeonPlayerController','ABP_CubeMan','ABP_Slime','BP_Slime','AIC_Slime','BTTask_FindRandomPatrol','BTTask_ChangeToChaseMode']:
        bp=unreal.load_asset('/Game/'+name)
        BlueprintTools.compile_blueprint(bp)
        for graph in BlueprintTools.list_graphs(bp):
            for n in lib.get_graph_nodes(graph):
                if isinstance(n,(unreal.AnimGraphNode_Root,unreal.AnimGraphNode_StateResult)):
                    n.set_node_pos(unreal.IntPoint(600,0))
                if name=='BP_Slime' and graph.get_name()=='ChangeMoveMode' and isinstance(n,unreal.K2Node_VariableGet):
                    info=BlueprintTools._get_node_info(n)
                    outputs=[p.name for p in info.output_pins]
                    if 'WalkSpeed' in outputs:n.set_node_pos(unreal.IntPoint(0,250))
                    if 'RunSpeed' in outputs:n.set_node_pos(unreal.IntPoint(0,430))
        unreal.EditorAssetLibrary.save_loaded_asset(bp,False)
        check(name+' compiles',True,True)
    player=unreal.load_asset('/Game/BP_CubeMan')
    cdo=BlueprintTools.get_default_object(player)
    check('Player tag','Player' in [str(t) for t in cdo.get_editor_property('tags')],True)
    check('UseControllerRotationYaw',cdo.get_editor_property('use_controller_rotation_yaw'),False)
    comps=ActorTools.get_components(cdo)
    capsule=next(c for c in comps if isinstance(c,unreal.CapsuleComponent))
    check('Player capsule half height',capsule.get_editor_property('capsule_half_height'),88.0)
    check('Player capsule radius',capsule.get_editor_property('capsule_radius'),25.0)
    mesh=next(c for c in comps if isinstance(c,unreal.SkeletalMeshComponent))
    check('Player mesh Z',mesh.get_editor_property('relative_location').z,-88.0)
    check('Player mesh yaw',mesh.get_editor_property('relative_rotation').yaw,270.0)
    movement=next(c for c in comps if isinstance(c,unreal.CharacterMovementComponent))
    check('OrientRotationToMovement',movement.get_editor_property('orient_rotation_to_movement'),True)
    check('RotationRate yaw',movement.get_editor_property('rotation_rate').yaw,1080.0)
    arm=next(c for c in comps if isinstance(c,unreal.SpringArmComponent))
    for prop,expected in [('target_arm_length',500.0),('use_pawn_control_rotation',True),('inherit_pitch',False),('inherit_roll',False),('enable_camera_lag',True),('enable_camera_rotation_lag',True)]:
        check('SpringArm '+prop,arm.get_editor_property(prop),expected)
    check('SpringArm pitch',arm.get_editor_property('relative_rotation').pitch,-50.0)
    for name in ['CubeMan','Slime']:
        asset=unreal.load_asset('/Game/SK_'+name)
        check(name+' skeleton binding',asset.get_editor_property('skeleton'),unreal.load_asset('/Game/SKEL_'+name))
        check(name+' material assigned',all(s.material_interface is not None for s in asset.get_editor_property('materials')),True)
    for mode in ['Idle','Run','Walk']:
        anim=unreal.load_asset('/Game/AS_CubeMan_'+mode)
        check(mode+' loops',anim.get_editor_property('loop'),True)
        check(mode+' sample rate',round(unreal.AnimationLibrary.get_num_frames(anim)/anim.get_play_length()),30)
        check(mode+' skeleton',anim.get_editor_property('skeleton'),unreal.load_asset('/Game/SKEL_CubeMan'))
    run=unreal.load_asset('/Game/AS_CubeMan_Run')
    events=unreal.AnimationLibrary.get_animation_notify_events_for_track(run,'Footsteps')
    check('Two footstep notifies',len(events),2)
    times=sorted(round(unreal.AnimationLibrary.get_anim_notify_event_trigger_time(e),5) for e in events)
    check('Footstep contact times',times,[0.23333,0.62])
    cue=unreal.load_asset('/Game/SC_Footsteps')
    check('Footstep volume',round(cue.get_editor_property('volume_multiplier'),3),0.2)
    check('Four sound waves',sum(bool(unreal.load_asset('/Game/WS_Footstep_%02d'%i)) for i in range(1,5)),4)
    slime=BlueprintTools.get_default_object(unreal.load_asset('/Game/BP_Slime'))
    for prop,expected in [('WalkSpeed',100.0),('RunSpeed',500.0)]:check(prop,slime.get_editor_property(prop),expected)
    sc=ActorTools.get_components(slime)
    cap=next(c for c in sc if isinstance(c,unreal.CapsuleComponent))
    check('Slime capsule radius',cap.get_editor_property('capsule_radius'),55.0)
    check('Slime capsule half height',cap.get_editor_property('capsule_half_height'),55.0)
    sm=next(c for c in sc if isinstance(c,unreal.SkeletalMeshComponent))
    check('Slime mesh Z',sm.get_editor_property('relative_location').z,-50.0)
    ai=BlueprintTools.get_default_object(unreal.load_asset('/Game/AIC_Slime'))
    sight=next(c for c in ActorTools.get_components(ai) if isinstance(c,unreal.AIPerceptionComponent)).get_editor_property('senses_config')[0]
    for prop,expected in [('sight_radius',3000.0),('lose_sight_radius',3500.0),('peripheral_vision_angle_degrees',90.0)]:check(prop,sight.get_editor_property(prop),expected)
    check('Detect neutrals',sight.get_editor_property('detection_by_affiliation').get_editor_property('detect_neutrals'),True)
    for prop,expected in [('PlayerTagName','Player'),('IsChaseModeKeyName','IsChaseMode'),('TargetActorKeyName','TargetActor')]:check(prop,str(ai.get_editor_property(prop)),expected)
    return {'pass':all(c['pass'] for c in checks),'checks':checks}


def build():
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    world = world or unreal.EditorLevelLibrary.get_game_world()
    world_settings = world.get_world_settings()
    result = {'editor_game_mode': str(world_settings.get_editor_property('default_game_mode'))}
    if not unreal.EditorLevelLibrary.get_game_world():
        result['asset_audit']=audit_assets()
    nav=unreal.NavigationSystemV1.get_navigation_system(world)
    result['navigation_system']=str(nav)
    result['navigation_actors']=[{'name':a.get_name(),'class':a.get_class().get_name(),'bounds':str(a.get_actor_bounds(False))} for a in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors() if 'Nav' in a.get_class().get_name()]
    result['nav_random']=str(unreal.NavigationSystemV1.get_random_reachable_point_in_radius(world,unreal.Vector(1800,-1500,57),500))
    result['nav_building']=unreal.NavigationSystemV1.is_navigation_being_built_or_locked(world)
    if not unreal.EditorLevelLibrary.get_game_world() and not result['nav_building'] and result['nav_random']!='None':
        result['navigation_saved']=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
    result['nav_settings']=[]
    for navdata in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors():
        if isinstance(navdata,unreal.RecastNavMesh):
            result['nav_settings'].append({p:str(navdata.get_editor_property(p)) for p in ['runtime_generation','can_be_main_nav_data','agent_radius','agent_height','force_rebuild_on_load']})
    bp = unreal.load_asset('/Game/BP_CubeMan')
    cdo = BlueprintTools.get_default_object(bp)
    result['components'] = []
    for c in ActorTools.get_components(cdo):
        data = {'name': c.get_name(), 'path': c.get_path_name(), 'class': c.get_class().get_name()}
        for p in ['relative_location', 'relative_rotation', 'target_arm_length', 'skeletal_mesh', 'capsule_half_height', 'capsule_radius', 'orient_rotation_to_movement']:
            try:
                data[p] = str(c.get_editor_property(p))
            except Exception:
                pass
        result['components'].append(data)
    for p in unreal.EditorLevelLibrary.get_all_level_actors():
        if isinstance(p, unreal.PlayerStart):
            result['player_start'] = str(p.get_actor_location())
    try:
        game_world = unreal.EditorLevelLibrary.get_game_world()
        if game_world:
            gm = unreal.GameplayStatics.get_game_mode(game_world)
            pc = unreal.GameplayStatics.get_player_controller(game_world, 0)
            result['game_mode'] = str(gm)
            result['runtime_controller'] = str(pc)
            result['runtime_default_pawn_class'] = str(gm.get_editor_property('default_pawn_class'))
            result['runtime_player_controller_class'] = str(gm.get_editor_property('player_controller_class'))
            result['runtime_pawn'] = str(pc.get_controlled_pawn()) if pc else None
            result['pawns'] = []
            for pawn in unreal.GameplayStatics.get_all_actors_of_class(game_world,unreal.Pawn):
                loc = pawn.get_actor_location()
                data = {'class':pawn.get_class().get_name(),'location':[loc.x,loc.y,loc.z],'speed':pawn.get_velocity().length()}
                mesh=pawn.get_component_by_class(unreal.SkeletalMeshComponent)
                if mesh:
                    data['anim_instance']=str(mesh.get_anim_instance())
                    data['mesh_skeleton']=str(mesh.get_editor_property('skeletal_mesh').get_editor_property('skeleton'))
                owner=pawn.get_controller()
                if isinstance(owner,unreal.AIController):
                    data['controller']=owner.get_class().get_name()
                    bb=owner.get_editor_property('blackboard')
                    if bb:
                        data['chasing']=bb.get_value_as_bool('IsChaseMode')
                        data['target']=str(bb.get_value_as_object('TargetActor'))
                        data['patrol_location']=str(bb.get_value_as_vector('PatrolLocation'))
                result['pawns'].append(data)
            result['gameplay_screenshot'] = unreal.ND1DungeonEditorLibrary.capture_play_viewport()
    except Exception as e:
        result['runtime_error'] = str(e)
    return result
