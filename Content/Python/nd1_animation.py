"""Lesson 2-2: editable Idle/Run animation state machine."""
import unreal
from editor_toolset.toolsets.blueprint import BlueprintTools
from editor_toolset.toolsets.actor import ActorTools
from nd1_graph import call, link, value, clear_graph


def footsteps():
    from nd1_footsteps import build as build_footsteps
    return build_footsteps()


def sequence(graph, anim, x=0, y=0):
    lib = unreal.ND1DungeonEditorLibrary
    player = lib.spawn_graph_node(graph, unreal.AnimGraphNode_SequencePlayer, unreal.Vector2D(x,y))
    data = player.get_editor_property('node')
    data.set_editor_property('sequence', anim)
    data.set_editor_property('loop_animation', True)
    player.set_editor_property('node', data)
    return player


def build():
    lib = unreal.ND1DungeonEditorLibrary
    bp = unreal.load_asset('/Game/ABP_CubeMan')
    if not bp:
        factory = unreal.AnimBlueprintFactory()
        factory.set_editor_property('target_skeleton', unreal.load_asset('/Game/SKEL_CubeMan'))
        factory.set_editor_property('preview_skeletal_mesh', unreal.load_asset('/Game/SK_CubeMan'))
        bp = unreal.AssetToolsHelpers.get_asset_tools().create_asset('ABP_CubeMan', '/Game', unreal.AnimBlueprint, factory)
    if 'Speed' not in BlueprintTools.list_variables(bp):
        BlueprintTools.add_variable(bp, 'Speed', 'float')
    animgraph = BlueprintTools.get_graph(bp, 'AnimGraph')
    editor = unreal.BlueprintGraphEditor.get_graph_editor(animgraph)
    roots = [n for n in lib.get_graph_nodes(animgraph) if isinstance(n, unreal.AnimGraphNode_Root)]
    root = roots[0]
    root.set_node_pos(unreal.IntPoint(600,0))
    # Replace only this generated animation graph; the state-machine node owns its nested graphs.
    editor.remove_nodes([n for n in lib.get_graph_nodes(animgraph) if n != root])
    machine = lib.spawn_graph_node(animgraph, unreal.AnimGraphNode_StateMachine, unreal.Vector2D(0,0))
    machine_graph = next(g for g in BlueprintTools.list_graphs(bp) if g.get_outer() == machine)
    unreal.BlueprintEditorLibrary.rename_graph(machine_graph, 'TopStateMachine')
    if not lib.connect_graph_nodes(machine, 'None', root, 'None'):
        raise RuntimeError('Could not connect TopStateMachine to Output Pose')
    entry = next(n for n in lib.get_graph_nodes(machine_graph) if isinstance(n, unreal.AnimStateEntryNode))
    states = {}
    for name,x in [('Idle',0),('Run',500)]:
        state = lib.spawn_graph_node(machine_graph, unreal.AnimStateNode, unreal.Vector2D(x,200))
        lib.rename_graph_node(state, name)
        graph = next(g for g in BlueprintTools.list_graphs(bp) if g.get_outer() == state)
        result = next(n for n in lib.get_graph_nodes(graph) if isinstance(n, unreal.AnimGraphNode_StateResult))
        result.set_node_pos(unreal.IntPoint(600,0))
        player = sequence(graph, unreal.load_asset('/Game/AS_CubeMan_' + name))
        if not lib.connect_graph_nodes(player, 'None', result, 'None'):
            raise RuntimeError('Could not connect animation pose for ' + name)
        states[name] = state
    if not lib.connect_graph_nodes(entry, 'None', states['Idle'], 'None'):
        raise RuntimeError('Could not set Idle as entry state')
    for source,target,fn in [('Idle','Run','Greater_DoubleDouble'),('Run','Idle','LessEqual_DoubleDouble')]:
        previous = set(n.get_path_name() for n in lib.get_graph_nodes(machine_graph))
        if not lib.connect_graph_nodes(states[source], 'None', states[target], 'None'):
            raise RuntimeError('Could not connect state transition ' + source + ' -> ' + target)
        transition = next(n for n in lib.get_graph_nodes(machine_graph) if isinstance(n,unreal.AnimStateTransitionNode) and n.get_path_name() not in previous)
        graph = next(g for g in BlueprintTools.list_graphs(bp) if g.get_outer() == transition)
        rule = unreal.BlueprintGraphEditor.get_graph_editor(graph)
        result = next(n for n in lib.get_graph_nodes(graph) if isinstance(n,unreal.AnimGraphNode_TransitionResult))
        speed = rule.add_get_member_variable_node('Speed', '')
        speed.set_node_pos(unreal.IntPoint(-650,0))
        comparison = call(rule,'/Script/Engine.KismetMathLibrary.'+fn,-350,0)
        link(speed,'Speed',comparison,'A')
        value(comparison,'B','100.0')
        link(comparison,'ReturnValue',result,'bCanEnterTransition')
    graph,event_editor = clear_graph(bp)
    update = BlueprintTools.add_event(bp,'BlueprintUpdateAnimation',unreal.IntPoint(0,0))
    pawn = call(event_editor,'/Script/Engine.AnimInstance.TryGetPawnOwner',0,250)
    velocity = call(event_editor,'/Script/Engine.Actor.GetVelocity',350,250)
    length = call(event_editor,'/Script/Engine.KismetMathLibrary.VSize',650,250)
    setter = event_editor.add_set_member_variable_node('Speed','')
    setter.set_node_pos(unreal.IntPoint(1000,0))
    valid = call(event_editor,'/Script/Engine.KismetSystemLibrary.IsValid',350,450)
    branch = event_editor.add_branch_node()
    branch.set_node_pos(unreal.IntPoint(650,0))
    link(pawn,'ReturnValue',valid,'Object')
    link(valid,'ReturnValue',branch,'Condition')
    link(update,'then',branch,'execute')
    link(branch,'then',setter,'execute')
    link(pawn,'ReturnValue',velocity,'self')
    link(velocity,'ReturnValue',length,'A')
    link(length,'ReturnValue',setter,'Speed')
    lib.mark_blueprint_changed(bp)
    BlueprintTools.compile_blueprint(bp)
    unreal.EditorAssetLibrary.save_loaded_asset(bp,False)
    player_bp = unreal.load_asset('/Game/BP_CubeMan')
    mesh = next(c for c in ActorTools.get_components(BlueprintTools.get_default_object(player_bp)) if isinstance(c,unreal.SkeletalMeshComponent))
    mesh.set_editor_property('anim_class',bp.generated_class())
    lib.mark_blueprint_changed(player_bp)
    BlueprintTools.compile_blueprint(player_bp)
    unreal.EditorAssetLibrary.save_loaded_asset(player_bp,False)
    return {'animation_blueprint':bp.get_path_name(),'state_machine':'TopStateMachine','idle_to_run':'Speed > 100','run_to_idle':'Speed <= 100','footsteps':footsteps()}
