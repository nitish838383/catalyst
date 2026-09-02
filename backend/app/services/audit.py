import json
from app.models.audit import AuditLog

def log_action(db,user_id,action,entity_type=None,entity_id=None,metadata=None):
    db.add(AuditLog(user_id=user_id,action=action,entity_type=entity_type,entity_id=entity_id,metadata_json=json.dumps(metadata) if metadata else None))
