import yaml, os, pathlib

def load_config(path="configs/default.yaml"):
    with open(path, "r") as f:
        cfg = yaml.safe_load(f)
    # make future cache dirs safely, if you add them later
    pathlib.Path("data").mkdir(exist_ok=True)
    return cfg
