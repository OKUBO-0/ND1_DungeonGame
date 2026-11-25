"""Project-local MCP tools for the ND1 lessons (editor only)."""
import importlib
import json
import pathlib
import traceback
import unreal
import toolset_registry
from toolset_registry.registration import Registration


@unreal.uclass()
class DungeonLessonTools(unreal.ToolsetDefinition):
    """Build and inspect the four ND1 DungeonGame lessons in this project."""

    @toolset_registry.tool_call
    @staticmethod
    def run_stage(stage: str) -> str:
        """Run foundation, controller, animation, level, ai, verification, runtime_test or checkpoint_audit.

        Internal checkpoints stage reconstructs earlier assets and requires a Content backup.
        """
        if stage not in {'foundation', 'controller', 'animation', 'level', 'ai', 'verification', 'runtime_test', 'checkpoints', 'checkpoint_audit', 'demo', 'lesson01', 'facing', 'facing_test', 'footsteps'}:
            raise ValueError('Unknown lesson stage')
        module = importlib.import_module('nd1_' + stage)
        importlib.reload(module)
        try:
            result = module.build()
            report = {'stage': stage, 'ok': True, 'result': result}
        except Exception:
            report = {'stage': stage, 'ok': False, 'error': traceback.format_exc()}
        target = pathlib.Path(unreal.Paths.project_saved_dir()) / 'LessonBuild'
        target.mkdir(parents=True, exist_ok=True)
        (target / (stage + '.json')).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
        return json.dumps(report, ensure_ascii=False)

    @toolset_registry.tool_call
    @staticmethod
    def describe_api(type_name: str) -> str:
        """Read Unreal Python type documentation and public member names for implementation planning."""
        if not type_name.isidentifier() or type_name.startswith('_'):
            raise ValueError('Expected a public Unreal Python type name')
        obj = getattr(unreal, type_name)
        return json.dumps({'doc': obj.__doc__, 'members': [x for x in dir(obj) if not x.startswith('_')]})

    @toolset_registry.tool_call
    @staticmethod
    def close_editor() -> str:
        """Save dirty packages and close this project editor; stop PIE first."""
        if unreal.EditorLevelLibrary.get_game_world():
            raise RuntimeError('Stop PIE before closing the editor')
        if not unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True):
            raise RuntimeError('Saving was cancelled or failed; editor remains open')
        handle = []
        def quit_next_tick(delta):
            unreal.unregister_slate_post_tick_callback(handle[0])
            unreal.SystemLibrary.quit_editor()
        handle.append(unreal.register_slate_post_tick_callback(quit_next_tick))
        return 'Saved packages; editor close scheduled'


_registration = Registration([DungeonLessonTools])
_registration.register()
unreal.log('ND1 DungeonLessonTools registered')
