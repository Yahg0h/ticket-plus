"""
All services related to audit logs used across all TicketPlus routes.
"""

import json
from datetime import datetime

from sqlalchemy import text

from app.database import engine

# ==========================================
# AUDIT LOG DATABASE OPERATIONS
# ==========================================

async def log_action(
    action: str,
    auditable_type: str,
    auditable_id: int,
    user_id: int | None = None,
    old_values: dict | None = None,
    new_values: dict | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None
) -> int:
    """
    Log an action to the audit_logs table.
    
    Args:
        action: Action type (create, update, delete, login, logout)
        auditable_type: Type of resource (user, event, order, ticket, etc)
        auditable_id: ID of the affected resource
        user_id: ID of the user who performed the action (optional)
        old_values: Previous values as dict (optional)
        new_values: New values as dict (optional)
        ip_address: IP address of the requester (optional)
        user_agent: User-Agent string (optional)
    
    Returns:
        int: The newly created audit_log's ID
    
    Raises:
        ValueError: If database operation fails
    """
    # If there was a change in values, convert them from dict to a JSON string
    old_values_json = json.dumps(old_values) if old_values else None
    new_values_json = json.dumps(new_values) if new_values else None

    # Connect to database
    async with engine.connect() as conn:
        # INSERT into the database the log action info
        insert_query = """
        INSERT INTO audit_logs (user_id, action, auditable_type, auditable_id, old_values, new_values, ip_address, user_agent)
        VALUES (:user_id, :action, :auditable_type, :auditable_id, :old_values, :new_values, :ip_address, :user_agent)
        """
        await conn.execute(text(insert_query), {"user_id": user_id, "action": action, "auditable_type": auditable_type, "auditable_id": auditable_id,
                                                "old_values": old_values_json, "new_values": new_values_json, "ip_address": ip_address, "user_agent": user_agent})
        await conn.commit()

        # Fetch the id of the recently added log
        query = await conn.execute(text("SELECT id FROM audit_logs WHERE id = LAST_INSERT_ID()"))
        recent_log_id = query.scalar() # Convert from row to int

        # Return it
        return recent_log_id

async def get_audit_logs(
    limit: int = 100,
    offset: int = 0,
    user_id: int | None = None,
    auditable_type: str | None = None,
    action: str | None = None
) -> list[dict]:
    """
    Fetch audit logs with optional filters.
    
    Args:
        limit: Maximum number of logs to return (default 100)
        offset: Offset for pagination (default 0)
        user_id: Filter by user ID (optional)
        auditable_type: Filter by resource type (optional)
        action: Filter by action type (optional)
    
    Returns:
        list: List of audit log dicts
    """
    # Create a dynamic query that changes based on the filters selected
    query = "SELECT * FROM audit_logs WHERE 1=1"
    params = {}

    if user_id:
        query += " AND user_id = :user_id"
        params["user_id"] = user_id

    if auditable_type:
        query += " AND auditable_type = :auditable_type"
        params["auditable_type"] = auditable_type

    if action:
        query += " AND action = :action"
        params["action"] = action

    # Connect to database
    async with engine.connect() as conn:
        # Get log info for each audit log found (for those that fall under the selected filters)
        paginated_query = query + " ORDER BY created_at DESC LIMIT :limit OFFSET :offset"
        params["limit"] = limit
        params["offset"] = offset

        result = await conn.execute(text(paginated_query), params)
        logs = result.mappings().all()

        # Convert each log to a list and then add each log info to a list
        log_list = [dict(log_row) for log_row in logs]

    # Return the list with all info (log_list)
    return log_list

async def get_audit_logs_by_resource(
    auditable_type: str,
    auditable_id: int
) -> list[dict]:
    """
    Fetch complete audit history for a specific resource.
    
    Args:
        auditable_type: Type of resource (user, event, order, ticket, etc)
        auditable_id: ID of the specific resource
    
    Returns:
        list: List of audit log dicts in chronological order
    """
    # Connect to database
    async with engine.connect() as conn:
        # Search DB for all logs under a certain resource in chronological order
        search_query = """
        SELECT * FROM audit_logs
        WHERE auditable_type = :auditable_type AND auditable_id = :auditable_id
        ORDER BY created_at ASC
        """
        query = await conn.execute(text(search_query), {"auditable_type": auditable_type, "auditable_id": auditable_id})
        logs = query.mappings().all()

        # Convert each low from row to dict, then add them to a list
        log_list = [dict(log_row) for log_row in logs]

    # Return log list
    return log_list


async def get_audit_logs_by_user(
    user_id: int,
    limit: int = 100,
    offset: int = 0
) -> list[dict]:
    """
    Fetch all actions performed by a specific user.
    
    Args:
        user_id: User ID to filter by
        limit: Maximum number of logs to return
        offset: Offset for pagination
    
    Returns:
        list: List of audit log dicts
    """
    # Connect to database
    async with engine.connect() as conn:
        # Search DB for all logs registered under a user and filter it (with limit and offset)
        search_query = """
        SELECT * FROM audit_logs
        WHERE user_id = :user_id
        ORDER BY created_at DESC
        LIMIT :limit OFFSET :offset
        """
        query = await conn.execute(text(search_query), {"user_id": user_id, "limit": limit, "offset": offset})
        logs = query.mappings().all()

        # Convert each log row to a dict, then add it to a list
        log_list = [dict(log_row) for log_row in logs]

    # Return log list
    return log_list


# ==========================================
# AUDIT LOG ANALYSIS & REPORTING
# ==========================================

async def get_recent_actions(hours: int = 24) -> list[dict]:
    """
    Fetch actions from the last N hours (useful for monitoring/alerts).
    
    Args:
        hours: Number of hours to look back (default 24)
    
    Returns:
        list: List of recent audit logs
    """
    # Connect to database
    async with engine.connect() as conn:
        # Search DB for all logs made in the last N hours
        search_query = """
        SELECT * FROM audit_logs
        WHERE created_at >= DATE_SUB(NOW(), INTERVAL :hours HOUR)
        ORDER BY created_at DESC
        """
        query = await conn.execute(text(search_query), {"hours": hours})
        logs = query.mappings().all()

        # Convert each log row to a dict, then add it to a list
        log_list = [dict(log_row) for log_row in logs]

    # Return log lits
    return log_list


async def get_action_statistics() -> dict:
    """
    Get statistics about actions (counts by type, by resource, etc).
    
    Returns:
        dict: Statistics about actions
            {
                "total": int,
                "by_action": {action: count, ...},
                "by_resource": {auditable_type: count, ...}
            }
    """
    # Connect to database
    async with engine.connect() as conn:
        # Search DB to get all stats about actions logged.
        # Total actions count
        total_query = await conn.execute(text("SELECT COUNT(*) as total FROM audit_logs"))
        total = total_query.scalar()

        # Total actions by type count
        actions_type_query = await conn.execute(text("SELECT action, COUNT(*) as count FROM audit_logs GROUP BY action"))
        actions_type = {row.action: row.count for row in actions_type_query.all()}

        # Total actions by resource count
        actions_resource_query = await conn.execute(text("SELECT auditable_type, COUNT(*) as count FROM audit_logs GROUP BY auditable_type"))
        actions_resource = {row.auditable_type: row.count for row in actions_resource_query.all()}

        # Organize the information in a statistics dict
        stats_dict = {
            "total": total,
            "by_action": actions_type,
            "by_resource": actions_resource
        }

    # Return stats dict
    return stats_dict

# ==========================================
# UTILITY FUNCTIONS
# ==========================================

def get_ip_from_request(request) -> str | None:
    """
    Extract IP address from FastAPI Request object.
    
    Args:
        request: FastAPI Request object
    
    Returns:
        str or None: IP address or None
    """
    # Try fetching the IP address from the client connection
    if request.client and request.client.host:
        return request.client.host

    # If IP not available/found, try looking for it in the proxies header
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        # The first IP in the list is the client original only, no proxies
        return forwarded_for.split(",")[0].strip()

    # If nothing works and IP can't be found, return None
    return None

def get_user_agent_from_request(request) -> str | None:
    """
    Extract User-Agent from FastAPI Request object.
    
    Args:
        request: FastAPI Request object
    
    Returns:
        str or None: User-Agent string or None
    """
    # Extract the User-Agent from the request
    user_agent = request.headers.get("user-agent")

    # If the User-Agent has been found, return it
    if user_agent:
        return user_agent

    # Else, return None
    return None


def prepare_old_new_values(old_dict: dict | None, new_dict: dict | None, exclude_fields: list[str] | None = None) -> tuple[str | None, str | None]:
    """
    Prepare old_values and new_values for audit logging (filter sensitive fields).
    
    Args:
        old_dict: Dictionary of old values (optional)
        new_dict: Dictionary of new values (optional)
        exclude_fields: List of field names to exclude (optional)
    
    Returns:
        tuple: (old_values_json_str, new_values_json_str) — both can be None
    """
    # Create default list of sensitive data to exclude
    default_exclude = ["password_hash", "cpf", "stripe_payment_id", "holder_cpf"]

    # If exclude_fields was provided, merge with default
    if exclude_fields:
        fields_to_exclude = default_exclude + exclude_fields
    else:
        # Else, use the default list
        fields_to_exclude = default_exclude

    # Filter old dict
    filtered_old = None
    if old_dict:
        filtered_old = {k: v for k, v in old_dict.items() if k not in fields_to_exclude}
        filtered_old = json.dumps(filtered_old) if filtered_old else None

    # Filter new dict
    filtered_new = None
    if new_dict:
        filtered_new = {k: v for k, v in new_dict.items() if k not in fields_to_exclude}
        filtered_new = json.dumps(filtered_new) if filtered_new else None

    # Return old and new values in a dict
    return (filtered_old, filtered_new)