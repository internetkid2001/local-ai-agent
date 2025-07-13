# Project Roadmap & Future Features

## Vision Statement

This document outlines the planned evolution of the Local AI Agent. The goal is to progress from a capable local assistant to a comprehensive, Jarvis-like intelligence for managing a personal digital ecosystem, with a strong focus on homelab and NAS integration.

---

## Phase 1: Core Feature - Homelab & NAS Integration

This is the primary near-term goal. The objective is to make the agent the central brain for a user's entire local network file system.

### 1.1: File System Indexing Engine
-   **Feature**: The agent will periodically and intelligently scan the file systems of designated network locations (NAS shares, server directories).
-   **Implementation Details**:
    -   Create a persistent index (e.g., using SQLite and a vector database like LanceDB) to store file metadata (name, path, size, modification date) and, optionally, content-derived vectors.
    -   The scanner should be efficient, respecting `.gitignore`-style rules and avoiding unnecessary re-indexing of unchanged directories.
    -   The agent needs to handle credentials securely to access network shares (e.g., SMB, NFS).

### 1.2: Natural Language File Search
-   **Feature**: Allow the user to find files and projects across their entire network using conversational queries.
-   **User Stories**:
    -   *"Where are the project files for that old Raspberry Pi weather station I built?"*
    -   *"Find the presentation I made about Q3 earnings last year."*
    -   *"Show me all the photos from my trip to Italy in 2023."*
-   **Implementation Details**: This will involve converting the user's query into an embedding and performing a vector search against the indexed file data.

### 1.3: Cross-System File Management
-   **Feature**: Empower the agent to move, copy, organize, and delete files across different machines on the local network.
-   **User Stories**:
    -   *"Take all the '.iso' files from my Downloads folder and move them to the 'ISOs' share on my NAS."*
    -   *"Create a new folder in my 'Projects' share named 'AI_Agent_Backup' and copy the current project files there."*
-   **Implementation Details**: The `Filesystem` MCP server will need to be enhanced to handle remote paths and authentication for different systems.

### 1.4: Automated File Organization & Archiving
-   **Feature**: The agent can proactively manage files based on user-defined rules or its own learned logic.
-   **User Stories**:
    -   *"Archive all projects in my 'Active Projects' folder that haven't been modified in over a year to the 'Archive' share."*
    -   *"Every night, organize my 'Scans' folder into subfolders by year and month."*

---

## Phase 2: Service & Accessibility

This phase focuses on evolving the agent from a personal tool into a private, multi-user service for a family or small team.

### 2.1: Secure Web Application Front-End
-   **Feature**: Develop a secure, web-based, ChatGPT-like application that acts as the primary interface for the agent.
-   **Implementation Details**:
    -   The agent's core logic will be exposed via a secure REST/WebSocket API.
    -   The front-end will be a modern web application (e.g., using React or Vue) that can be accessed from any device on the local network.

### 2.2: User Authentication & Permissions
-   **Feature**: Implement a user login system and a permissions layer to control access to files and agent capabilities.
-   **Implementation Details**:
    -   Users will have roles (e.g., `admin`, `viewer`, `editor`).
    -   File search results will be filtered based on the logged-in user's permissions, ensuring users can only see files they are authorized to access.

---

## Phase 3: Advanced Intelligence & Proactivity

This long-term phase aims to make the agent truly proactive and deeply integrated into the user's digital life.

### 3.1: Proactive Assistance
-   **Feature**: The agent learns user habits and anticipates needs.
-   **Examples**:
    -   *"I see you've created a new Python file. Should I set up a virtual environment for it?"*
    -   *"You have downloaded several large video files. Should I move them to the NAS to save space?"*

### 3.2: Deeper Application Integration
-   **Feature**: Move beyond desktop control to interact with applications via their APIs.
-   **Examples**: Add events to a calendar, manage tasks in a to-do list application, control a music player.

### 3.3: Conversational Memory & Personalization
-   **Feature**: The agent remembers past interactions and user preferences to provide a more personalized experience.

### 3.4: Voice Interaction
-   **Feature**: Integrate a local voice-to-text and text-to-speech engine for hands-free operation, completing the "Jarvis" experience.
