import os
import subprocess
import time

def test():
    env = os.environ.copy()
    from dotenv import load_dotenv
    load_dotenv()
    
    env["ALPACA_API_KEY"] = os.getenv("ALPACA_API_KEY")
    env["ALPACA_SECRET_KEY"] = os.getenv("ALPACA_SECRET_KEY")
    env["ALPACA_PAPER_TRADE"] = "true"
    
    print(f"Key: {env.get('ALPACA_API_KEY')}")
    
    args = ["uvx", "--quiet", "--with", "fastmcp==3.4.7", "alpaca-mcp-server==2.3.0", "serve"]
    p = subprocess.Popen(args, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    time.sleep(5)
    
    if p.poll() is not None:
        print(f"CRASHED: {p.returncode}")
        print(f"STDOUT: {p.stdout.read()}")
        print(f"STDERR: {p.stderr.read()}")
    else:
        print("SUCCESS! Running...")
        p.kill()

if __name__ == "__main__":
    test()
