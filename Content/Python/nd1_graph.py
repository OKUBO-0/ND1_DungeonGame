import unreal
from editor_toolset.toolsets.blueprint import BlueprintTools


def pin(node, name, output=False):
    result = node.find_output_pin(name) if output else node.find_input_pin(name)
    if not result.is_valid():
        raise RuntimeError('Missing pin ' + name + ' on ' + node.get_name())
    return result


def link(source, source_name, target, target_name):
    if not pin(source, source_name, True).try_create_connection(pin(target, target_name)):
        raise RuntimeError('Cannot connect ' + source.get_name() + '.' + source_name + ' -> ' + target.get_name() + '.' + target_name)


def value(node, name, val):
    if not pin(node, name).set_pin_value(str(val)):
        raise RuntimeError('Cannot set ' + node.get_name() + '.' + name + ' = ' + str(val))


def call(editor, path, x, y):
    node = editor.add_call_function_node(path)
    if not node:
        raise RuntimeError('Cannot create function node ' + path)
    node.set_node_pos(unreal.IntPoint(x, y))
    return node


def node(editor, type_id, x, y):
    created = editor.create_node_from_name(type_id, unreal.Vector2D(x, y), [])
    if not created:
        raise RuntimeError('Cannot create ' + type_id)
    return created


def clear_graph(bp):
    graph = BlueprintTools.get_graph(bp, 'EventGraph')
    editor = unreal.BlueprintGraphEditor.get_graph_editor(graph)
    editor.remove_nodes(editor.list_all_nodes())
    for comment in editor.list_comment_nodes():
        editor.remove_comment_node(comment)
    return graph, editor
