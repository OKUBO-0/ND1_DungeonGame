"""Lesson 2-2: a level made from editable additive and subtractive BSP brushes."""
import unreal


def build():
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    lib = unreal.ND1DungeonEditorLibrary
    for actor in actors.get_all_level_actors():
        if actor.actor_has_tag('ND1Geometry'):
            actors.destroy_actor(actor)
        elif actor.get_actor_label() == 'Floor':
            comp = actor.get_component_by_class(unreal.StaticMeshComponent)
            if comp and comp.get_editor_property('static_mesh') and 'SM_Template_Map_Floor' in comp.get_editor_property('static_mesh').get_path_name():
                actors.destroy_actor(actor)
    created = []

    def box(label, xyz, size, subtract=False, nav=False):
        brush = lib.add_box_brush(label, unreal.Vector(*xyz), unreal.Vector(*size), subtract, nav)
        if not brush:
            raise RuntimeError('Could not build brush ' + label)
        brush.set_editor_property('tags',['ND1Geometry'])
        created.append(brush.get_actor_label())
        return brush

    box('DungeonFloor', (1000,0,-50), (5000,5000,100))
    for label,xyz,size in [
        ('OuterWest',(-1000,0,150),(100,4100,300)),
        ('OuterEast',(3000,0,150),(100,4100,300)),
        ('OuterNorth',(1000,2000,150),(4000,100,300)),
        ('OuterSouth',(1000,-2000,150),(4000,100,300)),
        ('LongNorthCorridor',(900,1200,150),(3000,100,300)),
        ('WestDivider',(-300,-100,150),(100,1800,300)),
        ('CentreSpine',(1200,0,150),(100,1800,300)),
        ('EastUpper',(2250,500,150),(1500,100,300)),
        ('EastLower',(2050,-500,150),(1100,100,300)),
        ('LowerDivider',(1350,-1250,150),(2200,100,300)),
    ]:
        box(label,xyz,size)
    # Exact additive/subtractive example from 2-2 slides 47-49.
    box('Doorway_Additive',(400,0,250),(200,1000,500))
    box('Doorway_Subtractive',(400,0,150),(300,200,300),True)
    for actor in actors.get_all_level_actors():
        if isinstance(actor,unreal.PlayerStart):
            actor.set_actor_location(unreal.Vector(-650,-1500,90),False,False)
            actor.set_actor_rotation(unreal.Rotator(yaw=0),False)
    lib.rebuild_level()
    unreal.EditorLevelLibrary.set_level_viewport_camera_info(unreal.Vector(-2600,-3400,4800),unreal.Rotator(pitch=-55,yaw=48,roll=0))
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
    return {'brushes':created,'doorway':{'wall_location':[400,0,250],'wall_size':[200,1000,500],'cut_location':[400,0,150],'cut_size':[300,200,300]},'height_change':0}
