import ast

class ConstantFolder(ast.NodeTransformer):
    """Fold safe literal-only expressions without calling user-defined code."""
    ALLOWED_BINOPS = (
        ast.Add, ast.Sub, ast.Mult, ast.Div, ast.FloorDiv,
        ast.Mod, ast.Pow, ast.BitAnd, ast.BitOr, ast.BitXor,
        ast.LShift, ast.RShift,
    )
    ALLOWED_UNARYOPS = (ast.UAdd, ast.USub, ast.Not, ast.Invert)

    def __init__(self):
        self.count = 0

    def visit_BinOp(self, node):
        node = self.generic_visit(node)
        if isinstance(node.left, ast.Constant) and isinstance(node.right, ast.Constant):
            if isinstance(node.op, self.ALLOWED_BINOPS):
                try:
                    value = evaluate_literal_binop(node.left.value, node.op, node.right.value)
                    if isinstance(value, (str, int, float, complex, bytes, bool, type(None))):
                        self.count += 1
                        return ast.copy_location(ast.Constant(value=value), node)
                except Exception:
                    pass
        return node

    def visit_UnaryOp(self, node):
        node = self.generic_visit(node)
        if isinstance(node.operand, ast.Constant) and isinstance(node.op, self.ALLOWED_UNARYOPS):
            try:
                value = evaluate_literal_unary(node.op, node.operand.value)
                if isinstance(value, (str, int, float, complex, bytes, bool, type(None))):
                    self.count += 1
                    return ast.copy_location(ast.Constant(value=value), node)
            except Exception:
                pass
        return node

def evaluate_literal_binop(a, op, b):
    if isinstance(op, ast.Add): return a + b
    if isinstance(op, ast.Sub): return a - b
    if isinstance(op, ast.Mult): return a * b
    if isinstance(op, ast.Div): return a / b
    if isinstance(op, ast.FloorDiv): return a // b
    if isinstance(op, ast.Mod): return a % b
    if isinstance(op, ast.Pow): return a ** b
    if isinstance(op, ast.BitAnd): return a & b
    if isinstance(op, ast.BitOr): return a | b
    if isinstance(op, ast.BitXor): return a ^ b
    if isinstance(op, ast.LShift): return a << b
    if isinstance(op, ast.RShift): return a >> b
    raise ValueError("unsupported operator")

def evaluate_literal_unary(op, value):
    if isinstance(op, ast.UAdd): return +value
    if isinstance(op, ast.USub): return -value
    if isinstance(op, ast.Not): return not value
    if isinstance(op, ast.Invert): return ~value
    raise ValueError("unsupported operator")

class DeadAssignmentRemover(ast.NodeTransformer):
    """Conservatively remove simple assignments whose values have no side effects
    and whose target is never loaded anywhere in the module/function scope."""
    def __init__(self):
        self.removed = []

    def optimize_block(self, statements):
        # Compute loads in the whole tree before transformation.
        all_loaded = {
            n.id for n in ast.walk(self.root)
            if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load)
        }
        new = []
        for stmt in statements:
            if (isinstance(stmt, ast.Assign)
                and len(stmt.targets) == 1
                and isinstance(stmt.targets[0], ast.Name)):
                name = stmt.targets[0].id
                if name not in all_loaded and is_side_effect_free(stmt.value):
                    self.removed.append(name)
                    continue
            new.append(self.visit(stmt))
        return new

    def visit_Module(self, node):
        self.root = node
        node.body = self.optimize_block(node.body)
        return node

    def visit_FunctionDef(self, node):
        node.body = self.optimize_block(node.body)
        return node

    visit_AsyncFunctionDef = visit_FunctionDef

def is_side_effect_free(node):
    safe = (ast.Constant, ast.Name, ast.Tuple, ast.List, ast.Set, ast.Dict,
            ast.UnaryOp, ast.BinOp, ast.BoolOp, ast.Compare)
    if isinstance(node, ast.Constant):
        return True
    if isinstance(node, ast.Name):
        return True
    if isinstance(node, (ast.Tuple, ast.List, ast.Set)):
        return all(is_side_effect_free(x) for x in node.elts)
    if isinstance(node, ast.Dict):
        return all(
            (k is None or is_side_effect_free(k)) and is_side_effect_free(v)
            for k, v in zip(node.keys, node.values)
        )
    if isinstance(node, ast.UnaryOp):
        return is_side_effect_free(node.operand)
    if isinstance(node, ast.BinOp):
        return is_side_effect_free(node.left) and is_side_effect_free(node.right)
    if isinstance(node, ast.BoolOp):
        return all(is_side_effect_free(x) for x in node.values)
    if isinstance(node, ast.Compare):
        return is_side_effect_free(node.left) and all(is_side_effect_free(x) for x in node.comparators)
    return False

class LoopSuggestionVisitor(ast.NodeVisitor):
    def __init__(self):
        self.suggestions = []

    def visit_For(self, node):
        if isinstance(node.iter, ast.Call) and isinstance(node.iter.func, ast.Name):
            if node.iter.func.id == "range" and len(node.body) == 1:
                inner = node.body[0]
                if isinstance(inner, ast.Expr) and isinstance(inner.value, ast.Call):
                    self.suggestions.append({
                        "line": node.lineno,
                        "type": "loop_optimization_candidate",
                        "message": "Simple range loop detected; inspect whether direct iteration or vectorization is possible."
                    })
        self.generic_visit(node)

def optimize_source(source: str):
    tree = ast.parse(source)

    folder = ConstantFolder()
    tree = folder.visit(tree)
    ast.fix_missing_locations(tree)

    remover = DeadAssignmentRemover()
    tree = remover.visit(tree)
    ast.fix_missing_locations(tree)

    suggester = LoopSuggestionVisitor()
    suggester.visit(tree)

    optimized = ast.unparse(tree)
    return {
        "optimized_code": optimized,
        "optimizations": {
            "constant_folding": folder.count,
            "dead_assignments_removed": len(remover.removed),
            "dead_assignment_names": remover.removed,
        },
        "suggestions": suggester.suggestions,
    }
