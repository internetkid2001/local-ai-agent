# CLAUDE.md - Local AI Agent Project Instructions

## 🎯 Project Overview

You are about to work on a Local AI Agent with MCP (Model Context Protocol) Integration. This is a sophisticated system that orchestrates between local LLMs (via Ollama) and advanced AI services (Claude Code, Google CLI) to provide intelligent computer automation with visual context awareness.

## 📋 Pre-Development Analysis

Before starting any code, please analyze and confirm understanding of:

### 1. System Architecture Review
- [ ] Review the complete context documents in `claude code context` folder
- [ ] Understand the MCP server architecture
- [ ] Identify the role of each component
- [ ] Note the integration points between local and advanced AI

### 2. Development Plan Understanding
- [ ] Review `claude-code-dev-plan` 
- [ ] Identify which phase and session to start with
- [ ] Check token budget for current session
- [ ] Understand commit and documentation requirements

### 3. Current Project State
```bash
# Run these commands to analyze current state:
ls -la                          # Check if project exists
git status                      # Check git state
cat docs/progress/CURRENT_PHASE.md  # Current phase (if exists)
cat docs/progress/NEXT_STEPS.md     # Where to continue (if exists)
```

### 4. Environment Check
- [ ] Verify Python 3.8+ is available
- [ ] Check if Ollama is installed
- [ ] Identify available GPU (AMD Radeon RX 6600 XT)
- [ ] Note system specs (AMD Ryzen 7 3700X, 31GB RAM)

## 🚀 Starting Development

### For New Project (First Time)

```bash
# 1. Initialize project structure
mkdir -p ~/projects/local-ai-agent
cd ~/projects/local-ai-agent
git init

# 2. Create initial structure
mkdir -p src/{agent,mcp_client,ui,utils} \
         mcp-servers/{filesystem,system,desktop,ai_bridge,screenshot_context} \
         config docs/progress tests examples

# 3. Create progress tracking files
cat > docs/progress/CURRENT_PHASE.md << 'EOF'
# Current Phase: 1
## Session: 1.1
## Status: Starting Project Setup
## Started: [DATE]
EOF

# 4. Initialize git
git add .
git commit -m "[PHASE-1] Initial: Project structure created"

# 5. Create GitHub repository (manual step)
# Then: git remote add origin https://github.com/USERNAME/local-ai-agent.git
# git push -u origin main
# git checkout -b dev-phase-1
```

### For Continuing Development

```bash
# 1. Navigate to project
cd ~/projects/local-ai-agent

# 2. Check current state
git pull origin dev-phase-X
cat docs/progress/CURRENT_PHASE.md
cat docs/progress/NEXT_STEPS.md

# 3. Continue from last point
# [Follow instructions in NEXT_STEPS.md]
```

## 📝 Development Session Protocol

### At Session Start

1. **Announce session details**:
   ```
   Starting Session X.Y: [Component Name]
   Token Budget: ~XXk tokens
   Objectives: [List main goals]
   ```

2. **Update tracking**:
   ```bash
   # Update CURRENT_PHASE.md with session start time
   # Create SESSION_NOTES.md for this session
   ```

### During Development

1. **Commit regularly** (every 30-45 minutes):
   ```bash
   git add -A
   git commit -m "[PHASE-X] Component: Specific change description"
   git push origin dev-phase-X
   ```

2. **Document decisions** in `ARCHITECTURE_DECISIONS.md`

3. **Track progress** - update checkboxes in `COMPLETION_STATUS.md`

4. **Monitor token usage** - self-assess periodically:
   ```
   "Based on our conversation, I estimate we're at approximately X% token capacity"
   ```

### At Session End

1. **Complete documentation**:
   - Update `SESSION_NOTES.md` with accomplishments
   - Create detailed `NEXT_STEPS.md`
   - Update `COMPLETION_STATUS.md`

2. **Final commit and push**:
   ```bash
   git add -A
   git commit -m "[PHASE-X] Session X.Y: Summary of session work"
   git push origin dev-phase-X
   ```

3. **Prepare handoff**:
   ```markdown
   # In NEXT_STEPS.md include:
   - Exact file and line to continue from
   - Any unresolved issues
   - Context that matters for next session
   ```

## 🏗️ Phase-Specific Instructions

### Phase 1: Foundation (Sessions 1.1-1.3)
Focus: Basic infrastructure
- Start with MCP client base implementation
- Add Ollama integration with function calling
- Implement filesystem MCP server with security

### Phase 2: Core Intelligence (Sessions 2.1-2.4)
Focus: Agent decision-making
- Build task routing system
- Implement context management
- Add screenshot capabilities
- Create security framework

### Phase 3: Advanced AI Integration (Sessions 3.1-3.3)
Focus: Claude Code and Google CLI integration
- Create AI Bridge MCP server
- Implement context packaging
- Build decision engine

### Phase 4: UI & Polish (Sessions 4.1-4.3)
Focus: User interfaces and testing
- Create CLI interface
- Build web API
- Comprehensive testing

## 🧪 Testing Requirements

For each component:
1. Write unit tests alongside implementation
2. Aim for >80% code coverage
3. Create integration tests for workflows
4. Document test scenarios

## 📊 Progress Reporting

At any time, be ready to report:
- Current phase and session
- Percentage complete for current session
- Files created/modified
- Tests written and passing
- Any blockers or issues

## ⚠️ Important Reminders

1. **Security First**: Never bypass security measures for convenience
2. **Document Everything**: Future sessions depend on good documentation
3. **Test Frequently**: Catch issues early
4. **Commit Often**: Never lose more than 45 minutes of work
5. **Ask Questions**: If requirements unclear, ask for clarification

## 🔄 Context Management

### When to request new chat instance:
- Token usage approaching 70% (≈70k tokens)
- Completing a major phase
- After complex debugging sessions
- When context becomes confused

### How to request:
```
"I've completed [work done] and we're approaching token capacity. 
Please start a new chat to continue with [next task].
Key context to carry forward: [important points]"
```

## 💡 Quick Reference

### Git Commands
```bash
# Regular commits
git add -A && git commit -m "[PHASE-X] Component: Change"

# Check status
git status
git log --oneline -5

# Push changes
git push origin dev-phase-X
```

### Project Structure
```
local-ai-agent/
├── src/           # Main application code
├── mcp-servers/   # MCP server implementations  
├── config/        # Configuration files
├── tests/         # Test suites
├── docs/          # Documentation
│   └── progress/  # Progress tracking
└── examples/      # Usage examples
```

### Key Files to Update
1. `docs/progress/CURRENT_PHASE.md` - Active work
2. `docs/progress/SESSION_NOTES.md` - Per session
3. `docs/progress/NEXT_STEPS.md` - Handoff info
4. `docs/progress/COMPLETION_STATUS.md` - Overall progress
5. `docs/progress/ARCHITECTURE_DECISIONS.md` - Design choices

## 🎬 Ready to Start?

1. Confirm you understand the project architecture
2. Identify which session to begin/continue
3. Set up progress tracking
4. Start coding!

Remember: Quality over speed. Well-documented, tested code is the goal.

---

*This file should be the first thing Claude Code reads when starting work on the project.*
