from src.utils.config import load_config

def run():
    cfg = load_config()
    print(f"[{cfg['project']}] device={cfg['device']}")

if __name__ == "__main__":
    run()
