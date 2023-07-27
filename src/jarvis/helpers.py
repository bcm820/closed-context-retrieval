import os

from typing import List, Tuple


def select(category: str, options: List[str]):
    options.sort()
    match len(options):
        case 0:
            print(f'No {category}s found!')
            exit(1)
        case 1:
            return options[0]
        case _:
            input_message = f'Select a {category} (1-{len(options)}):\n'
            for idx, item in enumerate(options):
                input_message += f'{idx+1}) {item}\n'
            input_message += 'Your choice: '
            user_input = ''
            while user_input not in map(str, range(1, len(options) + 1)):
                user_input = input(input_message)
            return options[int(user_input)-1]


def get_model() -> Tuple[str, str]:
    typs = os.path.join('data', 'models')
    options = [f for f in os.listdir(typs) if f not in ['embeddings']]
    typ = select('model type', options)
    options = [f for f in os.listdir(
        os.path.join(typs, typ)) if f.endswith('.bin')]
    model = select('model', options)
    return (typ, os.path.join('data', 'models', typ, model))
