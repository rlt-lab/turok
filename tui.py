#!/usr/bin/env python3
"""Turok TUI entry point."""

from ui.app import TurokApp


def main():
    """Run the Turok TUI."""
    app = TurokApp()
    app.run()


if __name__ == "__main__":
    main()
