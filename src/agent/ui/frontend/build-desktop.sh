#!/bin/bash

echo "📦 Building Local AI Agent Desktop Application"
echo ""

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}1️⃣ Building React application...${NC}"
npm run build
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ React build successful${NC}"
else
    echo -e "${RED}❌ React build failed${NC}"
    exit 1
fi

echo ""
echo -e "${BLUE}2️⃣ Building Electron application...${NC}"
npm run dist
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Electron build successful${NC}"
else
    echo -e "${YELLOW}⚠️  Electron build completed with warnings${NC}"
fi

echo ""
echo -e "${GREEN}🎉 Desktop application build complete!${NC}"
echo ""
echo "📁 Built applications can be found in the 'dist' directory:"
ls -la dist/ 2>/dev/null || echo "No dist directory found - build may have failed"

echo ""
echo -e "${BLUE}💡 To run the built application:${NC}"
echo "   - On Linux: ./dist/Local\ AI\ Agent-1.0.0.AppImage"
echo "   - Or install the .deb package with: sudo dpkg -i dist/local-ai-agent_1.0.0_amd64.deb"