#!/bin/bash
echo "⏰ Running Notion publish cron job..."
curl -X POST http://localhost:8004/notion/publish-latest
