# -*- coding: utf-8 -*-
"""自动导出 Pydantic 数据模型对应的 JSON Schema 到 publishing/schemas/"""
import os, json, sys

# Ensure package is on sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from weekly_pipeline.models import (
    SourceDocument, EventPacket, RetellingUnit, CommentaryUnit, ExcerptUnit, IssueManifest
)

SCHEMA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "schemas")

MODELS = {
    "source_document.schema.json": SourceDocument,
    "event_packet.schema.json": EventPacket,
    "retelling_unit.schema.json": RetellingUnit,
    "commentary_unit.schema.json": CommentaryUnit,
    "excerpt_unit.schema.json": ExcerptUnit,
    "issue_manifest.schema.json": IssueManifest,
}

def export_all():
    os.makedirs(SCHEMA_DIR, exist_ok=True)
    exported = []
    for filename, model_cls in MODELS.items():
        out_path = os.path.join(SCHEMA_DIR, filename)
        schema = model_cls.model_json_schema()
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(schema, f, ensure_ascii=False, indent=2)
        exported.append(filename)
        print(f"Exported: {filename}")
    return exported

if __name__ == "__main__":
    export_all()
