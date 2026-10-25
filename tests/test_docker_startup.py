import json
import shlex
from pathlib import Path


def test_docker_startup_command_runs_migrations_then_execs_uvicorn():
    dockerfile = Path(__file__).parents[1] / "Dockerfile"
    command_line = next(line for line in dockerfile.read_text().splitlines() if line.startswith("CMD "))
    command = json.loads(command_line.removeprefix("CMD "))

    assert command[:2] == ["sh", "-c"]
    tokens = shlex.split(command[2])
    migration_end = tokens.index("head")
    assert tokens[migration_end + 1 : migration_end + 3] == ["&&", "exec"]
    assert tokens[migration_end + 3 : migration_end + 5] == ["uv", "run"]
    assert tokens[-2:] == ["--port", "${PORT:-8000}"]
