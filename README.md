# Python Compiler Optimization & Code Transformation Engine

A student-friendly Advanced Python project that analyzes Python source code, detects simple optimization opportunities, transforms the AST, benchmarks the original and optimized programs, and presents the results in a web dashboard.

## Features
- Token analysis
- Syntax validation
- AST generation
- Basic complexity analysis
- Dead-code detection
- Variable dependency analysis
- Constant folding
- Safe dead-assignment elimination
- Basic loop optimization suggestions
- Original vs optimized code comparison
- Execution-time and memory benchmarking
- REST APIs
- HTML/JavaScript dashboard

## Important safety note
The benchmark endpoint executes submitted Python code. This project is intended for local classroom demonstration. Do not expose the benchmark endpoint to untrusted users on a public server without sandboxing.

## Run

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate

pip install -r requirements.txt
uvicorn backend.main:app --reload
```

Open http://127.0.0.1:8000

## API
- POST /api/analyze
- POST /api/optimize
- POST /api/benchmark
- GET /api/health
