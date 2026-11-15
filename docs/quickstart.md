# Quick start

Four commands, in PowerShell 7 (`pwsh`), with Python 3 and git on PATH. No other tools are needed.

```text
git clone https://github.com/BarabashkaD/retroICs; cd retroICs
python -B -m unittest discover -s tools/tests -v
python -B tools/check_records.py
python -B tools/check_privacy.py --all
```

1. Clone. No submodules: `retroICs` depends on nothing.
2. The tools' own tests (the simulation ones need Icarus Verilog 13.0, else they skip).
3. The record checker: registry, records, source IDs.
4. The privacy checker on the working tree and every commit; it must pass before every push.

Next: `docs/agents/global.md` (the rules), `docs/conventions.md` (the IC folder contract), the IC
folder you work on and its `AGENTS.md`. The simulation runner (`simrun`): `AGENTS.md`, Commands.
