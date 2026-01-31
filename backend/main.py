from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
import math
import random
from typing import Any, Dict, List

import pandas as pd
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field


app = FastAPI(title="Group Formation API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class GroupRequest(BaseModel):
    participants: List[Dict[str, Any]]
    group_size: int = Field(5, ge=2, le=50)
    id_column: str = "Participant_ID"


@dataclass
class GroupingResult:
    groups: List[Dict[str, Any]]
    stats: Dict[str, Any]


def normalize_participants(participants: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    cleaned = []
    for row in participants:
        cleaned_row = {}
        for key, value in row.items():
            if value is None:
                cleaned_row[key] = ""
            else:
                cleaned_row[key] = value
        cleaned.append(cleaned_row)
    return cleaned


def extract_attribute_columns(participants: List[Dict[str, Any]], id_column: str) -> List[str]:
    if not participants:
        return []
    columns = set()
    for row in participants:
        columns.update(row.keys())
    columns.discard(id_column)
    return sorted(columns)


def diversity_score(candidate: Dict[str, Any], group: List[Dict[str, Any]], columns: List[str]) -> int:
    score = 0
    for column in columns:
        candidate_value = candidate.get(column, "")
        if candidate_value == "":
            continue
        score += sum(1 for member in group if member.get(column, "") == candidate_value)
    return score


def build_groups(participants: List[Dict[str, Any]], group_size: int, id_column: str) -> GroupingResult:
    participants = normalize_participants(participants)
    if not participants:
        raise HTTPException(status_code=400, detail="No participants provided.")

    if any(id_column not in row or str(row.get(id_column, "")).strip() == "" for row in participants):
        raise HTTPException(status_code=400, detail=f"Each participant must include {id_column}.")

    columns = extract_attribute_columns(participants, id_column)
    shuffled = participants[:]
    random.shuffle(shuffled)

    num_groups = max(1, math.ceil(len(shuffled) / group_size))
    groups: List[List[Dict[str, Any]]] = [[] for _ in range(num_groups)]

    for participant in shuffled:
        best_group_index = None
        best_score = None
        for index, group in enumerate(groups):
            if len(group) >= group_size:
                continue
            score = diversity_score(participant, group, columns)
            if best_score is None or score < best_score:
                best_score = score
                best_group_index = index
        if best_group_index is None:
            best_group_index = min(range(num_groups), key=lambda i: len(groups[i]))
        groups[best_group_index].append(participant)

    response_groups = [
        {"group_id": idx + 1, "participants": members}
        for idx, members in enumerate(groups)
    ]

    stats = {
        "total_participants": len(participants),
        "group_size": group_size,
        "groups": len(response_groups),
        "attribute_columns": columns,
    }
    return GroupingResult(groups=response_groups, stats=stats)


async def read_uploaded_file(upload: UploadFile) -> List[Dict[str, Any]]:
    content = await upload.read()
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded file was empty.")

    buffer = BytesIO(content)
    filename = upload.filename or ""
    if filename.lower().endswith(".csv"):
        df = pd.read_csv(buffer)
    elif filename.lower().endswith(".xlsx"):
        df = pd.read_excel(buffer)
    else:
        raise HTTPException(status_code=400, detail="Only .csv or .xlsx files are supported.")

    df = df.fillna("")
    return df.to_dict(orient="records")


@app.get("/api/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.post("/api/groups")
def create_groups(payload: GroupRequest) -> Dict[str, Any]:
    result = build_groups(payload.participants, payload.group_size, payload.id_column)
    return {"groups": result.groups, "stats": result.stats}


@app.post("/api/groups/from-file")
async def create_groups_from_file(
    file: UploadFile = File(...),
    group_size: int = 5,
    id_column: str = "Participant_ID",
) -> Dict[str, Any]:
    participants = await read_uploaded_file(file)
    result = build_groups(participants, group_size, id_column)
    return {"groups": result.groups, "stats": result.stats}
