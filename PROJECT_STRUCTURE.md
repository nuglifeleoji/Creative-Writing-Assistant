# Project Structure Documentation

## Overview

This document describes the organization of the AI Creative Writing Assistant project, including code structure, book data organization, and file naming conventions.

## Code Structure

```
ai-creative-writing-assistant/
├── README.md                    # Project documentation
├── PROJECT_STRUCTURE.md         # This file - project structure guide
├── requirements.txt             # Python dependencies
├── .env                         # Environment variables (not in repo)
├── .gitignore                   # Git ignore rules
│
├── app.py                       # Main Flask application
├── langchain_agent.py           # Core LangChain agent implementation
├── cross_book_agent.py          # Cross-book orchestration agent
├── polish_agent.py              # Text polishing agent
├── prompt_utils.py              # Agent prompts and utilities
├── prompt.py                    # Additional prompt templates
│
├── frontend/                    # Frontend assets
│   ├── index.html              # Main application page
│   ├── styles.css              # Application styling
│   ├── script_enhanced.js      # Frontend JavaScript logic
│   └── test.html               # Test page
│
├── search/                      # GraphRAG search engines
│   ├── rag_engine.py           # Main GraphRAG engine
│   └── quick_engine.py         # Conservative parameter engine
│
└── book_data/                   # Book data directories
    ├── ordinary_world/          # "平凡的世界" (Ordinary World)
    ├── three_body_problem/      # "三体" (Three-Body Problem)
    ├── three_body_problem_2/    # "三体2" (Three-Body Problem 2)
    ├── supernova_era/           # "超新星纪元" (Supernova Era)
    ├── white_night/             # "白夜行" (White Night)
    ├── frankenstein/            # "弗兰肯斯坦" (Frankenstein)
    ├── dune/                    # "沙丘" (Dune)
    ├── suspect_x/               # "嫌疑人x的献身" (Suspect X)
    ├── soul_land_4/             # "斗罗大陆4" (Soul Land 4)
    └── romance_of_three_kingdoms/ # "三国演义" (Romance of Three Kingdoms)
```

## Book Data Organization

### Current Book Data Structure

Each book data directory contains the following structure:

```
book_name/
└── output/
    ├── communities.parquet      # Community detection results
    ├── entities.parquet         # Entity extraction results
    ├── community_reports.parquet # Community analysis reports
    ├── relationships.parquet    # Entity relationship data
    ├── text_units.parquet       # Text segmentation units
    └── lancedb/                 # Vector database for embeddings
        ├── entity_descriptions/ # Entity description embeddings
        └── metadata/            # Database metadata
```

### Book Data Mapping

| Current Path | English Name | Chinese Name | Genre |
|--------------|--------------|--------------|-------|
| `book4/output/` | Ordinary World | 平凡的世界 | Modern Literature |
| `book5/output/` | Three-Body Problem | 三体 | Science Fiction |
| `book6/output/` | Three-Body Problem 2 | 三体2 | Science Fiction |
| `cxx/output/` | Supernova Era | 超新星纪元 | Science Fiction |
| `rag_book2/ragtest/output/` | White Night | 白夜行 | Mystery/Thriller |
| `tencent/output/` | Frankenstein | 弗兰肯斯坦 | Gothic Fiction |
| `rag/output/` | Dune | 沙丘 | Science Fiction |
| `book7/output/` | Suspect X | 嫌疑人x的献身 | Mystery/Thriller |
| `book8/output/` | Soul Land 4 | 斗罗大陆4 | Fantasy |
| `sanguo/output/` | Romance of Three Kingdoms | 三国演义 | Historical Fiction |

## File Naming Conventions

### Code Files

- **Python files**: Use snake_case (e.g., `langchain_agent.py`)
- **JavaScript files**: Use snake_case (e.g., `script_enhanced.js`)
- **CSS files**: Use snake_case (e.g., `styles.css`)
- **HTML files**: Use snake_case (e.g., `index.html`)

### Book Data Directories

**Current (Legacy) Naming:**
- Uses generic names like `book4/`, `book5/`, etc.
- Some use abbreviated names like `cxx/`, `sanguo/`

**Recommended Naming Convention:**
- Use descriptive English names in snake_case
- Include both English and Chinese names in documentation
- Example: `ordinary_world/` for "平凡的世界"

### Configuration Files

- **Environment**: `.env` (not in repository)
- **Dependencies**: `requirements.txt`
- **Git**: `.gitignore`

## Migration Plan for Book Data

To improve organization, consider migrating to the following structure:

```
book_data/
├── ordinary_world/              # 平凡的世界
├── three_body_problem/          # 三体
├── three_body_problem_2/        # 三体2
├── supernova_era/               # 超新星纪元
├── white_night/                 # 白夜行
├── frankenstein/                # 弗兰肯斯坦
├── dune/                        # 沙丘
├── suspect_x/                   # 嫌疑人x的献身
├── soul_land_4/                 # 斗罗大陆4
└── romance_of_three_kingdoms/   # 三国演义
```

### Migration Steps

1. **Create new directory structure**
2. **Copy book data to new locations**
3. **Update configuration in `app.py`**
4. **Update documentation**
5. **Test all book loading functionality**

## Code Organization Principles

### Backend Structure

1. **Main Application (`app.py`)**
   - Flask routes and API endpoints
   - SSE streaming implementation
   - Agent initialization and management

2. **Agent Modules**
   - `langchain_agent.py`: Core agent implementation
   - `cross_book_agent.py`: Multi-book orchestration
   - `polish_agent.py`: Text enhancement

3. **Search Engines (`search/`)**
   - GraphRAG implementation
   - Multi-book management
   - Vector database integration

### Frontend Structure

1. **HTML (`index.html`)**
   - Main application interface
   - Semantic markup structure

2. **CSS (`styles.css`)**
   - Responsive design
   - Animation and interaction styles
   - Theme consistency

3. **JavaScript (`script_enhanced.js`)**
   - SSE event handling
   - UI interaction logic
   - Real-time updates

## Development Guidelines

### Adding New Books

1. **Prepare book data** using GraphRAG pipeline
2. **Create directory** with descriptive name
3. **Update configuration** in `app.py`
4. **Test loading** and functionality
5. **Update documentation**

### Code Style

- **Python**: Follow PEP 8 guidelines
- **JavaScript**: Use ES6+ features, consistent formatting
- **CSS**: Use BEM methodology for class naming
- **Comments**: Write clear, English documentation

### Testing

- **Unit tests**: For individual functions and classes
- **Integration tests**: For API endpoints
- **End-to-end tests**: For complete user workflows
- **Performance tests**: For streaming and large book handling

## Deployment Considerations

### File Organization

- **Static assets**: Serve from `frontend/` directory
- **Book data**: Large files, consider CDN or separate storage
- **Configuration**: Environment-specific settings

### Performance

- **Book loading**: Lazy loading for large datasets
- **Memory management**: Efficient handling of multiple books
- **Streaming**: Optimize SSE for real-time responses

### Security

- **API keys**: Never commit to repository
- **Input validation**: Sanitize all user inputs
- **Rate limiting**: Prevent abuse of API endpoints

---

**Note**: This document should be updated as the project evolves and new features are added.
