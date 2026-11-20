"""Lessons 2-3 and 2-4: editable Slime character, tasks, perception and behavior tree."""
import unreal
from editor_toolset.toolsets.blueprint import BlueprintTools
from editor_toolset.toolsets.actor import ActorTools
from nd1_foundation import import_fbx,bp,apply_default_material
from nd1_animation import sequence
from nd1_graph import call,link,value,node,clear_graph,pin


def add_variable(blueprint,name,type_name,default=None):
    if name not in BlueprintTools.list_variables(blueprint):
        BlueprintTools.add_variable(blueprint,name,type_name)
    BlueprintTools.compile_blueprint(blueprint)
    if default is not None:
        BlueprintTools.get_default_object(blueprint).set_editor_property(name,default)


def mesh_components(blueprint):
    return ActorTools.get_components(BlueprintTools.get_default_object(blueprint))


def save_bp(blueprint):
    unreal.ND1DungeonEditorLibrary.mark_blueprint_changed(blueprint)
    BlueprintTools.compile_blueprint(blueprint)
    unreal.EditorAssetLibrary.save_loaded_asset(blueprint,False)


def build_slime():
    mesh=import_fbx('Slime.fbx','SK_Slime',embedded=True)
    apply_default_material(mesh)
    skel=mesh.get_editor_property('skeleton')
    if skel.get_name()!='SKEL_Slime':
        unreal.EditorAssetLibrary.rename_asset(skel.get_path_name(),'/Game/SKEL_Slime')
        skel=unreal.load_asset('/Game/SKEL_Slime')
    anim=unreal.load_asset('/Game/AS_Slime')
    if not anim:
        raise RuntimeError('Embedded Slime animation was not imported as AS_Slime')
    anim.set_editor_property('loop',True)
    abp=unreal.load_asset('/Game/ABP_Slime')
    if not abp:
        factory=unreal.AnimBlueprintFactory()
        factory.set_editor_property('target_skeleton',skel)
        factory.set_editor_property('preview_skeletal_mesh',mesh)
        abp=unreal.AssetToolsHelpers.get_asset_tools().create_asset('ABP_Slime','/Game',unreal.AnimBlueprint,factory)
    graph=BlueprintTools.get_graph(abp,'AnimGraph')
    lib=unreal.ND1DungeonEditorLibrary
    root=next(n for n in lib.get_graph_nodes(graph) if isinstance(n,unreal.AnimGraphNode_Root))
    root.set_node_pos(unreal.IntPoint(600,0))
    editor=unreal.BlueprintGraphEditor.get_graph_editor(graph)
    editor.remove_nodes([n for n in lib.get_graph_nodes(graph) if n!=root])
    play=sequence(graph,anim)
    if not lib.connect_graph_nodes(play,'None',root,'None'):
        raise RuntimeError('Could not connect Slime pose')
    save_bp(abp)
    slime=bp('BP_Slime',unreal.Character)
    clear_graph(slime)
    if any(g.get_name()=='ChangeMoveMode' for g in BlueprintTools.list_graphs(slime)):
        BlueprintTools.remove_function_graph(slime,'ChangeMoveMode')
    cdo=BlueprintTools.get_default_object(slime)
    cdo.set_editor_property('use_controller_rotation_yaw',False)
    comps=mesh_components(slime)
    sm=next(c for c in comps if isinstance(c,unreal.SkeletalMeshComponent))
    sm.set_editor_property('skeletal_mesh',mesh)
    sm.set_editor_property('relative_location',unreal.Vector(0,0,-50))
    sm.set_editor_property('anim_class',abp.generated_class())
    capsule=next(c for c in comps if isinstance(c,unreal.CapsuleComponent))
    capsule.set_editor_property('capsule_radius',55.0)
    capsule.set_editor_property('capsule_half_height',55.0)
    movement=next(c for c in comps if isinstance(c,unreal.CharacterMovementComponent))
    movement.set_editor_property('orient_rotation_to_movement',True)
    movement.set_editor_property('max_walk_speed',100.0)
    for name,default in [('WalkSpeed',100.0),('RunSpeed',500.0)]:
        add_variable(slime,name,'float',default)
    enum=lib.create_move_mode_enum()
    functions=BlueprintTools.list_graphs(slime)
    old=next((g for g in functions if g.get_name()=='ChangeMoveMode'),None)
    if old:
        BlueprintTools.remove_function_graph(slime,'ChangeMoveMode')
    fn=BlueprintTools.add_function_graph(slime,'ChangeMoveMode')
    fe=unreal.BlueprintGraphEditor.get_graph_editor(fn)
    mode_pin=fe.add_graph_input_parameter('MoveMode',lib.enum_pin_type(enum),'NewEnumerator0')
    entry=mode_pin.get_owning_node()
    select=fe.create_node_from_name('ユーティリティ|選択する',unreal.Vector2D(350,200),[mode_pin])
    if not select:
        raise RuntimeError('Cannot create enum Select')
    if not pin(select,'Index').list_connected_pins() and not mode_pin.try_create_connection(pin(select,'Index')):
        raise RuntimeError('Cannot connect MoveMode enum to Select')
    options=[p for p in unreal.BlueprintEditorLibrary.list_all_pins(select,unreal.EdGraphPinDirection.EGPD_INPUT) if str(p.get_pin_name())!='Index']
    if len(options)!=2:
        raise RuntimeError('Select should have Walk and Run choices')
    for name,choice in zip(['WalkSpeed','RunSpeed'],options):
        getter=fe.add_get_member_variable_node(name,'')
        getter.set_node_pos(unreal.IntPoint(0,250 if name=='WalkSpeed' else 430))
        if not pin(getter,name,True).try_create_connection(choice):
            raise RuntimeError('Could not set enum speed choice')
    cm=fe.add_get_member_variable_node('CharacterMovement','')
    cm.set_node_pos(unreal.IntPoint(350,500))
    setter=fe.add_set_member_variable_node('MaxWalkSpeed','/Script/Engine.CharacterMovementComponent')
    setter.set_node_pos(unreal.IntPoint(800,0))
    link(entry,'then',setter,'execute')
    link(cm,'CharacterMovement',setter,'self')
    link(select,'ReturnValue',setter,'MaxWalkSpeed')
    save_bp(slime)
    graph,ge=clear_graph(slime)
    begin=BlueprintTools.add_event(slime,'ReceiveBeginPlay',unreal.IntPoint(0,0))
    change=call(ge,'/Game/BP_Slime.BP_Slime_C.ChangeMoveMode',350,0)
    value(change,'MoveMode','NewEnumerator0')
    link(begin,'then',change,'execute')
    save_bp(slime)
    for item in [mesh,skel,anim,enum]:unreal.EditorAssetLibrary.save_loaded_asset(item,False)
    return slime


def build():
    slime=build_slime()
    blackboard=build_blackboard()
    patrol=build_task('BTTask_FindRandomPatrol',False)
    chase=build_task('BTTask_ChangeToChaseMode',True)
    tree=unreal.load_asset('/Game/BT_SlimeAI')
    if not tree:
        tree=unreal.AssetToolsHelpers.get_asset_tools().create_asset('BT_SlimeAI','/Game',unreal.BehaviorTree,unreal.BehaviorTreeFactory())
    if not unreal.ND1DungeonEditorLibrary.build_slime_tree(tree,blackboard,patrol.generated_class(),chase.generated_class()):
        raise RuntimeError('Slime behavior tree has no root')
    unreal.EditorAssetLibrary.save_loaded_asset(tree,False)
    controller=build_controller(tree)
    cdo=BlueprintTools.get_default_object(slime)
    cdo.set_editor_property('ai_controller_class',controller.generated_class())
    save_bp(slime)
    player=unreal.load_asset('/Game/BP_CubeMan')
    BlueprintTools.get_default_object(player).set_editor_property('tags',['Player'])
    save_bp(player)
    actors=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    if not any(isinstance(a,unreal.NavMeshBoundsVolume) for a in actors.get_all_level_actors()):
        bounds=unreal.ND1DungeonEditorLibrary.add_box_brush('NavMeshBoundsVolume',unreal.Vector(1000,0,250),unreal.Vector(5000,5000,1000),False,True)
        bounds.set_editor_property('tags',['ND1Navigation'])
    if not any(a.get_class()==slime.generated_class() for a in actors.get_all_level_actors()):
        enemy=actors.spawn_actor_from_class(slime.generated_class(),unreal.Vector(1800,-1500,58),unreal.Rotator(yaw=180))
        enemy.set_actor_label('Slime')
        enemy.set_editor_property('tags',['ND1AI'])
    world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    nav=unreal.NavigationSystemV1.get_navigation_system(world)
    for volume in actors.get_all_level_actors():
        if isinstance(volume,unreal.NavMeshBoundsVolume):
            nav.on_navigation_bounds_updated(volume)
    unreal.ND1DungeonEditorLibrary.rebuild_level()
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
    return {'slime':slime.get_path_name(),'tree':tree.get_path_name(),'blackboard':blackboard.get_path_name(),'controller':controller.get_path_name()}


def build_blackboard():
    bb=unreal.load_asset('/Game/BB_SlimeAI')
    if not bb:
        bb=unreal.AssetToolsHelpers.get_asset_tools().create_asset('BB_SlimeAI','/Game',unreal.BlackboardData,unreal.BlackboardDataFactory())
    entries=[]
    for name,kind in [('PatrolLocation','Vector'),('IsChaseMode','Bool'),('TargetActor','Object')]:
        cls=unreal.load_class(None,'/Script/AIModule.BlackboardKeyType_'+kind)
        key=unreal.new_object(cls,outer=bb)
        if kind=='Object':
            key.set_editor_property('BaseClass',unreal.Actor.static_class())
        entry=unreal.BlackboardEntry()
        entry.set_editor_property('entry_name',name)
        entry.set_editor_property('key_type',key)
        entries.append(entry)
    bb.set_editor_property('keys',entries)
    unreal.EditorAssetLibrary.save_loaded_asset(bb,False)
    return bb


def build_task(name,is_chase):
    task=bp(name,unreal.BTTask_BlueprintBase)
    graph,ed=clear_graph(task)
    execute=BlueprintTools.add_event(task,'ReceiveExecuteAI',unreal.IntPoint(0,0))
    cast=node(ed,'ユーティリティ|Casting|CastToBP_Slime',300,0)
    link(execute,'then',cast,'execute')
    link(execute,'ControlledPawn',cast,'Object')
    cast_result=next(p.name for p in BlueprintTools._get_node_info(cast).output_pins if p.name not in ['then','CastFailed'])
    change=call(ed,'/Game/BP_Slime.BP_Slime_C.ChangeMoveMode',600,0)
    link(cast,'then',change,'execute')
    link(cast,cast_result,change,'self')
    value(change,'MoveMode','NewEnumerator1' if is_chase else 'NewEnumerator0')
    fail=call(ed,'/Script/AIModule.BTTask_BlueprintBase.FinishExecute',600,-250)
    link(cast,'CastFailed',fail,'execute')
    value(fail,'bSuccess','false')
    finish=call(ed,'/Script/AIModule.BTTask_BlueprintBase.FinishExecute',1800,0)
    value(finish,'bSuccess','true')
    if is_chase:
        link(change,'then',finish,'execute')
    else:
        blackboard=call(ed,'/Script/AIModule.AIBlueprintHelperLibrary.GetBlackboard',650,450)
        link(execute,'OwnerController',blackboard,'Target')
        location=call(ed,'/Script/Engine.Actor.K2_GetActorLocation',300,700)
        link(execute,'ControlledPawn',location,'self')
        random=call(ed,'/Script/NavigationSystem.NavigationSystemV1.K2_GetRandomReachablePointInRadius',700,700)
        value(random,'Radius','500.0')
        link(location,'ReturnValue',random,'Origin')
        select=call(ed,'/Script/Engine.KismetMathLibrary.SelectVector',1100,700)
        link(random,'ReturnValue',select,'bPickA')
        link(random,'RandomLocation',select,'A')
        link(location,'ReturnValue',select,'B')
        write=call(ed,'/Script/AIModule.BlackboardComponent.SetValueAsVector',1450,0)
        key=call(ed,'/Script/Engine.KismetSystemLibrary.MakeLiteralName',1100,450)
        value(key,'Value','PatrolLocation')
        link(key,'ReturnValue',write,'KeyName')
        link(blackboard,'ReturnValue',write,'self')
        link(select,'ReturnValue',write,'VectorValue')
        link(change,'then',write,'execute')
        link(write,'then',finish,'execute')
    save_bp(task)
    return task


def build_controller(tree):
    controller=bp('AIC_Slime',unreal.AIController)
    graph,ed=clear_graph(controller)
    for name,default in [('PlayerTagName','Player'),('IsChaseModeKeyName','IsChaseMode'),('TargetActorKeyName','TargetActor')]:
        add_variable(controller,name,'name',default)
    if 'LoseSightTimer' not in BlueprintTools.list_variables(controller):
        BlueprintTools.add_struct_variable(controller,'LoseSightTimer',unreal.TimerHandle.static_struct())
    BlueprintTools.compile_blueprint(controller)
    perception=next((c for c in mesh_components(controller) if isinstance(c,unreal.AIPerceptionComponent)),None)
    if not perception:
        perception=ActorTools.add_component(controller,unreal.AIPerceptionComponent.static_class(),'AIPerception')
    sight=unreal.new_object(unreal.AISenseConfig_Sight,outer=perception)
    sight.set_editor_property('sight_radius',3000.0)
    sight.set_editor_property('lose_sight_radius',3500.0)
    sight.set_editor_property('peripheral_vision_angle_degrees',90.0)
    sight.set_editor_property('detection_by_affiliation',unreal.AISenseAffiliationFilter(detect_enemies=True,detect_neutrals=True,detect_friendlies=False))
    perception.set_editor_property('senses_config',[sight])
    perception.set_editor_property('dominant_sense',unreal.AISense_Sight)
    begin=BlueprintTools.add_event(controller,'ReceiveBeginPlay',unreal.IntPoint(0,-500))
    run=call(ed,'/Script/AIModule.AIController.RunBehaviorTree',350,-500)
    value(run,'BTAsset',tree.get_path_name())
    link(begin,'then',run,'execute')
    event=BlueprintTools.add_component_bound_event(perception,'OnTargetPerceptionUpdated',graph)
    event.set_node_pos(unreal.IntPoint(0,0))
    tag=call(ed,'/Script/Engine.Actor.ActorHasTag',350,300)
    tagname=ed.add_get_member_variable_node('PlayerTagName','')
    tagname.set_node_pos(unreal.IntPoint(0,420))
    link(event,'Actor',tag,'self')
    link(tagname,'PlayerTagName',tag,'Tag')
    types=BlueprintTools.find_node_types(graph,'AIStimulus')
    break_type=next(t for t in types if 'Break' in t or '分解' in t)
    stimulus=node(ed,break_type,350,600)
    stim_in=BlueprintTools._get_node_info(stimulus).input_pins[0].name
    sensed=next(p.name for p in BlueprintTools._get_node_info(stimulus).output_pins if 'successfully' in p.name.lower())
    link(event,'Stimulus',stimulus,stim_in)
    found=call(ed,'/Script/Engine.KismetMathLibrary.BooleanAND',700,300)
    link(tag,'ReturnValue',found,'A')
    link(stimulus,sensed,found,'B')
    branch=ed.add_branch_node()
    branch.set_node_pos(unreal.IntPoint(1000,0))
    link(event,'then',branch,'execute')
    link(found,'ReturnValue',branch,'Condition')
    bb=ed.add_get_member_variable_node('Blackboard','')
    bb.set_node_pos(unreal.IntPoint(950,420))
    chasekey=ed.add_get_member_variable_node('IsChaseModeKeyName','')
    chasekey.set_node_pos(unreal.IntPoint(950,550))
    targetkey=ed.add_get_member_variable_node('TargetActorKeyName','')
    targetkey.set_node_pos(unreal.IntPoint(1450,420))
    enable=call(ed,'/Script/AIModule.BlackboardComponent.SetValueAsBool',1350,0)
    value(enable,'BoolValue','true')
    link(branch,'then',enable,'execute')
    link(bb,'Blackboard',enable,'self')
    link(chasekey,'IsChaseModeKeyName',enable,'KeyName')
    target=call(ed,'/Script/AIModule.BlackboardComponent.SetValueAsObject',1750,0)
    link(enable,'then',target,'execute')
    link(bb,'Blackboard',target,'self')
    link(targetkey,'TargetActorKeyName',target,'KeyName')
    link(event,'Actor',target,'ObjectValue')
    timerget=ed.add_get_member_variable_node('LoseSightTimer','')
    timerget.set_node_pos(unreal.IntPoint(1900,400))
    clear=call(ed,'/Script/Engine.KismetSystemLibrary.K2_ClearAndInvalidateTimerHandle',2200,0)
    link(target,'then',clear,'execute')
    link(timerget,'LoseSightTimer',clear,'Handle')
    notsensed=call(ed,'/Script/Engine.KismetMathLibrary.Not_PreBool',700,700)
    link(stimulus,sensed,notsensed,'A')
    lost=call(ed,'/Script/Engine.KismetMathLibrary.BooleanAND',1000,750)
    link(tag,'ReturnValue',lost,'A')
    link(notsensed,'ReturnValue',lost,'B')
    lostbranch=ed.add_branch_node()
    lostbranch.set_node_pos(unreal.IntPoint(1350,750))
    link(branch,'else',lostbranch,'execute')
    link(lost,'ReturnValue',lostbranch,'Condition')
    loseevent=BlueprintTools.add_event(controller,'LoseSight',unreal.IntPoint(1400,1200))
    disable=call(ed,'/Script/AIModule.BlackboardComponent.SetValueAsBool',1800,1200)
    value(disable,'BoolValue','false')
    link(loseevent,'then',disable,'execute')
    link(bb,'Blackboard',disable,'self')
    link(chasekey,'IsChaseModeKeyName',disable,'KeyName')
    schedule=call(ed,'/Script/Engine.KismetSystemLibrary.K2_SetTimerDelegate',1800,750)
    value(schedule,'Time','3.0')
    value(schedule,'bLooping','false')
    link(lostbranch,'then',schedule,'execute')
    delegate=next(p.name for p in BlueprintTools._get_node_info(loseevent).output_pins if p.name!='then')
    link(loseevent,delegate,schedule,'Delegate')
    timerset=ed.add_set_member_variable_node('LoseSightTimer','')
    timerset.set_node_pos(unreal.IntPoint(2200,750))
    link(schedule,'ReturnValue',timerset,'LoseSightTimer')
    link(schedule,'then',timerset,'execute')
    save_bp(controller)
    return controller
