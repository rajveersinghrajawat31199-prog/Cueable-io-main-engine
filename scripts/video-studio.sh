#!/usr/bin/env bash
# video-studio.sh — Orchestrate staged video production
# Usage: ./scripts/video-studio.sh <project-name> <stage> [options]
#
# Stages:
#   init       — Initialize a new HyperFrames project
#   build      — Build the HTML composition (runs Claude Code)
#   verify     — Run lint, check, snapshot
#   preview    — Open Studio preview
#   render     — Render to MP4

set -euo pipefail

WORKSPACE="$HOME/hyperframe-studio"
STAGE="${1:-help}"
PROJECT="${2:-}"
OPTION="${3:-}"

case "$STAGE" in
  init)
    if [ -z "$PROJECT" ]; then
      echo "Usage: $0 init <project-name> [workflow]"
      echo "Workflows: motion-graphics, faceless-explainer, product-launch-video, general-video"
      exit 1
    fi
    WORKFLOW="${OPTION:-general-video}"
    PROJECT_DIR="$WORKSPACE/videos/$PROJECT"
    
    echo "🎬 Initializing video project: $PROJECT (workflow: $WORKFLOW)"
    cd "$WORKSPACE"
    npx hyperframes init "videos/$PROJECT" --non-interactive --example=blank --skill="$WORKFLOW"
    
    echo ""
    echo "✅ Project created at: $PROJECT_DIR"
    echo "📝 Next steps:"
    echo "   1. Write BRIEF.md with your creative direction"
    echo "   2. Run: $0 build $PROJECT"
    ;;

  build)
    if [ -z "$PROJECT" ]; then
      echo "Usage: $0 build <project-name> [claude-prompt]"
      exit 1
    fi
    PROJECT_DIR="$WORKSPACE/videos/$PROJECT"
    
    if [ ! -d "$PROJECT_DIR" ]; then
      echo "❌ Project not found: $PROJECT_DIR"
      echo "   Run: $0 init $PROJECT [workflow]"
      exit 1
    fi
    
    echo "🔨 Building composition for: $PROJECT"
    cd "$PROJECT_DIR"
    
    # Determine the workflow from BRIEF.md or hyperframes.json
    WORKFLOW=$(grep -oP 'workflow:\s*\K\S+' BRIEF.md 2>/dev/null || echo "general-video")
    
    PROMPT="${OPTION:-"Using /hyperframes, build the composition for this project. Follow the storyboard at STORYBOARD.md and the design in frame.md. Write valid HyperFrames HTML with paused GSAP timelines on window.__timelines."}"
    
    echo "🤖 Launching Claude Code (workflow: $WORKFLOW)..."
    claude -p "$PROMPT" --max-turns 20 2>&1
    
    echo ""
    echo "✅ Build complete. Checking composition..."
    npx hyperframes lint . 2>&1 || true
    ;;

  verify)
    if [ -z "$PROJECT" ]; then
      echo "Usage: $0 verify <project-name>"
      exit 1
    fi
    PROJECT_DIR="$WORKSPACE/videos/$PROJECT"
    cd "$PROJECT_DIR"
    
    echo "🔍 Verifying composition..."
    echo "--- Lint ---"
    npx hyperframes lint . 2>&1
    echo ""
    echo "--- Check ---"
    npx hyperframes check . 2>&1
    echo ""
    echo "✅ Verification complete."
    ;;

  preview)
    if [ -z "$PROJECT" ]; then
      echo "Usage: $0 preview <project-name>"
      exit 1
    fi
    PROJECT_DIR="$WORKSPACE/videos/$PROJECT"
    cd "$PROJECT_DIR"
    
    echo "👁️  Opening Studio preview..."
    npx hyperframes preview --background
    echo "✅ Preview running. Open http://localhost:3000 in your browser."
    echo "   Stop with: npx hyperframes preview --stop"
    ;;

  render)
    if [ -z "$PROJECT" ]; then
      echo "Usage: $0 render <project-name> [quality]"
      exit 1
    fi
    PROJECT_DIR="$WORKSPACE/videos/$PROJECT"
    QUALITY="${OPTION:-high}"
    cd "$PROJECT_DIR"
    
    echo "🎬 Rendering video (quality: $QUALITY)..."
    mkdir -p renders
    npx hyperframes render . --quality "$QUALITY" -o ./renders/video.mp4
    
    if [ -f renders/video.mp4 ]; then
      echo ""
      echo "✅ Render complete!"
      echo "📁 Output: $PROJECT_DIR/renders/video.mp4"
      ffprobe -v quiet -show_entries format=duration,size -of default=noprint_wrappers=1 renders/video.mp4 2>&1
    else
      echo "❌ Render failed — no output file."
      exit 1
    fi
    ;;

  status)
    echo "📊 Video Studio Status"
    echo "====================="
    echo ""
    echo "Workspace: $WORKSPACE"
    echo ""
    if [ -d "$WORKSPACE/videos" ]; then
      echo "Projects:"
      for d in "$WORKSPACE/videos"/*/; do
        if [ -d "$d" ]; then
          NAME=$(basename "$d")
          HAS_BRIEF="❌"
          HAS_STORY="❌"
          HAS_HTML="❌"
          HAS_MP4="❌"
          [ -f "$d/BRIEF.md" ] && HAS_BRIEF="✅"
          [ -f "$d/STORYBOARD.md" ] && HAS_STORY="✅"
          [ -f "$d/compositions/index.html" ] && HAS_HTML="✅"
          [ -f "$d/renders/video.mp4" ] && HAS_MP4="✅"
          echo "  📁 $NAME"
          echo "     Brief: $HAS_BRIEF | Storyboard: $HAS_STORY | HTML: $HAS_HTML | MP4: $HAS_MP4"
        fi
      done
    else
      echo "No projects yet."
    fi
    echo ""
    echo "Claude Code: $(claude --version 2>&1)"
    echo "HyperFrames: $(npx hyperframes --version 2>&1 | head -1)"
    ;;

  help|*)
    echo "Video Studio — SaaS & Tech Video Factory"
    echo "========================================="
    echo ""
    echo "Usage: $0 <command> <project-name> [options]"
    echo ""
    echo "Commands:"
    echo "  init <name> [workflow]   Initialize a new video project"
    echo "  build <name> [prompt]    Build the HTML composition"
    echo "  verify <name>            Run lint + check"
    echo "  preview <name>           Open Studio preview"
    echo "  render <name> [quality]  Render to MP4"
    echo "  status                   Show all projects and status"
    echo ""
    echo "Workflows:"
    echo "  motion-graphics          Short motion graphic (5-30s)"
    echo "  faceless-explainer       Topic explainer with invented visuals"
    echo "  product-launch-video     Website product demo"
    echo "  general-video            Custom video (any length)"
    echo ""
    echo "Examples:"
    echo "  $0 init acme-demo motion-graphics"
    echo "  $0 build acme-demo"
    echo "  $0 render acme-demo high"
    echo ""
    echo "Projects live in: $WORKSPACE/videos/"
    ;;
esac
