import yaml

from jarvis.app import App
from jarvis.config import Config
from jarvis.helpers import get_model


def main():
    with open('config.yaml') as stream:
        data = yaml.safe_load(stream)
    typ, path = get_model()
    data[typ]['model_path'] = path
    conf = Config(**data)
    app = App(conf)
    app.run()


if __name__ == "__main__":
    main()
