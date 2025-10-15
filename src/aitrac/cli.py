"""AiTrac CLI entry point"""

import argparse
import asyncio
import os
import sys
from pathlib import Path

import uvicorn


def init_project():
    """Initialize .aitrac directory and configuration"""
    aitrac_dir = Path(".aitrac")
    aitrac_dir.mkdir(exist_ok=True)
    
    config_file = aitrac_dir / "config.json"
    if not config_file.exists():
        import json
        default_config = {
            "project_prefix": "at",
            "source_id": "local"
        }
        with open(config_file, "w") as f:
            json.dump(default_config, f, indent=2)
    
    print(f"Initialized aitrac in {aitrac_dir.absolute()}")


def serve(host: str = "127.0.0.1", port: int = 8080, reload: bool = False):
    """Start the aitrac server"""
    os.environ["AITRAC_HOST"] = host
    os.environ["AITRAC_PORT"] = str(port)
    
    uvicorn.run(
        "aitrac.main:app",
        host=host,
        port=port,
        reload=reload,
        log_level="info"
    )


def dev():
    """Start development environment with live reload"""
    import subprocess
    import sys
    from pathlib import Path
    
    dev_script = Path(__file__).parent.parent.parent / "dev.py"
    if dev_script.exists():
        subprocess.run([sys.executable, str(dev_script)])
    else:
        print("Development script not found, starting backend only with reload...")
        serve(reload=True)


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(description="AiTrac - AI Agent Issue Tracker")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Init command
    subparsers.add_parser("init", help="Initialize aitrac in current directory")
    
    # Serve command
    serve_parser = subparsers.add_parser("serve", help="Start aitrac server")
    serve_parser.add_argument("--host", default="127.0.0.1", help="Host to bind to")
    serve_parser.add_argument("--port", type=int, default=8080, help="Port to bind to")
    serve_parser.add_argument("--reload", action="store_true", help="Enable auto-reload")
    
    # Dev command
    subparsers.add_parser("dev", help="Start development server with live reload")
    
    args = parser.parse_args()
    
    if args.command == "init":
        init_project()
    elif args.command == "serve":
        serve(args.host, args.port, args.reload)
    elif args.command == "dev":
        dev()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()