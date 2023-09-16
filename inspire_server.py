import random
import server
from enum import Enum

class SGmode(Enum):
    FIX = 1
    INCR = 2
    DECR = 3
    RAND = 4


class SeedGenerator:
    def __init__(self, base_value, action):
        self.base_value = base_value

        if action == "increment" or action == "decrement" or action == "randomize":
            self.action = SGmode.FIX
        elif action == 'increment for each node':
            self.action = SGmode.INCR
        elif action == 'decrement for each node':
            self.action = SGmode.DECR
        elif action == 'randomize for each node':
            self.action = SGmode.RAND

    def next(self):
        seed = self.base_value

        if self.action == SGmode.INCR:
            self.base_value += 1
            if self.base_value > 1125899906842624:
                self.base_value = 0
        elif self.action == SGmode.DECR:
            self.base_value -= 1
            if self.base_value < 0:
                self.base_value = 1125899906842624
        elif self.action == SGmode.RAND:
            self.base_value = random.randint(0, 1125899906842624)

        return seed


def control_seed(v):
    action = v['inputs']['action']
    value = v['inputs']['value']

    if action == 'increment' or action == 'increment for each node':
        value += 1
        if value > 1125899906842624:
            value = 0
    elif action == 'decrement' or action == 'decrement for each node':
        value -= 1
        if value < 0:
            value = 1125899906842624
    elif action == 'randomize' or action == 'randomize for each node':
        value = random.randint(0, 1125899906842624)

    v['inputs']['value'] = value

    return value


def prompt_seed_update(json_data):
    seed_widget_map = json_data['extra_data']['extra_pnginfo']['workflow']['seed_widgets']
    value = None
    mode = None
    node = None
    action = None

    for k, v in json_data['prompt'].items():
        cls = v['class_type']
        if cls == 'GlobalSeed //Inspire':
            mode = v['inputs']['mode']
            action = v['inputs']['action']
            value = v['inputs']['value']
            node = k, v

    # control before generated
    if mode is not None and mode:
        value = control_seed(node[1])

    if value is not None:
        seed_generator = SeedGenerator(value, action)

        for k, v in json_data['prompt'].items():
            if k not in seed_widget_map:
                continue

            if 'seed' in v['inputs']:
                if isinstance(v['inputs']['seed'], int):
                    v['inputs']['seed'] = seed_generator.next()

    # control after generated
    if mode is not None and not mode:
        control_seed(node[1])

    return value is not None


def workflow_seed_update(json_data):
    nodes = json_data['extra_data']['extra_pnginfo']['workflow']['nodes']
    seed_widget_map = json_data['extra_data']['extra_pnginfo']['workflow']['seed_widgets']
    prompt = json_data['prompt']

    updated_seed_map = {}
    value = None
    for node in nodes:
        if node['type'] == 'GlobalSeed //Inspire':
            value = prompt[str(node['id'])]['inputs']['value']
            node['widgets_values'][0] = value
        elif str(node['id']) in seed_widget_map:
            node_id = str(node['id'])
            widget_idx = seed_widget_map[node_id]
            seed = prompt[str(node['id'])]['inputs']['seed']
            node['widgets_values'][widget_idx] = seed
            updated_seed_map[node_id] = seed

    server.PromptServer.instance.send_sync("inspire-global-seed", {"id": node_id, "value": value, "seed_map": updated_seed_map})


def onprompt(json_data):
    is_changed = prompt_seed_update(json_data)
    if is_changed:
        workflow_seed_update(json_data)

    return json_data


server.PromptServer.instance.add_on_prompt_handler(onprompt)


NODE_CLASS_MAPPINGS = {}
NODE_DISPLAY_NAME_MAPPINGS = {}