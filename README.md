# Turok

CLI torrent search. Searches 1337x, The Pirate Bay, and RARBG in parallel.

![Turok TUI](assets/screenshot.png)

## Install

```bash
pipx install git+https://github.com/rlt-lab/turok.git
```

Or with pip: `pip install git+https://github.com/rlt-lab/turok.git`

## Use

Turok has two interfaces: a full-screen TUI and a simple CLI.

### TUI

```bash
turok-tui
```

Type to search, browse results with arrow keys or `j`/`k`.

| Key | Action |
|-----|--------|
| `Enter` | Send to torrent client |
| `y` | Copy magnet to clipboard |
| `o` | Open detail page in browser |
| `g` / `G` | Jump to first / last |
| `q` | Quit |
| `?` | Help |

### CLI

```bash
turok ubuntu          # search
turok "linux mint"    # multi-word
turok ubuntu -n 20    # 20 results (default: 10)
turok debian -s size  # sort by size (default: seeders)
```

Results print to stdout. Type a number to send that torrent to your client, or `q` to quit.

### Add custom sites

```bash
turok add https://example-torrent-site.com
turok sites           # list configured sites
```

Turok will auto-detect the site's search structure and save it for future searches.

## Dev

Requires [uv](https://docs.astral.sh/uv/).

```bash
git clone https://github.com/rlt-lab/turok.git
cd turok
uv run turok-tui      # run TUI
uv run turok ubuntu   # run CLI
```
