"""SHA-256 Blockchain-Style Tamper-Evident Audit Trail.

All model predictions, forecaster sign-offs, and parameter overrides are recorded
into a JSONL log file where each entry is cryptographically chained to the previous entry,
making any retroactive modification detectable via hash verification.
"""

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.core.config import LOGS_DIR

AUDIT_LOG_PATH = LOGS_DIR / "cyclone_audit_trail.jsonl"


def _sha256(data: str) -> str:
    """Compute SHA-256 hexdigest of an arbitrary string."""
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def _load_last_hash(log_path: Path) -> str:
    """Read the hash of the most recent audit record, or a genesis hash if log is empty."""
    if not log_path.exists() or log_path.stat().st_size == 0:
        return _sha256("GENESIS:SIH2026:CYCLONE_AI_SYSTEM:MoES_IMD")
    # Read last line
    last_line = ""
    with open(log_path, "r", encoding="utf-8") as f:
        for line in f:
            stripped = line.strip()
            if stripped:
                last_line = stripped
    if not last_line:
        return _sha256("GENESIS:SIH2026:CYCLONE_AI_SYSTEM:MoES_IMD")
    try:
        record = json.loads(last_line)
        return record.get("record_hash", _sha256(last_line))
    except json.JSONDecodeError:
        return _sha256(last_line)


class AuditTrailManager:
    """Manages cryptographic SHA-256 chained audit records for full forecaster accountability."""

    def __init__(self, log_path: Optional[Path] = None):
        self.log_path = log_path or AUDIT_LOG_PATH
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

    def log_prediction(
        self,
        frame_id: str,
        model_version: str,
        predictions: Dict[str, Any],
        forecaster_id: str = "SYSTEM_AUTO",
        forecaster_corrections: Optional[Dict[str, Any]] = None,
        forecaster_notes: str = "Automated AI prediction — awaiting forecaster review.",
        status: str = "PENDING_REVIEW",
    ) -> Dict[str, Any]:
        """Append a tamper-evident prediction record to the audit chain.
        
        Returns the created audit record with its SHA-256 hash.
        """
        now_utc = datetime.now(timezone.utc)
        prev_hash = _load_last_hash(self.log_path)

        # Serialize core payload deterministically
        payload_obj = {
            "timestamp": now_utc.isoformat(),
            "frame_id": frame_id,
            "model_version": model_version,
            "forecaster_id": forecaster_id,
            "status": status,
            "predictions": predictions,
            "forecaster_corrections": forecaster_corrections or {},
            "forecaster_notes": forecaster_notes,
            "previous_record_hash": prev_hash,
        }
        payload_str = json.dumps(payload_obj, sort_keys=True, default=str)
        record_hash = _sha256(payload_str)

        record = {**payload_obj, "record_hash": record_hash}

        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, default=str) + "\n")

        return record

    def verify_chain(self) -> Dict[str, Any]:
        """Verify that no audit record has been tampered with by re-computing the hash chain.
        
        Returns:
            {"valid": bool, "records_checked": int, "first_tampered_index": Optional[int], "details": str}
        """
        if not self.log_path.exists():
            return {"valid": True, "records_checked": 0, "details": "No audit log found — chain is empty."}

        records = []
        with open(self.log_path, "r", encoding="utf-8") as f:
            for line in f:
                stripped = line.strip()
                if stripped:
                    records.append(json.loads(stripped))

        if not records:
            return {"valid": True, "records_checked": 0, "details": "Empty audit log."}

        prev_hash = _sha256("GENESIS:SIH2026:CYCLONE_AI_SYSTEM:MoES_IMD")

        for i, record in enumerate(records):
            stored_hash = record.pop("record_hash")
            record["previous_record_hash"] = prev_hash
            recomputed_str = json.dumps(record, sort_keys=True, default=str)
            recomputed_hash = _sha256(recomputed_str)

            if recomputed_hash != stored_hash and record.get("previous_record_hash") == prev_hash:
                # Strict: prev_hash must match
                pass  # allow chain-based check below

            record["record_hash"] = stored_hash  # restore

            # Validate this record
            payload_for_hash = {k: v for k, v in record.items() if k != "record_hash"}
            payload_for_hash["previous_record_hash"] = prev_hash
            expected_hash = _sha256(json.dumps(payload_for_hash, sort_keys=True, default=str))

            if expected_hash != stored_hash:
                return {
                    "valid": False,
                    "records_checked": i + 1,
                    "first_tampered_index": i,
                    "details": f"Tampering detected at record index {i} (frame_id: {record.get('frame_id', 'UNKNOWN')}). Expected hash {expected_hash[:16]}... but found {stored_hash[:16]}...",
                }
            prev_hash = stored_hash

        return {
            "valid": True,
            "records_checked": len(records),
            "details": f"Audit chain verified successfully across {len(records)} prediction records. Hash integrity confirmed.",
        }

    def get_audit_log(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Load the most recent N audit records."""
        if not self.log_path.exists():
            return []
        records = []
        with open(self.log_path, "r", encoding="utf-8") as f:
            for line in f:
                stripped = line.strip()
                if stripped:
                    records.append(json.loads(stripped))
        return records[-limit:]
