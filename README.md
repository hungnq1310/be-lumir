# Lumir Agentic

[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104%2B-green.svg)](https://fastapi.tiangolo.com)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Docker](https://img.shields.io/badge/docker-supported-blue.svg)](https://docker.com)

**Lumir Agentic** is an advanced AI agent system designed for trading intelligence and financial analysis. It combines sophisticated behavioral analysis, trading insights, and conversational AI to provide personalized financial guidance and market intelligence.

## 🚀 Features

### Core Capabilities
- **🤖 Intelligent AI Agent**: Advanced conversational AI powered by LangChain and OpenAI
- **📊 TBI Analysis**: Trading Behavior Intelligence calculation based on personal data
- **🔍 RAG Search**: Retrieval-Augmented Generation for contextual information
- **💬 Session Management**: Persistent conversation history with PostgreSQL
- **🌐 RESTful API**: FastAPI-based web service with comprehensive endpoints
- **🐳 Docker Support**: Containerized deployment with PostgreSQL and pgAdmin

### Trading Intelligence Tools
- **TBI Calculator**: Comprehensive behavioral analysis including:
  - Path Potential Alignment (PPA)
  - Skill Potential Index (SPI)
  - Crisis Management Index (CMI)
  - Natural Edge Index (NEI)
  - Resilience Index (RI)
  - And 15+ other behavioral indicators

- **Market Analysis**: Real-time trading data analysis and insights
- **Document Retrieval**: Context-aware document search for trading strategies

## 📋 Table of Contents

- [Installation](#installation)
- [Quick Start](#quick-start)
- [Configuration](#configuration)
- [API Documentation](#api-documentation)
- [Usage Examples](#usage-examples)
- [Development](#development)
- [Docker Deployment](#docker-deployment)
- [Testing](#testing)
- [Contributing](#contributing)
- [License](#license)

## 🛠 Installation

### Prerequisites

- Python 3.8 or higher
- Docker and Docker Compose (for containerized deployment)
- PostgreSQL 15+ (if running without Docker)

### Local Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/lumir/lumir-agentic.git
   cd lumir-agentic
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

5. **Initialize database**
   ```bash
   # Start PostgreSQL container
   docker-compose up -d postgres
   
   # Or set up your own PostgreSQL instance
   # Database schema will be automatically created
   ```

## ⚡ Quick Start

### Using Docker (Recommended)

1. **Start all services**
   ```bash
   docker-compose up -d
   ```

2. **Access the API**
   - API Server: http://localhost:8081
   - pgAdmin: http://localhost:8080 (admin@lumir.ai / admin123)
   - API Documentation: http://localhost:8081/docs

### Manual Setup

1. **Start the API server**
   ```bash
   python -m uvicorn src.lumir_agentic.api.v1:app --host 0.0.0.0 --port 8081 --reload
   ```

2. **Run CLI interface**
   ```bash
   python main.py --interactive
   ```

## ⚙️ Configuration

### Environment Variables

Create a `.env` file with the following configuration:

```env
# Model Configuration
MODEL_NAME="gpt-4.1-nano-2025-04-14"
API_KEY="your-openai-api-key"
BASE_URL="https://api.openai.com/v1"
TEMPERATURE=0.5
MAX_TOKENS=4096

# Database Configuration
DATABASE_URL=postgresql://lumir_user:lumir_password@localhost:5434/lumir_agentic
DB_HOST=localhost
DB_PORT=5434
DB_NAME=lumir_agentic
DB_USER=lumir_user
DB_PASSWORD=lumir_password
DB_SSL_MODE=prefer

# External Services
TBI_DOCS_URL="https://your-tbi-docs-api.com/api/v1/documents/content-by-indicators"
RAG_QUERY_URL="https://your-rag-service.com/api/rag/query"
TRADING_ANALYZE_URL="http://localhost:8080/analyze_trading"

# Session Configuration
SESSION_DATA_TBI='your-session-id'
ACCOUNT_NUMBER="your-account-number"
```

### Database Schema

The system automatically creates the following tables:
- `sessions`: User session management
- `conversations`: Conversation history with metadata
- Indexes for optimal query performance

## 📚 API Documentation

### Core Endpoints

#### Create Session
```http
POST /api/v1/sessions/create
Content-Type: application/json

{
  "user_id": "user123"
}
```

#### Call Agent
```http
POST /api/v1/agent/call
Content-Type: application/json

{
  "user_question": "What's my trading behavior analysis?",
  "account_number": "9259695",
  "language": "vi",
  "name": "John Doe",
  "birthday": "1990-01-01",
  "user_id": "user123",
  "memory_session_id": "session-uuid"
}
```

#### Delete Session
```http
DELETE /api/v1/sessions/delete
Content-Type: application/json

{
  "user_id": "user123",
  "session_id": "session-uuid"
}
```

#### Health Check
```http
GET /api/v1/health
```

### Interactive Documentation

Visit `http://localhost:8081/docs` for complete Swagger/OpenAPI documentation.

## 💡 Usage Examples

### Python SDK Usage

```python
from src.lumir_agentic.agent.graph import LumirAgent
from src.lumir_agentic.utils.session_manager import SessionManager

# Initialize agent
agent = LumirAgent(
    model_name="gpt-4",
    api_key="your-api-key",
    base_url="https://api.openai.com/v1"
)

# Create user profile
user_profile = {
    "full_name": "John Doe",
    "account_number": "9259692",
    "birthday": "1990-01-01",
    "language": "en"
}

# Get response
response = agent.run(
    user_question="Analyze my trading behavior",
    conversation_history="",
    user_profile=user_profile
)

print(response)
```

### TBI Calculator Usage

```python
from src.lumir_agentic.tools.TBI_caculate import calculate_tbi

# Calculate TBI indicators
indicators = calculate_tbi(
    dob="01/01/1990",
    name="John Doe",
    current_date="15/12/2024"
)

print(indicators)
```

### RAG Search Usage

```python
from src.lumir_agentic.tools.search_rag import rag_query

# Search for relevant documents
results = rag_query(
    question="What are the best trading strategies?",
    top_n=5,
    score_threshold=0.7
)

print(results)
```

## 🔧 Development

### Project Structure

```
lumir_agentic/
├── src/lumir_agentic/
│   ├── agent/              # AI agent implementation
│   │   ├── graph.py        # Main agent logic
│   │   └── states.py       # Agent state management
│   ├── api/                # FastAPI endpoints
│   │   └── v1.py          # API v1 implementation
│   ├── database/           # Database management
│   │   ├── connection.py   # Database connection
│   │   ├── manager.py      # Database operations
│   │   ├── config.py       # Database configuration
│   │   └── schema.sql      # Database schema
│   ├── tools/              # Agent tools
│   │   ├── TBI_caculate.py # TBI calculation
│   │   ├── search_rag.py   # RAG search
│   │   └── trading_caculate.py # Trading analysis
│   └── utils/              # Utilities
│       ├── logger.py       # Logging system
│       └── session_manager.py # Session management
├── docker-compose.yml      # Docker services
├── requirements.txt        # Python dependencies
├── main.py                # CLI entry point
└── test_api.py            # API tests
```

### Setting Up Development Environment

1. **Install development dependencies**
   ```bash
   pip install -r requirements.txt
   pip install pytest pytest-cov black flake8 mypy
   ```

2. **Run code formatting**
   ```bash
   black src/ tests/
   ```

3. **Run linting**
   ```bash
   flake8 src/ tests/
   mypy src/
   ```

4. **Run tests**
   ```bash
   pytest tests/ -v --cov=src/
   ```

### Code Style

- Follow PEP 8 guidelines
- Use type hints for all functions
- Document all public methods and classes
- Maintain test coverage above 80%

## 🐳 Docker Deployment

### Production Deployment

1. **Build and start services**
   ```bash
   docker-compose up -d
   ```

2. **Scale the application**
   ```bash
   docker-compose up -d --scale app=3
   ```

3. **Monitor logs**
   ```bash
   docker-compose logs -f app
   ```

### Docker Services

- **postgres**: PostgreSQL 15 database
- **pgadmin**: Database administration interface
- **app**: Lumir Agentic API server (when configured)

### Environment-Specific Configurations

Create environment-specific compose files:
- `docker-compose.prod.yml` for production
- `docker-compose.dev.yml` for development
- `docker-compose.test.yml` for testing

## 🧪 Testing

### Running Tests

```bash
# Run all tests
python test_api.py

# Run specific test categories
pytest tests/unit/ -v
pytest tests/integration/ -v
pytest tests/e2e/ -v
```

### Test Coverage

```bash
# Generate coverage report
pytest --cov=src/ --cov-report=html
open htmlcov/index.html
```

### API Testing

The project includes comprehensive API tests:
- Health check validation
- Session management testing
- Agent interaction testing
- Error handling verification

## 🤝 Contributing

We welcome contributions! Please follow these steps:

1. **Fork the repository**
2. **Create a feature branch**
   ```bash
   git checkout -b feature/amazing-feature
   ```
3. **Make your changes**
4. **Add tests for new functionality**
5. **Run the test suite**
   ```bash
   pytest tests/ -v
   ```
6. **Commit your changes**
   ```bash
   git commit -m "Add amazing feature"
   ```
7. **Push to your branch**
   ```bash
   git push origin feature/amazing-feature
   ```
8. **Open a Pull Request**

### Development Guidelines

- Write clear, concise commit messages
- Include tests for new features
- Update documentation as needed
- Follow the existing code style
- Ensure all tests pass before submitting

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

### Documentation

- [API Documentation](http://localhost:8081/docs) - Interactive API docs
- [Architecture Guide](ARCHITECTURE.md) - System architecture overview
- [Setup Guide](SETUP.md) - Detailed setup instructions

### Getting Help

- **Issues**: [GitHub Issues](https://github.com/lumir/lumir-agentic/issues)
- **Discussions**: [GitHub Discussions](https://github.com/lumir/lumir-agentic/discussions)
- **Email**: team@lumir.ai

### Troubleshooting

#### Common Issues

1. **Database Connection Error**
   ```bash
   # Check if PostgreSQL is running
   docker-compose ps postgres
   
   # Restart database service
   docker-compose restart postgres
   ```

2. **API Key Issues**
   ```bash
   # Verify environment variables
   echo $API_KEY
   
   # Check .env file configuration
   cat .env | grep API_KEY
   ```

3. **Port Conflicts**
   ```bash
   # Check if ports are in use
   lsof -i :8081
   lsof -i :5434
   
   # Modify ports in docker-compose.yml if needed
   ```

## 🔄 Changelog

### Version 1.0.0 (Current)
- Initial release
- Core AI agent functionality
- TBI calculation system
- RESTful API with FastAPI
- PostgreSQL integration
- Docker containerization
- Comprehensive testing suite

---

**Built with ❤️ by the Lumir Team**

For more information, visit our [website](https://lumir.ai) or check out our [documentation](https://docs.lumir.ai).