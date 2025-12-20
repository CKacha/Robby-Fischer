# CHESSARM

Chess-playing robot arm system:
Camera -> Board State (FEN) -> Stockfish -> Plan -> Robot Macros -> Verify -> Repeat

## Quickstart (Ubuntu 24.04)

### 1) System deps
```bash
sudo apt update
sudo apt install -y stockfish v4l-utils python3-venv
sudo usermod -aG dialout $USER
# log out/in so dialout permission applies
