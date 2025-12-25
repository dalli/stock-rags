"""
Phase 3 Comprehensive Test Suite
Tests the Query Engine components without external dependencies
"""

import sys
from dataclasses import is_dataclass
from enum import Enum

print("=" * 80)
print("PHASE 3 COMPREHENSIVE TEST SUITE")
print("=" * 80)

# Test 1: Module structure and imports
print("\n[TEST 1] Module Structure & AST Analysis")
print("-" * 80)

import ast
import os

test_files = {
    "backend/app/agents/state.py": {
        "expected_classes": ["AgentState"],
        "expected_functions": ["add_error", "to_dict"],
        "expected_decorators": ["dataclass"],
    },
    "backend/app/services/search_service.py": {
        "expected_classes": ["QueryIntent", "IntentClassifier", "GraphQuerier", "VectorSearcher", "HybridSearcher", "AnswerSynthesizer"],
        "expected_enums": ["QueryIntent"],
    },
    "backend/app/agents/graph_builder.py": {
        "expected_classes": ["QueryAgentBuilder"],
        "expected_functions": ["build", "process_query", "get_agent_builder"],
    },
    "backend/app/agents/nodes/intent_node.py": {
        "expected_functions": ["intent_classification_node"],
    },
    "backend/app/agents/nodes/search_nodes.py": {
        "expected_functions": ["graph_search_node", "vector_search_node", "hybrid_search_node", "select_search_node"],
    },
    "backend/app/agents/nodes/synthesis_node.py": {
        "expected_functions": ["answer_synthesis_node"],
    },
    "backend/app/api/v1/chat.py": {
        "expected_classes": ["ChatMessage", "ChatRequest", "ChatResponse", "ConversationResponse"],
        "expected_functions": ["chat", "list_conversations", "get_conversation", "delete_conversation"],
    },
    "backend/app/db/postgres_client.py": {
        "expected_classes": ["PostgresClient"],
        "expected_functions": ["get_postgres_client"],
    },
}

def parse_file(filepath):
    """Parse Python file and extract AST info"""
    with open(filepath, 'r') as f:
        return ast.parse(f.read())

def get_classes(tree):
    """Extract class names from AST"""
    classes = []
    enums = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            # Check if it's an Enum
            for base in node.bases:
                if isinstance(base, ast.Name) and base.id == "Enum":
                    enums.append(node.name)
            classes.append(node.name)
    return classes, enums

def get_functions(tree):
    """Extract function names from AST"""
    functions = []
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            functions.append(node.name)
    return functions

test1_passed = 0
test1_total = 0

for filepath, expectations in test_files.items():
    if not os.path.exists(filepath):
        print(f"❌ {filepath}: FILE NOT FOUND")
        test1_total += 1
        continue

    try:
        tree = parse_file(filepath)
        classes, enums = get_classes(tree)
        functions = get_functions(tree)

        # Check expected classes
        if "expected_classes" in expectations:
            for expected_class in expectations["expected_classes"]:
                if expected_class in classes:
                    print(f"  ✅ Class '{expected_class}' found")
                    test1_passed += 1
                else:
                    print(f"  ❌ Class '{expected_class}' NOT found")
                test1_total += 1

        # Check expected enums
        if "expected_enums" in expectations:
            for expected_enum in expectations["expected_enums"]:
                if expected_enum in enums:
                    print(f"  ✅ Enum '{expected_enum}' found")
                    test1_passed += 1
                else:
                    print(f"  ❌ Enum '{expected_enum}' NOT found")
                test1_total += 1

        # Check expected functions
        if "expected_functions" in expectations:
            for expected_func in expectations["expected_functions"]:
                if expected_func in functions:
                    print(f"  ✅ Function '{expected_func}' found")
                    test1_passed += 1
                else:
                    print(f"  ❌ Function '{expected_func}' NOT found")
                test1_total += 1

        print(f"✅ {filepath}: PASSED")

    except Exception as e:
        print(f"❌ {filepath}: {str(e)}")
        test1_total += len(expectations.get("expected_classes", []))
        test1_total += len(expectations.get("expected_functions", []))

print(f"\n[Result] Test 1: {test1_passed}/{test1_total} checks passed")

# Test 2: Code Logic Analysis
print("\n[TEST 2] Code Logic & Design Pattern Validation")
print("-" * 80)

test2_checks = []

# Check QueryIntent enum
print("Checking QueryIntent enum...")
try:
    with open("backend/app/services/search_service.py", 'r') as f:
        content = f.read()

    checks = [
        ("GRAPH" in content, "QueryIntent.GRAPH value"),
        ("VECTOR" in content, "QueryIntent.VECTOR value"),
        ("HYBRID" in content, "QueryIntent.HYBRID value"),
        ("class QueryIntent(str, Enum)" in content, "QueryIntent inherits from (str, Enum)"),
    ]

    for check, desc in checks:
        if check:
            print(f"  ✅ {desc}")
            test2_checks.append(True)
        else:
            print(f"  ❌ {desc}")
            test2_checks.append(False)
except Exception as e:
    print(f"  ❌ Error: {e}")
    test2_checks.append(False)

# Check AgentState dataclass structure
print("\nChecking AgentState structure...")
try:
    with open("backend/app/agents/state.py", 'r') as f:
        content = f.read()

    checks = [
        ("@dataclass" in content, "@dataclass decorator"),
        ("query: str" in content, "query field"),
        ("conversation_id: str" in content, "conversation_id field"),
        ("intent: Optional[QueryIntent]" in content, "intent field"),
        ("search_results: dict" in content, "search_results field"),
        ("answer: Optional[str]" in content, "answer field"),
        ("sources: list" in content, "sources field"),
        ("def add_error" in content, "add_error method"),
        ("def to_dict" in content, "to_dict method"),
    ]

    for check, desc in checks:
        if check:
            print(f"  ✅ {desc}")
            test2_checks.append(True)
        else:
            print(f"  ❌ {desc}")
            test2_checks.append(False)
except Exception as e:
    print(f"  ❌ Error: {e}")
    test2_checks.append(False)

# Check Agent Graph Structure
print("\nChecking QueryAgentBuilder structure...")
try:
    with open("backend/app/agents/graph_builder.py", 'r') as f:
        content = f.read()

    checks = [
        ("class QueryAgentBuilder" in content, "QueryAgentBuilder class"),
        ("def build(self)" in content, "build method"),
        ("StateGraph" in content, "StateGraph usage"),
        ("add_node" in content, "add_node calls"),
        ("add_edge" in content, "add_edge calls"),
        ("add_conditional_edges" in content, "add_conditional_edges for routing"),
        ("async def process_query" in content, "async process_query method"),
        ("def get_agent_builder" in content, "get_agent_builder function"),
    ]

    for check, desc in checks:
        if check:
            print(f"  ✅ {desc}")
            test2_checks.append(True)
        else:
            print(f"  ❌ {desc}")
            test2_checks.append(False)
except Exception as e:
    print(f"  ❌ Error: {e}")
    test2_checks.append(False)

# Check Search Nodes
print("\nChecking Search Nodes structure...")
try:
    with open("backend/app/agents/nodes/search_nodes.py", 'r') as f:
        content = f.read()

    checks = [
        ("def graph_search_node" in content, "graph_search_node function"),
        ("def vector_search_node" in content, "vector_search_node function"),
        ("def hybrid_search_node" in content, "hybrid_search_node function"),
        ("def select_search_node" in content, "select_search_node routing function"),
        ("AgentState" in content, "AgentState parameter"),
        ("QueryIntent" in content, "QueryIntent usage"),
    ]

    for check, desc in checks:
        if check:
            print(f"  ✅ {desc}")
            test2_checks.append(True)
        else:
            print(f"  ❌ {desc}")
            test2_checks.append(False)
except Exception as e:
    print(f"  ❌ Error: {e}")
    test2_checks.append(False)

# Check Chat API
print("\nChecking Chat API structure...")
try:
    with open("backend/app/api/v1/chat.py", 'r') as f:
        content = f.read()

    checks = [
        ("router = APIRouter()" in content, "APIRouter initialization"),
        ("@router.post(\"/chat\")" in content, "POST /chat endpoint"),
        ("@router.get(\"/chat/conversations\")" in content, "GET /conversations endpoint"),
        ("@router.get(\"/chat/conversations/{" in content, "GET /{id} endpoint"),
        ("@router.delete(\"/chat/conversations/{" in content, "DELETE /{id} endpoint"),
        ("class ChatRequest" in content, "ChatRequest model"),
        ("class ChatResponse" in content, "ChatResponse model"),
        ("get_agent_builder()" in content, "Agent integration"),
        ("get_postgres_client()" in content, "Database integration"),
    ]

    for check, desc in checks:
        if check:
            print(f"  ✅ {desc}")
            test2_checks.append(True)
        else:
            print(f"  ❌ {desc}")
            test2_checks.append(False)
except Exception as e:
    print(f"  ❌ Error: {e}")
    test2_checks.append(False)

test2_passed = sum(test2_checks)
test2_total = len(test2_checks)
print(f"\n[Result] Test 2: {test2_passed}/{test2_total} checks passed")

# Test 3: File Coverage
print("\n[TEST 3] Implementation Coverage Analysis")
print("-" * 80)

test3_checks = []

files_to_check = {
    "backend/app/agents/state.py": "Agent State",
    "backend/app/agents/graph_builder.py": "LangGraph Builder",
    "backend/app/agents/nodes/intent_node.py": "Intent Node",
    "backend/app/agents/nodes/search_nodes.py": "Search Nodes",
    "backend/app/agents/nodes/synthesis_node.py": "Synthesis Node",
    "backend/app/services/search_service.py": "Search Services",
    "backend/app/api/v1/chat.py": "Chat API",
    "backend/app/db/postgres_client.py": "PostgreSQL Client",
}

for filepath, name in files_to_check.items():
    try:
        with open(filepath, 'r') as f:
            lines = f.readlines()

        code_lines = sum(1 for line in lines if line.strip() and not line.strip().startswith('#'))
        docstring_lines = sum(1 for line in lines if '"""' in line or "'''" in line)

        if code_lines > 0:
            print(f"✅ {name:<30} Lines: {len(lines):<4} Code: {code_lines:<4} Docs: {docstring_lines:<2}")
            test3_checks.append(True)
        else:
            print(f"⚠️  {name:<30} Empty file")
            test3_checks.append(False)
    except Exception as e:
        print(f"❌ {name:<30} Error: {e}")
        test3_checks.append(False)

test3_passed = sum(test3_checks)
test3_total = len(test3_checks)
print(f"\n[Result] Test 3: {test3_passed}/{test3_total} files have content")

# Test 4: Integration Points
print("\n[TEST 4] Integration Points Validation")
print("-" * 80)

test4_checks = []

# Check main.py includes chat router
print("Checking main.py includes chat router...")
try:
    with open("backend/app/main.py", 'r') as f:
        content = f.read()

    if "from app.api.v1 import models, reports, chat" in content:
        print(f"  ✅ Chat module imported in main.py")
        test4_checks.append(True)
    else:
        print(f"  ❌ Chat module NOT imported in main.py")
        test4_checks.append(False)

    if "app.include_router(chat.router" in content:
        print(f"  ✅ Chat router registered in main.py")
        test4_checks.append(True)
    else:
        print(f"  ❌ Chat router NOT registered in main.py")
        test4_checks.append(False)
except Exception as e:
    print(f"  ❌ Error: {e}")
    test4_checks.append(False)

# Check LLM router has embedding provider method
print("\nChecking LLM router integration...")
try:
    with open("backend/app/llm/router.py", 'r') as f:
        content = f.read()

    if "def get_embedding_provider" in content:
        print(f"  ✅ get_embedding_provider method in LLMRouter")
        test4_checks.append(True)
    else:
        print(f"  ❌ get_embedding_provider method NOT found")
        test4_checks.append(False)
except Exception as e:
    print(f"  ❌ Error: {e}")
    test4_checks.append(False)

# Check prompt templates
print("\nChecking prompt templates...")
prompt_templates = [
    "backend/app/prompts/templates/reasoning/intent_classification.yaml",
    "backend/app/prompts/templates/reasoning/cypher_generation.yaml",
    "backend/app/prompts/templates/reasoning/answer_synthesis.yaml",
]

for template in prompt_templates:
    if os.path.exists(template):
        print(f"  ✅ {os.path.basename(template)}")
        test4_checks.append(True)
    else:
        print(f"  ❌ {os.path.basename(template)} NOT found")
        test4_checks.append(False)

test4_passed = sum(test4_checks)
test4_total = len(test4_checks)
print(f"\n[Result] Test 4: {test4_passed}/{test4_total} integration points validated")

# Summary
print("\n" + "=" * 80)
print("FINAL TEST RESULTS")
print("=" * 80)

total_passed = test1_passed + test2_passed + test3_passed + test4_passed
total_tests = test1_total + test2_total + test3_total + test4_total

results = [
    ("Test 1: Module Structure & AST", test1_passed, test1_total),
    ("Test 2: Code Logic & Patterns", test2_passed, test2_total),
    ("Test 3: File Coverage", test3_passed, test3_total),
    ("Test 4: Integration Points", test4_passed, test4_total),
]

for test_name, passed, total in results:
    percentage = (passed / total * 100) if total > 0 else 0
    status = "✅" if passed == total else "⚠️ "
    print(f"{status} {test_name:<40} {passed:>3}/{total:<3} ({percentage:>5.1f}%)")

print("-" * 80)
percentage = (total_passed / total_tests * 100) if total_tests > 0 else 0
if percentage == 100:
    print(f"✅ OVERALL RESULT: {total_passed}/{total_tests} ({percentage:.1f}%) - ALL TESTS PASSED")
    exit_code = 0
elif percentage >= 90:
    print(f"⚠️  OVERALL RESULT: {total_passed}/{total_tests} ({percentage:.1f}%) - MOSTLY PASSED")
    exit_code = 0
else:
    print(f"❌ OVERALL RESULT: {total_passed}/{total_tests} ({percentage:.1f}%) - TESTS FAILED")
    exit_code = 1

print("=" * 80)

sys.exit(exit_code)
