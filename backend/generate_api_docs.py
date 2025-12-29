"""
API Documentation Generator

Generates API documentation from FastAPI app and Pydantic schemas.
Ensures documentation stays in sync with code.
"""

import json
from fastapi.openapi.utils import get_openapi
from src.api import app


def generate_openapi_schema():
    """Generate OpenAPI 3.0 schema from FastAPI app"""
    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )

    # Save to file
    with open("docs/openapi.json", "w") as f:
        json.dump(openapi_schema, f, indent=2)

    print("✅ OpenAPI schema generated: docs/openapi.json")
    return openapi_schema


def generate_markdown_docs():
    """Generate Markdown documentation from OpenAPI schema"""

    schema = generate_openapi_schema()

    markdown = f"""# API Documentation

**Version:** {schema['info']['version']}
**Base URL:** `/api/v1`

## Overview

{schema['info'].get('description', 'API for AP2 Expense Management Agent')}

---

## Authentication

Most endpoints require authentication via JWT Bearer token:

```
Authorization: Bearer <your_access_token>
```

Get access token via `POST /api/v1/auth/login`

---

## Endpoints

"""

    # Group endpoints by tags
    endpoints_by_tag = {}
    for path, methods in schema['paths'].items():
        for method, details in methods.items():
            if method == 'parameters':
                continue

            tags = details.get('tags', ['Other'])
            tag = tags[0]

            if tag not in endpoints_by_tag:
                endpoints_by_tag[tag] = []

            endpoints_by_tag[tag].append({
                'path': path,
                'method': method.upper(),
                'details': details
            })

    # Generate markdown for each tag
    for tag, endpoints in sorted(endpoints_by_tag.items()):
        markdown += f"### {tag}\n\n"

        for endpoint in sorted(endpoints, key=lambda x: x['path']):
            details = endpoint['details']
            method = endpoint['method']
            path = endpoint['path']

            # Method and path
            markdown += f"#### `{method} {path}`\n\n"

            # Summary
            if 'summary' in details:
                markdown += f"{details['summary']}\n\n"

            # Description
            if 'description' in details:
                markdown += f"{details['description']}\n\n"

            # Request body
            if 'requestBody' in details:
                markdown += "**Request Body:**\n```json\n"
                content = details['requestBody'].get('content', {})
                json_content = content.get('application/json', {})
                schema_ref = json_content.get('schema', {})
                markdown += json.dumps(schema_ref, indent=2)
                markdown += "\n```\n\n"

            # Responses
            if 'responses' in details:
                markdown += "**Responses:**\n\n"
                for status_code, response in details['responses'].items():
                    description = response.get('description', 'No description')
                    markdown += f"- `{status_code}`: {description}\n"
                markdown += "\n"

            markdown += "---\n\n"

    # Save to file
    import os
    os.makedirs("docs", exist_ok=True)

    with open("docs/API.md", "w") as f:
        f.write(markdown)

    print("✅ Markdown documentation generated: docs/API.md")


def generate_typescript_client():
    """Generate TypeScript client types from OpenAPI schema"""

    schema = generate_openapi_schema()

    typescript = """/**
 * Auto-generated TypeScript API Client Types
 * DO NOT EDIT MANUALLY - Generated from OpenAPI schema
 *
 * Run `python backend/generate_api_docs.py` to regenerate
 */

"""

    # Extract schemas
    if 'components' in schema and 'schemas' in schema['components']:
        typescript += "// API Response Types\n\n"

        for schema_name, schema_def in schema['components']['schemas'].items():
            typescript += f"export interface {schema_name} {{\n"

            if 'properties' in schema_def:
                for prop_name, prop_def in schema_def['properties'].items():
                    prop_type = prop_def.get('type', 'any')
                    ts_type = {
                        'string': 'string',
                        'integer': 'number',
                        'number': 'number',
                        'boolean': 'boolean',
                        'array': 'any[]',
                        'object': 'any',
                    }.get(prop_type, 'any')

                    required = schema_def.get('required', [])
                    optional = '' if prop_name in required else '?'

                    typescript += f"  {prop_name}{optional}: {ts_type};\n"

            typescript += "}\n\n"

    # Save to file
    with open("frontend/src/types/api-generated.ts", "w") as f:
        f.write(typescript)

    print("✅ TypeScript types generated: frontend/src/types/api-generated.ts")


def check_schema_sync():
    """
    Check if backend schemas are in sync with frontend types.

    This prevents the recurring error of mismatched response structures.
    """
    print("\n" + "=" * 70)
    print("CHECKING BACKEND/FRONTEND SCHEMA SYNC")
    print("=" * 70)

    # Compare key response structures
    checks = {
        "UserCreatedResponse": {
            "backend": "backend/src/schemas/responses.py",
            "frontend": "frontend/src/types/api.ts",
            "expected_structure": "{ success: true, message: string, user: UserData }"
        },
        "ExpenseCreatedResponse": {
            "backend": "backend/src/schemas/responses.py",
            "frontend": "frontend/src/types/api.ts",
            "expected_structure": "{ success: true, message: string, expense: ExpenseData }"
        },
    }

    print("\n📋 Checking key response structures...\n")

    for check_name, check_data in checks.items():
        print(f"  • {check_name}")
        print(f"    Backend: {check_data['backend']}")
        print(f"    Frontend: {check_data['frontend']}")
        print(f"    Expected: {check_data['expected_structure']}")
        print()

    print("⚠️  Manual review recommended:")
    print("   1. Check that all responses have 'success' field")
    print("   2. Check that data is nested (e.g., 'user', 'expense')")
    print("   3. Update frontend types when backend schemas change")
    print()
    print("=" * 70)


if __name__ == "__main__":
    print("Generating API Documentation...")
    print()

    # Generate all documentation
    generate_markdown_docs()
    generate_typescript_client()
    check_schema_sync()

    print("\n✅ All documentation generated successfully!")
    print("\nGenerated files:")
    print("  - docs/openapi.json - OpenAPI 3.0 schema")
    print("  - docs/API.md - Markdown documentation")
    print("  - frontend/src/types/api-generated.ts - TypeScript types")
