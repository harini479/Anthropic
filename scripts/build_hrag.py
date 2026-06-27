"""
CLI script to trigger the H-RAG build process.
"""

import sys
import os
import argparse

# Add the project root to sys.path so we can import from src
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.hrag_builder import build_hrag


def main():
    parser = argparse.ArgumentParser(description="Build H-RAG knowledge base")
    parser.add_argument("--force", action="store_true", help="Clear existing data before building")
    parser.add_argument("--node", type=str, choices=["anthropic", "projects"], help="Build a specific node")
    parser.add_argument("--all", action="store_true", help="Build all nodes")

    args = parser.parse_args()

    if args.all or not args.node:
        print("Building ALL nodes...")
        build_hrag(force=args.force, node_name="anthropic")
        print("\n" + "="*50 + "\n")
        build_hrag(force=args.force, node_name="projects")
    else:
        build_hrag(force=args.force, node_name=args.node)


if __name__ == "__main__":
    main()
