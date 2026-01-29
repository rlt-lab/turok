# Turok

CLI torrent search. Searches 1337x, The Pirate Bay, and RARBG in parallel.

![Turok TUI](assets/screenshot.png)

## Install

**pipx** (recommended - installs globally in isolated env):
```bash
pipx install git+https://github.com/rlt-lab/turok.git
```

**pip**:
```bash
pip install git+https://github.com/rlt-lab/turok.git
```

**From source**:
```bash
git clone https://github.com/rlt-lab/turok.git
cd turok
pip install .
```

## Use

```bash
turok ubuntu          # search
turok "linux mint"    # multi-word search
turok ubuntu -n 20    # show 20 results (default: 10)
turok debian -s size  # sort by size (default: seeders)
```

Results show title, size, seeders/leechers, and source:

```
[1] Ubuntu 24.04 Desktop ISO (4.2 GB) - 1523↑ 42↓ [TPB]
[2] Ubuntu 24.04 Server ISO (2.1 GB) - 892↑ 15↓ [1337x]
```

Type a number to send that torrent to your default client. Type `q` to quit.
