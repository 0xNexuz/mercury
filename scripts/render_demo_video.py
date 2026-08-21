"""Render the captions-only MERCURY product demo from committed visual assets."""

from __future__ import annotations

import math
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
WIDTH, HEIGHT, FPS = 1280, 720, 12
CYAN = (230, 215, 70)
WHITE = (242, 242, 242)
MUTED = (145, 145, 145)
GREEN = (125, 230, 110)
RED = (80, 100, 245)


def text(frame: np.ndarray, value: str, x: int, y: int, size: float, color=WHITE, thickness: int = 1) -> None:
    cv2.putText(frame, value, (x, y), cv2.FONT_HERSHEY_DUPLEX, size, color, thickness, cv2.LINE_AA)


def base_frame(second: float) -> np.ndarray:
    frame = np.zeros((HEIGHT, WIDTH, 3), dtype=np.uint8)
    frame[:] = (5, 5, 5)
    for y in range(0, HEIGHT, 4):
        frame[y : y + 1] = (8, 8, 8)
    cv2.rectangle(frame, (24, 22), (WIDTH - 24, HEIGHT - 22), (45, 45, 45), 1)
    cut = 34
    for x, y, sx, sy in [(24, 22, 1, 1), (WIDTH - 24, 22, -1, 1), (24, HEIGHT - 22, 1, -1), (WIDTH - 24, HEIGHT - 22, -1, -1)]:
        cv2.line(frame, (x, y), (x + sx * cut, y), CYAN, 2)
        cv2.line(frame, (x, y), (x, y + sy * cut), CYAN, 2)
    text(frame, "M", 48, 67, 1.0, CYAN, 2)
    text(frame, "MERCURY", 88, 55, 0.55, WHITE, 1)
    text(frame, "PERSISTENT INCIDENT INTELLIGENCE", 88, 73, 0.26, MUTED, 1)
    text(frame, f"T+{second:05.1f}", WIDTH - 138, 57, 0.34, MUTED, 1)
    scan_y = 94 + int((HEIGHT - 145) * ((second * 0.16) % 1))
    cv2.line(frame, (25, scan_y), (WIDTH - 25, scan_y), (24, 34, 34), 1)
    return frame


def paste_cover(frame: np.ndarray, image: np.ndarray, box: tuple[int, int, int, int], alpha: float = 1.0) -> None:
    x, y, w, h = box
    scale = max(w / image.shape[1], h / image.shape[0])
    resized = cv2.resize(image, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
    ox = max(0, (resized.shape[1] - w) // 2)
    oy = max(0, (resized.shape[0] - h) // 2)
    crop = resized[oy : oy + h, ox : ox + w]
    frame[y : y + h, x : x + w] = cv2.addWeighted(crop, alpha, frame[y : y + h, x : x + w], 1 - alpha, 0)


def panel(frame: np.ndarray, x: int, y: int, w: int, h: int, accent=CYAN) -> None:
    overlay = frame.copy()
    cv2.rectangle(overlay, (x, y), (x + w, y + h), (14, 14, 14), -1)
    frame[:] = cv2.addWeighted(overlay, 0.9, frame, 0.1, 0)
    cv2.rectangle(frame, (x, y), (x + w, y + h), (54, 54, 54), 1)
    cv2.line(frame, (x, y), (x + w, y), accent, 2)


def render(output: Path) -> None:
    brain = cv2.imread(str(ROOT / "public" / "memory-brain.png"))
    if brain is None:
        raise RuntimeError("public/memory-brain.png is required")
    output.parent.mkdir(parents=True, exist_ok=True)
    writer = cv2.VideoWriter(str(output), cv2.VideoWriter_fourcc(*"mp4v"), FPS, (WIDTH, HEIGHT))
    duration = 27
    for index in range(duration * FPS):
        second = index / FPS
        frame = base_frame(second)
        if second < 4:
            drift = int(math.sin(second * 1.8) * 8)
            paste_cover(frame, brain, (625, 105 + drift, 560, 500), 0.72)
            text(frame, "LOAD-BEARING MEMORY / 01", 76, 145, 0.42, CYAN, 1)
            text(frame, "MEMORY", 72, 235, 1.45, WHITE, 2)
            text(frame, "CHANGED", 72, 315, 1.45, WHITE, 2)
            text(frame, "THE DECISION.", 72, 395, 1.18, CYAN, 2)
            text(frame, "A fresh session behaves differently because Sibyl remembers.", 77, 455, 0.43, MUTED, 1)
        elif second < 9:
            text(frame, "SESSION A / TEACH THE SYSTEM", 66, 140, 0.48, CYAN, 1)
            panel(frame, 66, 182, 1148, 375)
            text(frame, "INC-104", 100, 235, 0.48, MUTED)
            text(frame, "PAYMENTS QUEUE BACKLOG", 100, 285, 0.85, WHITE, 2)
            text(frame, "ACTION", 100, 350, 0.34, MUTED)
            text(frame, "RESTART WORKER", 100, 390, 0.72, WHITE, 1)
            text(frame, "OUTCOME", 685, 350, 0.34, MUTED)
            text(frame, "WORSE", 685, 390, 0.72, RED, 2)
            cv2.line(frame, (100, 425), (1125, 425), (45, 45, 45), 1)
            text(frame, "Persisted as a real Sibyl incident entity + journal outcome", 100, 475, 0.48, CYAN)
            text(frame, "PROCESS ENDS / SQLITE + FTS5 MEMORY SURVIVES", 100, 520, 0.38, MUTED)
        elif second < 15:
            text(frame, "FRESH SESSION B / SAME SYMPTOMS", 66, 140, 0.48, CYAN, 1)
            panel(frame, 66, 182, 510, 350, (85, 85, 85))
            panel(frame, 704, 182, 510, 350, CYAN)
            text(frame, "WITHOUT MEMORY", 100, 235, 0.38, MUTED)
            text(frame, "RESTART", 100, 320, 1.05, WHITE, 2)
            text(frame, "WORKER", 100, 385, 1.05, WHITE, 2)
            text(frame, "72% confidence", 100, 455, 0.42, MUTED)
            text(frame, ">", 610, 365, 1.2, CYAN, 2)
            text(frame, "WITH SIBYL MEMORY", 738, 235, 0.38, CYAN)
            text(frame, "DRAIN QUEUE", 738, 320, 0.82, WHITE, 2)
            text(frame, "+ ROLLBACK", 738, 385, 0.82, WHITE, 2)
            text(frame, "91% confidence", 738, 455, 0.42, GREEN)
            text(frame, "MEMORY CHANGED THIS DECISION", 376, 592, 0.62, CYAN, 2)
        elif second < 20:
            text(frame, "EXPLAINABLE EVIDENCE / NO LLM IN THE CRITICAL PATH", 66, 140, 0.45, CYAN)
            labels = [("SERVICE", 35), ("SYMPTOMS", 30), ("CATEGORY", 20), ("ERROR SIG.", 10), ("DEPENDENCY", 5)]
            for row, (name, score) in enumerate(labels):
                y = 215 + row * 70
                text(frame, name, 90, y + 15, 0.42, WHITE)
                cv2.rectangle(frame, (300, y - 8), (1050, y + 18), (24, 24, 24), -1)
                cv2.rectangle(frame, (300, y - 8), (300 + int(750 * score / 35), y + 18), CYAN, -1)
                text(frame, f"{score}%", 1080, y + 15, 0.38, MUTED)
            text(frame, "QUALIFY >= 0.55 / UNRESOLVED + SUPERSEDED MEMORIES EXCLUDED", 90, 608, 0.38, MUTED)
        elif second < 24:
            text(frame, "SAFETY RUNS AFTER MEMORY INFLUENCE", 66, 140, 0.5, CYAN)
            panel(frame, 66, 185, 550, 335)
            panel(frame, 664, 185, 550, 335)
            text(frame, "POLICY", 100, 235, 0.36, MUTED)
            text(frame, "MEMORY CAN CHANGE", 100, 305, 0.58, WHITE)
            text(frame, "ACTION + CONFIDENCE", 100, 350, 0.58, WHITE)
            text(frame, "IT CANNOT LOWER RISK", 100, 420, 0.55, CYAN)
            text(frame, "PROVENANCE", 698, 235, 0.36, MUTED)
            text(frame, "CANONICAL KECCAK", 698, 305, 0.58, WHITE)
            text(frame, "BASE SEPOLIA RECEIPT", 698, 350, 0.58, WHITE)
            text(frame, "UNANCHORED UNTIL VERIFIED", 698, 420, 0.48, CYAN)
        else:
            paste_cover(frame, brain, (760, 120, 400, 400), 0.45)
            text(frame, "RUN THE PROOF", 74, 205, 0.46, CYAN)
            text(frame, "1. RECORD SESSION A", 74, 285, 0.72, WHITE, 2)
            text(frame, "2. START FRESH SESSION B", 74, 355, 0.72, WHITE, 2)
            text(frame, "3. OPEN TECHNICAL EVIDENCE", 74, 425, 0.72, WHITE, 2)
            text(frame, "mercury-ir.vercel.app  /  github.com/0xNexuz/mercury", 74, 555, 0.42, MUTED)
            text(frame, "REAL MEMORY / SIMULATED MITIGATION / VERIFIED RECEIPTS ONLY", 74, 605, 0.37, CYAN)
        writer.write(frame)
    writer.release()


if __name__ == "__main__":
    render(ROOT / "public" / "mercury-demo.mp4")
