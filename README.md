# Turok

CLI torrent search. Searches 1337x, The Pirate Bay, and RARBG in parallel.

## Install

```bash
git clone https://github.com/youruser/turok.git
cd turok
uv sync
```

## Use

```bash
uv run turok matrix          # search
uv run turok "the matrix"    # multi-word search
uv run turok matrix -n 20    # show 20 results (default: 10)
uv run turok matrix -s size  # sort by size (default: seeders)
```

Results show title, size, seeders/leechers, and source:

```
[1] The Matrix (1999) 1080p (1.9 GB) - 745↑ 44↓ [TPB]
[2] The Matrix Reloaded (1999) 1080p (1.9 GB) - 361↑ 31↓ [TPB]
```

Type a number to send that torrent to your default client. Type `q` to quit.
