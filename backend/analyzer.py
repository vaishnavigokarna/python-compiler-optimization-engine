import ast
import io
import tokenize
import token as token_module
from collections import Counter, defaultdict

def token_analysis(source: str):
    result = []
    try:
        stream = tokenize.generate_tokens(io.StringIO(source).readline)
        for tok in stream:
            if tok.type in (token_module.ENCODING, tokenize.ENDMARKER, tokenize.NL, tokenize.NEWLINE, tokenize.INDENT, tokenize.DEDENT):
                continue
            result.append({
                "type": token_module.tok_name.get(tok.type, str(tok.type)),
                "value": tok.string,
                "line": tok.start[0],
                "column": tok.start[1],
            })
    except (tokenize.TokenError, IndentationError) as exc:
        return {"valid": False, "error": str(exc), "tokens": []}
    return {"valid": True, "count": len(result), "tokens": result}

def syntax_and_ast(source: str):
    try:
        tree = ast.parse(source)
        return True, tree, None
    except SyntaxError as exc:
        return False, None, f"Line {exc.lineno}, column {exc.offset}: {exc.msg}"

class Analyzer(ast.NodeVisitor):
    def __init__(self):
        self.functions = 0
        self.loops = 0
        self.branches = 0
        self.max_loop_depth = 0
        self._loop_depth = 0
        self.assignments = Counter()
        self.loads = Counter()
        self.dead_assignments = []
        self.function_names = []
        self.dependencies = defaultdict(set)
        self.current_target_names = []

    def visit_FunctionDef(self, node):
        self.functions += 1
        self.function_names.append(node.name)
        self.generic_visit(node)

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_For(self, node):
        self.loops += 1
        self._loop_depth += 1
        self.max_loop_depth = max(self.max_loop_depth, self._loop_depth)
        self.generic_visit(node)
        self._loop_depth -= 1

    def visit_While(self, node):
        self.loops += 1
        self._loop_depth += 1
        self.max_loop_depth = max(self.max_loop_depth, self._loop_depth)
        self.generic_visit(node)
        self._loop_depth -= 1

    def visit_If(self, node):
        self.branches += 1
        self.generic_visit(node)

    def visit_Name(self, node):
        if isinstance(node.ctx, ast.Store):
            self.assignments[node.id] += 1
            self.current_target_names.append(node.id)
        elif isinstance(node.ctx, ast.Load):
            self.loads[node.id] += 1
            for target in self.current_target_names:
                if target != node.id:
                    self.dependencies[target].add(node.id)

    def visit_Assign(self, node):
        before = len(self.current_target_names)
        self.current_target_names = []
        self.generic_visit(node)
        targets = list(self.current_target_names)
        self.current_target_names = self.current_target_names[:0]
        self.current_target_names = []
        # Restore is not needed for this simple analysis; dependencies are collected
        # mainly from direct assignment expressions.
        if not targets:
            for target in node.targets:
                for name in extract_names(target):
                    targets.append(name)
        self.current_target_names = []
        for name in targets:
            self.assignments[name] += 0

    def finalize(self):
        for name, count in self.assignments.items():
            if self.loads[name] == 0:
                self.dead_assignments.append(name)

def extract_names(node):
    names = []
    for n in ast.walk(node):
        if isinstance(n, ast.Name):
            names.append(n.id)
    return names

def complexity_score(tree):
    cyclomatic = 1
    for node in ast.walk(tree):
        if isinstance(node, (ast.If, ast.For, ast.While, ast.AsyncFor,
                             ast.Try, ast.ExceptHandler, ast.IfExp,
                             ast.comprehension, ast.Match)):
            cyclomatic += 1
        elif isinstance(node, ast.BoolOp):
            cyclomatic += max(0, len(node.values) - 1)
    return cyclomatic

def find_dead_assignments(tree):
    """Conservative dead-assignment detection for simple local/module names.

    A name assigned exactly once and never loaded is reported. It is not removed
    here; the optimizer applies an even more conservative rule.
    """
    assigned = Counter()
    loaded = Counter()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            if isinstance(node.ctx, ast.Store):
                assigned[node.id] += 1
            elif isinstance(node.ctx, ast.Load):
                loaded[node.id] += 1
    return [
        {"variable": name, "assignments": assigned[name], "uses": loaded[name]}
        for name in sorted(assigned)
        if loaded[name] == 0 and name not in {"_"}
    ]

def dependency_graph(tree):
    graph = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            targets = extract_names(node.targets[0]) if node.targets else []
            sources = sorted({
                n.id for n in ast.walk(node.value)
                if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load)
            })
            for target in targets:
                for source in sources:
                    graph.append({"from": source, "to": target})
    return graph

def analyze_source(source: str):
    tokens = token_analysis(source)
    valid, tree, error = syntax_and_ast(source)
    if not valid:
        return {
            "valid": False,
            "syntax_error": error,
            "tokens": tokens,
            "ast": None,
        }

    analyzer = Analyzer()
    analyzer.visit(tree)
    analyzer.finalize()
    dead = find_dead_assignments(tree)
    complexity = complexity_score(tree)

    return {
        "valid": True,
        "syntax_error": None,
        "tokens": tokens,
        "summary": {
            "functions": analyzer.functions,
            "loops": analyzer.loops,
            "branches": analyzer.branches,
            "max_loop_depth": analyzer.max_loop_depth,
            "cyclomatic_complexity": complexity,
            "dead_assignments": len(dead),
        },
        "dead_code": dead,
        "dependencies": dependency_graph(tree),
        "function_names": analyzer.function_names,
        "ast_dump": ast.dump(tree, indent=2),
    }
