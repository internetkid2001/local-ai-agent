# Project Vision & User Stories

## The Vision: A Local, Jarvis-Like Assistant

The ultimate goal of this project is to create a local, private, and highly capable AI assistant, akin to **Jarvis** from the Marvel comics. This agent should be a proactive and context-aware partner, capable of helping with a wide range of everyday digital tasks, from simple file management to complex, multi-step creative and technical work.

**Core Principles:**
-   **Privacy-First**: All core operations and context should remain on the local machine.
-   **Context-Aware**: The agent must understand the user's screen, active applications, and project context to provide relevant assistance.
-   **Extensible**: The MCP server architecture should allow for easy addition of new tools and capabilities.
-   **User-Centric**: The agent should reduce cognitive load and make interacting with a computer more natural and efficient.

---

## User Personas

To guide development, we will focus on three key user personas who represent the spectrum of tasks our "Jarvis" should handle.

### 1. Priya, The Developer
-   **Role**: Software Engineer
-   **Needs**: Help with writing, debugging, and managing code; automating development workflows; and researching technical solutions.
-   **Goal**: To spend more time on complex problem-solving and less on repetitive coding and setup tasks.

### 2. Leo, The Researcher & Student
-   **Role**: University Student / Content Creator
-   **Needs**: Assistance with gathering information, summarizing articles and videos, organizing notes, and creating presentations.
-   **Goal**: To accelerate his research and learning process and streamline content creation.

### 3. Maria, The Everyday User
-   **Role**: Manages a small business and personal digital life.
-   **Needs**: Help with organizing files, managing emails, setting reminders, and performing common computer operations without needing to remember specific steps.
-   **Goal**: To make her computer feel less like a tool she has to operate and more like an assistant that works for her.

### 4. Alex, The Homelab Enthusiast
-   **Role**: IT Professional / Hobbyist
-   **Needs**: A way to manage and query a large, complex file system across a local network (NAS, servers); help with organizing and archiving old projects.
-   **Goal**: To interact with their entire homelab infrastructure using natural language, without needing to manually `ssh` into different machines or navigate complex directory trees.

---

## User Stories

These stories break down the high-lvel vision into concrete, actionable development goals.

### For Priya (The Developer)

-   **As a developer, I want to** point the agent to a script with an error and say, "Debug this," **so that** the agent can use visual context and code analysis to suggest a fix.
-   **As a developer, I want to** describe a new feature in plain English, **so that** the agent can generate the boilerplate code, including files, classes, and functions, directly in my project.
-   **As a developer, I want to** say, "Refactor this module to improve performance," **so that** the agent can analyze the code and apply optimizations, explaining the changes it made.
-   **As a developer, I want to** ask, "What were the last 5 commits about?" **so that** I can get a quick summary of recent changes in the project.

### For Leo (The Researcher & Student)

-   **As a researcher, I want to** give the agent a list of URLs to academic papers and say, "Summarize these and create a bibliography," **so that** I can quickly get up to speed on a new topic.
-   **As a student, I want to** have the agent watch a video lecture with me and say, "Take notes on the key concepts," **so that** I can focus on the content while the agent creates a study guide.
-   **As a content creator, I want to** say, "Find me royalty-free images of futuristic cities," **so that** the agent can search the web and download relevant images to a folder.
-   **As a student, I want to** say, "Turn my research notes into a slide deck outline," **so that** the agent can structure my raw text into a presentation format.

### For Maria (The Everyday User)

-   **As an everyday user, I want to** say, "My desktop is a mess, please clean it up," **so that** the agent can organize files into folders based on their type (e.g., Documents, Images, Videos).
-   **As an everyday user, I want to** ask, "Where is that invoice from last month?" **so that** the agent can search my files and emails to find the correct document.
-   **As an everyday user, I want to** say, "Remind me to pay the electricity bill when I open my banking website," **so that** the agent can set a context-aware reminder that triggers based on my actions.
-   **As an everyday user, I want to** say, "Help me book a flight to New York for next weekend," **so that** the agent can open a travel website and assist me by filling in the forms based on my request.

### For Alex (The Homelab Enthusiast)

-   **As a homelab user, I want the agent to** periodically scan my NAS and homelab file systems, **so that** it can build and maintain an index for natural language queries.
-   **As a homelab user, I want to** ask, "Where are the project files for that old Raspberry Pi weather station I built?" **so that** the agent can search its index and provide me with a direct path to the files on my NAS.
-   **As a homelab user, I want to** say, "Take all the '.iso' files from my Downloads folder and move them to the 'ISOs' share on my NAS," **so that** the agent can perform file operations across different machines on my network.
-   **As a homelab user, I want to** say, "Archive all projects in my 'Active Projects' folder that haven't been modified in over a year," **so that** the agent can intelligently organize and archive my files based on metadata.
-   **(Long-term Goal) As a homelab user, I want to** eventually expose this agent through a secure, web-based, ChatGPT-like application, **so that** my family or team members can log in from any device and find files on our home network that they have permission to see.
