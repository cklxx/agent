# 🔌 DeepTool API Reference

## Overview

DeepTool provides comprehensive RESTful APIs for integrating with external systems and building custom applications. All APIs follow OpenAPI 3.0 specification and include comprehensive documentation.

## 🚀 Base Configuration

### API Endpoints

| Environment | Base URL | Status |
|-------------|----------|--------|
| **Production** | `https://api.deeptool.tech` | 🟢 Active |
| **Staging** | `https://staging-api.deeptool.tech` | 🟡 Limited |
| **Local Development** | `http://localhost:8000` | 🔧 Development |

### Authentication

```bash
# API Key Authentication
curl -H "Authorization: Bearer YOUR_API_KEY" \
     -H "Content-Type: application/json" \
     https://api.deeptool.tech/v1/agents/execute
```

## 📋 Core APIs

### 🤖 Agent Execution API

#### Execute Agent Task

**POST** `/v1/agents/execute`

Execute a task using the multi-agent system.

```bash
curl -X POST "http://localhost:8000/v1/agents/execute" \
     -H "Content-Type: application/json" \
     -d '{
       "task": "Analyze the security vulnerabilities in authentication system",
       "agent_type": "code_agent",
       "max_iterations": 5,
       "debug": false
     }'
```

**Request Body:**
```json
{
  "task": "string",           // Required: Task description
  "agent_type": "string",     // Optional: code_agent, architect_agent, research_agent
  "max_iterations": 5,        // Optional: Maximum execution iterations
  "debug": false,             // Optional: Enable debug mode
  "workspace": "string",      // Optional: Working directory path
  "locale": "en-US"          // Optional: Language locale
}
```

**Response:**
```json
{
  "success": true,
  "task_id": "task_12345",
  "status": "completed",
  "result": {
    "final_report": "string",
    "iteration_count": 3,
    "execution_time": 12.5,
    "generated_files": ["file1.py", "file2.js"]
  },
  "metadata": {
    "agent_type": "code_agent",
    "timestamp": "2024-01-15T10:30:00Z"
  }
}
```

#### Get Task Status

**GET** `/v1/agents/tasks/{task_id}`

Retrieve the status and results of a specific task.

```bash
curl "http://localhost:8000/v1/agents/tasks/task_12345"
```

**Response:**
```json
{
  "task_id": "task_12345",
  "status": "running",        // pending, running, completed, failed
  "progress": 65,             // Completion percentage
  "current_step": "code_generation",
  "estimated_time_remaining": 45,
  "logs": [
    {
      "timestamp": "2024-01-15T10:30:00Z",
      "level": "INFO",
      "message": "Starting code analysis..."
    }
  ]
}
```

### 🏗️ Architect Agent API

#### Execute Architecture Planning

**POST** `/v1/architect/plan`

Execute technical architecture planning and system design.

```bash
curl -X POST "http://localhost:8000/v1/architect/plan" \
     -H "Content-Type: application/json" \
     -d '{
       "requirements": "Design a microservices architecture for e-commerce",
       "constraints": ["budget: $50k", "timeline: 3 months"],
       "tech_preferences": ["Python", "Docker", "Kubernetes"]
     }'
```

**Request Body:**
```json
{
  "requirements": "string",           // Required: Architecture requirements
  "constraints": ["string"],          // Optional: Project constraints
  "tech_preferences": ["string"],     // Optional: Technology preferences
  "complexity": "medium",             // Optional: low, medium, high
  "output_format": "detailed"        // Optional: brief, detailed, technical
}
```

### 🧠 RAG Enhanced Code API

#### Semantic Code Search

**POST** `/v1/rag/search`

Search for relevant code snippets using natural language.

```bash
curl -X POST "http://localhost:8000/v1/rag/search" \
     -H "Content-Type: application/json" \
     -d '{
       "query": "authentication middleware with JWT validation",
       "repository_path": "/path/to/repo",
       "max_results": 10
     }'
```

**Request Body:**
```json
{
  "query": "string",              // Required: Natural language search query
  "repository_path": "string",    // Optional: Repository to search in
  "max_results": 10,              // Optional: Maximum results to return
  "file_types": ["py", "js"],     // Optional: File extensions to include
  "similarity_threshold": 0.7     // Optional: Minimum similarity score
}
```

**Response:**
```json
{
  "results": [
    {
      "file_path": "src/auth/middleware.py",
      "code_snippet": "def jwt_auth_middleware(request):\n    # JWT validation logic\n    ...",
      "similarity_score": 0.92,
      "line_numbers": [15, 45],
      "context": "Authentication middleware implementation"
    }
  ],
  "total_results": 5,
  "search_time_ms": 245
}
```

#### Generate Context-Aware Code

**POST** `/v1/rag/generate`

Generate code using RAG-enhanced context awareness.

```bash
curl -X POST "http://localhost:8000/v1/rag/generate" \
     -H "Content-Type: application/json" \
     -d '{
       "prompt": "Create a user authentication endpoint",
       "repository_path": "/path/to/repo",
       "follow_patterns": true
     }'
```

### 🔍 Search Integration API

#### Multi-Provider Search

**POST** `/v1/search/query`

Search across multiple providers (Tavily, Brave, DuckDuckGo, Arxiv).

```bash
curl -X POST "http://localhost:8000/v1/search/query" \
     -H "Content-Type: application/json" \
     -d '{
       "query": "latest Python security best practices",
       "providers": ["tavily", "arxiv"],
       "max_results": 5
     }'
```

### 🗺️ Map Services API

#### Location Search

**POST** `/v1/maps/search`

Search for locations using AMAP integration.

```bash
curl -X POST "http://localhost:8000/v1/maps/search" \
     -H "Content-Type: application/json" \
     -d '{
       "query": "restaurants near Beijing",
       "latitude": 39.9042,
       "longitude": 116.4074
     }'
```

### 🔊 Text-to-Speech API

#### Generate Audio

**POST** `/v1/tts/generate`

Convert text to speech using Volcengine TTS.

```bash
curl -X POST "http://localhost:8000/v1/tts/generate" \
     -H "Content-Type: application/json" \
     -d '{
       "text": "Welcome to DeepTool AI platform",
       "voice": "en-US-female",
       "speed": 1.0
     }' \
     --output audio.mp3
```

## 🔄 WebSocket APIs

### Real-time Task Updates

Connect to WebSocket for real-time task execution updates.

```javascript
// JavaScript WebSocket example
const ws = new WebSocket('ws://localhost:8000/ws/tasks/task_12345');

ws.onmessage = function(event) {
    const data = JSON.parse(event.data);
    console.log('Task update:', data);
};

// Message format:
{
  "type": "progress_update",
  "task_id": "task_12345",
  "progress": 75,
  "current_step": "generating_report",
  "message": "Finalizing analysis results..."
}
```

## 📊 Status & Health APIs

### System Health Check

**GET** `/v1/health`

Check system health and status.

```bash
curl "http://localhost:8000/v1/health"
```

**Response:**
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "uptime": 86400,
  "components": {
    "database": "healthy",
    "llm_service": "healthy",
    "rag_system": "healthy",
    "external_apis": "degraded"
  },
  "metrics": {
    "active_tasks": 5,
    "completed_tasks_today": 127,
    "average_response_time": 1.3
  }
}
```

### System Metrics

**GET** `/v1/metrics`

Retrieve detailed system metrics.

```bash
curl "http://localhost:8000/v1/metrics"
```

## 🔐 Error Handling

### Standard Error Response

```json
{
  "error": {
    "code": "INVALID_REQUEST",
    "message": "The request parameters are invalid",
    "details": {
      "field": "agent_type",
      "reason": "Must be one of: code_agent, architect_agent, research_agent"
    },
    "request_id": "req_12345",
    "timestamp": "2024-01-15T10:30:00Z"
  }
}
```

### Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `INVALID_REQUEST` | 400 | Request parameters are invalid |
| `UNAUTHORIZED` | 401 | Invalid or missing authentication |
| `FORBIDDEN` | 403 | Insufficient permissions |
| `NOT_FOUND` | 404 | Resource not found |
| `RATE_LIMITED` | 429 | Too many requests |
| `INTERNAL_ERROR` | 500 | Internal server error |
| `SERVICE_UNAVAILABLE` | 503 | Service temporarily unavailable |

## 📝 Rate Limiting

### Rate Limit Headers

All API responses include rate limiting information:

```
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 999
X-RateLimit-Reset: 1642248000
```

### Rate Limits by Plan

| Plan | Requests/Hour | Concurrent Tasks |
|------|---------------|------------------|
| **Free** | 100 | 1 |
| **Developer** | 1,000 | 3 |
| **Professional** | 10,000 | 10 |
| **Enterprise** | Unlimited | Unlimited |

## 🧪 SDK & Examples

### Python SDK

```bash
pip install deeptool-sdk
```

```python
from deeptool import DeepToolClient

client = DeepToolClient(api_key="your_api_key")

# Execute a code generation task
result = client.agents.execute(
    task="Create a REST API for user management",
    agent_type="rag_code_agent",
    workspace="/path/to/project"
)

print(f"Task completed: {result.success}")
print(f"Generated files: {result.generated_files}")
```

### JavaScript SDK

```bash
npm install @deeptool/sdk
```

```javascript
import { DeepToolClient } from '@deeptool/sdk';

const client = new DeepToolClient({
  apiKey: 'your_api_key',
  baseUrl: 'http://localhost:8000'
});

// Execute architecture planning
const result = await client.architect.plan({
  requirements: 'Design a scalable chat application',
  techPreferences: ['Node.js', 'React', 'MongoDB']
});

console.log('Architecture plan:', result.plan);
```

## 📖 Interactive Documentation

Visit the interactive API documentation at:
- **Local Development**: http://localhost:8000/docs
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## 🆘 Support

- **📧 Email**: api-support@deeptool.tech
- **📚 Documentation**: https://docs.deeptool.tech
- **💬 Discord**: https://discord.gg/deeptool
- **🐛 Issues**: https://github.com/cklxx/agent/issues

---

**🔌 DeepTool API** - Empowering developers with programmatic access to AI-driven code intelligence. 