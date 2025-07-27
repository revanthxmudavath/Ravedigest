## RaveDigest – AI-Powered Digest Generator

RaveDigest collects trending content, analyzes it with LLMs, and publishes digests to Notion.

```mermaid
graph LR
    Collector --> Analyzer --> Composer --> NotionWorker
    Collector --> Redis
    All --> Postgres
