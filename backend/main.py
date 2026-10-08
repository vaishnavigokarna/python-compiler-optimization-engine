from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .analyzer import analyze_source
from .optimizer import optimize_source
from .benchmark import compare

app = FastAPI(
    title="Python Compiler Optimization Engine",
    version="1.0.0",
    description="Analyze, optimize and benchmark Python code."
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

class CodeRequest(BaseModel):
    code: str = Field(min_length=1, max_length=100_000)

class BenchmarkRequest(BaseModel):
    original_code: str = Field(min_length=1, max_length=100_000)
    optimized_code: str = Field(min_length=1, max_length=100_000)
    runs: int = Field(default=3, ge=1, le=5)

@app.get("/api/health")
def health():
    return {"status": "ok"}

@app.post("/api/analyze")
def analyze(req: CodeRequest):
    return analyze_source(req.code)

@app.post("/api/optimize")
def optimize(req: CodeRequest):
    try:
        analysis = analyze_source(req.code)
        if not analysis["valid"]:
            raise HTTPException(status_code=400, detail=analysis["syntax_error"])
        result = optimize_source(req.code)
        return {**result, "analysis": analysis}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))

@app.post("/api/benchmark")
def benchmark(req: BenchmarkRequest):
    return compare(req.original_code, req.optimized_code, runs=req.runs)

app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")
