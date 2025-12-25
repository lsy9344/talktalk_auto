# Architecture Documentation Index

This directory contains the architecture documentation for TalkTalk Auto, organized for easy navigation.

## Reading Guide

For a comprehensive understanding of the system, read the documents in this order:

1. **[System Overview (High Level Architecture)](../architecture.md#high-level-architecture)** - Start here to understand the overall system design, AWS components, and data flow
2. **[Tech Stack](tech-stack.md)** - Technologies, libraries, and AWS services used in the project
3. **[Coding Standards](coding-standards.md)** - Development rules and testing guidelines that all code must follow
4. **[Source Tree](source-tree.md)** - Project folder structure (target architecture)

## Quick Links

### Core Architecture Documents

- **[Complete Architecture Document](../architecture.md)** - Full architecture documentation (includes all sections below)
- **[High Level Architecture](../architecture.md#high-level-architecture)** - System overview, AWS components summary, and data flow
- **[High Level Project Diagram](../architecture.md#high-level-project-diagram)** - Mermaid diagram showing all AWS components and connections
- **[Tech Stack](tech-stack.md)** - Technologies and AWS services
- **[Coding Standards](coding-standards.md)** - Development and testing standards
- **[Source Tree](source-tree.md)** - Target folder structure
- **[Implementation Notes (실수 방지 메모)](implementation-notes.md)** - Common mistakes and prevention guidelines for TalkTalk integration

### Implementation Status

**Current Status (as of 2025-12-21):**

- ✅ **Implemented:** Ingest Lambda (basic structure created)
- ✅ **Implemented:** Infrastructure templates (SAM template.yaml exists)
- ⏳ **Pending:** Worker Lambda
- ⏳ **Pending:** Indexer Lambda
- ⏳ **Pending:** Shared layer (talktalk_shared package)
- ⏳ **Pending:** Full test suite

**Note:** The source tree documentation (`source-tree.md`) represents the **target architecture** - the goal we are building towards. Not all folders/files exist yet. Use the status list above to see current progress.

## Document Maintenance

- The **complete architecture document** (`docs/architecture.md`) contains all architecture information in one file
- The **sharded documents** (this directory) split specific sections for easier reading and reference
- When updating architecture, update both locations to keep them in sync
