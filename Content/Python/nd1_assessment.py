"""Build the assessment's two playable vaults using Unreal Editor/MCP only."""
import collections
import pathlib
import unreal
from editor_toolset.toolsets.blueprint import BlueprintTools
from editor_toolset.toolsets.actor import ActorTools

ROOT='/Game/Adventure'
CELL=360.0
FLOORS=[
    {'name':'L_Vault01','title':'THE OUTER VAULT','grid':[
        '###########','#S..#....E#','#.#.#.###.#','#.#...#...#','#.###.#.#.#',
        '#...#...#.#','###.#.###.#','#...#.....#','#.#####.#.#','#.......#.#','###########'],
     'sigils':[(3,1),(1,7),(7,5)],'slimes':[(5,3),(7,7),(9,3)],'hearts':[(1,9)]},
    {'name':'L_Vault02','title':'THE SUNKEN CORE','grid':[
        '#############','#S....#....E#','#.###.#.###.#','#...#...#...#','###.#####.#.#',
        '#...#.....#.#','#.###.###.#.#','#.....#...#.#','#.#####.###.#','#...#...#...#',
        '#.#.#.###.#.#','#.#.......#.#','#############'],
     'sigils':[(5,1),(1,9),(9,5)],'slimes':[(5,3),(5,7),(9,7),(11,9)],'hearts':[(7,11),(11,5)]}
]


def native(name): return unreal.load_class(None,'/Script/ND1DungeonRuntime.'+name)
def save(asset): return unreal.EditorAssetLibrary.save_loaded_asset(asset,False)
def vector(x,y,z=0): return unreal.Vector(x,y,z)


def validate(floor):
    rows=floor['grid']; assert len({len(row) for row in rows})==1
    start=next((x,y) for y,row in enumerate(rows) for x,char in enumerate(row) if char=='S')
    goal=next((x,y) for y,row in enumerate(rows) for x,char in enumerate(row) if char=='E')
    reached={start}; queue=collections.deque([start])
    while queue:
        x,y=queue.popleft()
        for point in [(x+1,y),(x-1,y),(x,y+1),(x,y-1)]:
            xx,yy=point
            if 0<=yy<len(rows) and 0<=xx<len(rows[yy]) and rows[yy][xx]!='#' and point not in reached:
                reached.add(point); queue.append(point)
    for point in [goal,*floor['sigils'],*floor['slimes'],*floor['hearts']]:
        if point not in reached: raise RuntimeError('Unreachable objective '+str(point)+' in '+floor['name'])
    return start,goal,reached


def material(name,color,emission=0,metallic=0,translucent=False):
    asset=unreal.load_asset(ROOT+'/Materials/'+name)
    if asset: return asset
    asset=unreal.AssetToolsHelpers.get_asset_tools().create_asset(name,ROOT+'/Materials',unreal.Material,unreal.MaterialFactoryNew())
    lib=unreal.MaterialEditingLibrary
    base=lib.create_material_expression(asset,unreal.MaterialExpressionConstant3Vector,-500,0)
    base.set_editor_property('constant',unreal.LinearColor(*color))
    lib.connect_material_property(base,'',unreal.MaterialProperty.MP_BASE_COLOR)
    rough=lib.create_material_expression(asset,unreal.MaterialExpressionConstant,-500,150); rough.set_editor_property('r',0.65)
    lib.connect_material_property(rough,'',unreal.MaterialProperty.MP_ROUGHNESS)
    metal=lib.create_material_expression(asset,unreal.MaterialExpressionConstant,-500,300); metal.set_editor_property('r',metallic)
    lib.connect_material_property(metal,'',unreal.MaterialProperty.MP_METALLIC)
    if emission:
        light=lib.create_material_expression(asset,unreal.MaterialExpressionConstant3Vector,-500,450)
        light.set_editor_property('constant',unreal.LinearColor(*(c*emission for c in color)))
        lib.connect_material_property(light,'',unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    if translucent:
        asset.set_editor_property('blend_mode',unreal.BlendMode.BLEND_ADDITIVE)
        asset.set_editor_property('shading_model',unreal.MaterialShadingModel.MSM_UNLIT)
        opacity=lib.create_material_expression(asset,unreal.MaterialExpressionConstant,-200,600); opacity.set_editor_property('r',0.3)
        lib.connect_material_property(opacity,'',unreal.MaterialProperty.MP_OPACITY)
    lib.recompile_material(asset); save(asset); return asset


def resources():
    colors={'FloorA':((0.17,0.21,0.23),0,0),'FloorB':((0.14,0.18,0.20),0,0),
            'Wall':((0.055,0.08,0.105),0,0.05),'Trim':((0.32,0.24,0.13),0,0.55),
            'Amber':((1,0.55,0.10),2,0.2),'Relic':((0.10,0.75,0.90),2,0.1),
            'Heart':((0.20,0.95,0.55),2,0.1),'Hero':((0.09,0.42,0.50),0.08,0.25),
            'Slime':((0.42,0.12,0.55),0.06,0.05)}
    mats={name:material('M_Vault_'+name,*args) for name,args in colors.items()}
    for name in ['Hero','Slime']:
        mats[name].set_editor_property('bUsedWithSkeletalMesh',True)
        unreal.MaterialEditingLibrary.recompile_material(mats[name]); save(mats[name])
    mats['Pulse']=material('M_Vault_Pulse',(0.1,0.8,1),2,0,True)
    sounds={}
    project=pathlib.Path(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir()))
    for filename in sorted((project/'SourceAssets/Audio/Vault').glob('*.wav')):
        sound=unreal.load_asset(ROOT+'/Audio/'+filename.stem)
        if not sound:
            task=unreal.AssetImportTask(); factory=unreal.new_object(unreal.load_class(None,'/Script/AudioEditor.SoundFactory'))
            factory.set_editor_property('bAutoCreateCue',False)
            for prop,value in {'filename':str(filename),'destination_path':ROOT+'/Audio','destination_name':filename.stem,'automated':True,'save':True,'factory':factory}.items(): task.set_editor_property(prop,value)
            unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task]); sound=unreal.load_asset(ROOT+'/Audio/'+filename.stem)
        if not sound: raise RuntimeError('Missing '+filename.stem)
        sound.set_editor_property('volume',1.0)
        sound.set_editor_property('bLooping',filename.stem.startswith('S_BGM'))
        save(sound); sounds[filename.stem]=sound
    audio=unreal.load_asset(ROOT+'/DA_VaultAudio')
    if not audio:
        factory=unreal.DataAssetFactory(); factory.set_editor_property('DataAssetClass',native('ND1VaultAudio'))
        audio=unreal.AssetToolsHelpers.get_asset_tools().create_asset('DA_VaultAudio',ROOT,native('ND1VaultAudio'),factory)
    for key,name in {'Pickup':'S_Relic','Sigil':'S_Sigil','Hit':'S_Hit','Pulse':'S_Pulse','Gate':'S_Gate','Alert':'S_Alert','Confirm':'S_Confirm','Clear':'S_Clear'}.items(): audio.set_editor_property(key,sounds[name])
    save(audio)
    mode=unreal.load_asset(ROOT+'/BP_VaultGameMode') or BlueprintTools.create(ROOT,'BP_VaultGameMode',native('ND1VaultGameMode'))
    BlueprintTools.compile_blueprint(mode); cdo=BlueprintTools.get_default_object(mode)
    for prop,value in {'default_pawn_class':unreal.load_asset('/Game/BP_CubeMan').generated_class(),
                       'player_controller_class':unreal.load_asset('/Game/BP_DungeonPlayerController').generated_class(),
                       'Audio':audio,'HeroMaterial':mats['Hero'],'PulseMaterial':mats['Pulse']}.items(): cdo.set_editor_property(prop,value)
    BlueprintTools.compile_blueprint(mode); save(mode)
    return mats,sounds,mode


def build_floor(index,mats,sounds,mode):
    floor=FLOORS[index]; start,goal,reached=validate(floor)
    asset_path='/Game/Maps/'+floor['name']
    world=unreal.EditorLoadingAndSavingUtils.load_map(asset_path) if unreal.EditorAssetLibrary.does_asset_exist(asset_path) else unreal.EditorLoadingAndSavingUtils.new_blank_map(False)
    actors=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    for old in list(actors.get_all_level_actors()):
        if old.actor_has_tag('VaultGenerated'): actors.destroy_actor(old)
    def spawn(cls,position,label):
        actor=actors.spawn_actor_from_class(cls,position); actor.set_actor_label(label); actor.set_editor_property('tags',['VaultGenerated']); return actor
    world.get_world_settings().set_editor_property('default_game_mode',mode.generated_class())
    cube=unreal.load_asset('/Engine/BasicShapes/Cube')
    meshes={}
    for key in ['FloorA','FloorB','Wall','Trim']:
        owner=spawn(unreal.Actor,vector(0,0,0),'Vault_'+key)
        component=ActorTools.add_component(owner,unreal.InstancedStaticMeshComponent.static_class(),key)
        ActorTools.get_root_component(owner).set_editor_property('mobility',unreal.ComponentMobility.STATIC)
        component.set_editor_property('mobility',unreal.ComponentMobility.STATIC)
        component.set_static_mesh(cube); component.set_material(0,mats[key]); component.set_collision_profile_name('BlockAll')
        meshes[key]=component
    def box(key,xyz,size):
        transform=unreal.Transform(location=vector(*xyz),rotation=unreal.Rotator(),scale=vector(*(v/100 for v in size)))
        meshes[key].add_instance(transform,False)
    for y,row in enumerate(floor['grid']):
        for x,char in enumerate(row):
            px,py=x*CELL,y*CELL
            if char=='#':
                box('Wall',(px,py,110),(CELL,CELL,220))
                box('Trim',(px,py,224),(CELL+3,CELL+3,9))
            else:
                for dy in [-90,90]:
                    for dx in [-90,90]: box('FloorA' if (x+y+(dx>0))%2 else 'FloorB',(px+dx,py+dy,-18),(178,178,36))
    sun=spawn(unreal.DirectionalLight,vector(0,0,1800),'Vault_Moonlight'); sun.set_actor_rotation(unreal.Rotator(pitch=-52,yaw=-32),False)
    sun.get_component_by_class(unreal.DirectionalLightComponent).set_editor_property('mobility',unreal.ComponentMobility.MOVABLE)
    sun.get_component_by_class(unreal.DirectionalLightComponent).set_editor_property('intensity',4.0)
    sky=spawn(unreal.SkyLight,vector(0,0,500),'Vault_Skylight'); sky.get_component_by_class(unreal.SkyLightComponent).set_editor_property('intensity',0.7)
    sky.get_component_by_class(unreal.SkyLightComponent).set_editor_property('mobility',unreal.ComponentMobility.MOVABLE)
    spawn(unreal.SkyAtmosphere,vector(0,0,0),'Vault_Atmosphere')
    post=spawn(unreal.PostProcessVolume,vector(0,0,0),'Vault_ColorGrade'); post.set_editor_property('bUnbound',True)
    settings=post.get_editor_property('settings')
    for prop,value in {'bOverride_AutoExposureMinBrightness':True,'bOverride_AutoExposureMaxBrightness':True,'AutoExposureMinBrightness':1.0,'AutoExposureMaxBrightness':1.0,'bOverride_AutoExposureBias':True,'AutoExposureBias':0.0,'bOverride_BloomIntensity':True,'BloomIntensity':0.5}.items(): settings.set_editor_property(prop,value)
    post.set_editor_property('settings',settings)
    info=spawn(native('ND1VaultLevel'),vector(0,0,0),'Vault_LevelInfo')
    for prop,value in {'FloorNumber':index+1,'DisplayName':floor['title'],'NextLevel':'L_Vault02','Grid':floor['grid'],'CellSize':CELL,'RequiredSigils':3,'Music':sounds['S_BGM_0'+str(index+1)]}.items(): info.set_editor_property(prop,value)
    spawn(unreal.PlayerStart,vector(start[0]*CELL,start[1]*CELL,90),'Vault_PlayerStart')
    def pickup(point,kind,points,material_name):
        actor=spawn(native('ND1VaultPickup'),vector(point[0]*CELL,point[1]*CELL,78),'Vault_'+kind+'_'+str(point))
        kind_enum=getattr(unreal,'VaultPickup',None) or getattr(unreal,'EVaultPickup')
        actor.set_editor_property('Kind',{'Treasure':kind_enum.TREASURE,'Sigil':kind_enum.SIGIL,'Heart':kind_enum.HEART}[kind])
        actor.set_editor_property('Points',points)
        actor.get_editor_property('Gem').set_material(0,mats[material_name])
    for point in floor['sigils']: pickup(point,'Sigil',250,'Amber')
    for point in floor['hearts']: pickup(point,'Heart',25,'Heart')
    reserved=set([start,goal,*floor['sigils'],*floor['hearts'],*floor['slimes']])
    treasures=[p for p in sorted(reached,key=lambda p:(p[1],p[0])) if p not in reserved and (p[0]+p[1])%3==0][:12+index*3]
    for point in treasures: pickup(point,'Treasure',100,'Relic')
    gate=spawn(native('ND1VaultGate'),vector(goal[0]*CELL,goal[1]*CELL,125),'Vault_ExitGate'); gate.get_editor_property('Bars').set_material(0,mats['Amber'])
    for dx in [-145,145]: box('Trim',(goal[0]*CELL+dx,goal[1]*CELL,135),(30,45,270))
    box('Trim',(goal[0]*CELL,goal[1]*CELL,265),(320,45,30))
    slime_class=unreal.load_asset('/Game/BP_Slime').generated_class()
    for n,point in enumerate(floor['slimes']):
        slime=spawn(slime_class,vector(point[0]*CELL,point[1]*CELL,58),'Vault_Sentinel_'+str(n+1))
        slime.get_component_by_class(unreal.SkeletalMeshComponent).set_material(0,mats['Slime'])
    for n,point in enumerate(sorted(reached)):
        if n%7: continue
        light=spawn(unreal.PointLight,vector(point[0]*CELL,point[1]*CELL,145),'Vault_Lantern_'+str(n))
        component=light.get_component_by_class(unreal.PointLightComponent)
        component.set_editor_property('mobility',unreal.ComponentMobility.MOVABLE)
        component.set_editor_property('intensity',36); component.set_editor_property('attenuation_radius',480)
        component.set_editor_property('cast_shadows',False); component.set_light_color(unreal.LinearColor(1,0.52,0.17))
    size=len(floor['grid'])*CELL
    bounds=unreal.ND1DungeonEditorLibrary.add_box_brush('Vault_NavBounds',vector((size-CELL)/2,(size-CELL)/2,250),vector(size+CELL,size+CELL,900),False,True)
    bounds.set_editor_property('tags',['VaultGenerated'])
    nav=next((obj for obj in unreal.ObjectIterator(unreal.NavigationSystemV1) if obj.get_outer()==world),None)
    if nav: nav.on_navigation_bounds_updated(bounds)
    unreal.ND1DungeonEditorLibrary.rebuild_level()
    if not unreal.EditorLoadingAndSavingUtils.save_map(world,asset_path): raise RuntimeError('Map save failed')
    return {'map':asset_path,'reachable_cells':len(reached),'sigils':3,'treasures':len(treasures),'slimes':len(floor['slimes'])}


def build():
    if unreal.EditorLevelLibrary.get_game_world(): raise RuntimeError('Stop PIE before building vaults')
    for floor in FLOORS: validate(floor)
    mats,sounds,mode=resources()
    results=[build_floor(i,mats,sounds,mode) for i in range(2)]
    import nd1_assessment_prepare
    preparation=nd1_assessment_prepare.build()
    return {'levels':results,'mode':mode.get_path_name(),'audio_assets':len(sounds),'navigation_preparation':preparation}
