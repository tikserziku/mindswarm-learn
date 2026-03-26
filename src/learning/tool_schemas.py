"""Challenge 5: Real Claude tool_use — JSON schemas for all agent tools.

Course: Tool Use, Lessons 1-3
  - Lesson 1: Tool definitions with JSON Schema
  - Lesson 2: Single tool execution
  - Lesson 3: Multi-tool orchestration

Each tool schema follows the Anthropic tool_use format:
{
    "name": "tool_name",
    "description": "What this tool does",
    "input_schema": { JSON Schema }
}
"""

from __future__ import annotations
from typing import Any


# ─── Policy Evaluation Tools ───

TOOL_READ_POLICY_RULES = {
    "name": "read_policy_rules",
    "description": "Read the current policy rules from the platform configuration. Returns a list of rules with actions, conditions, and effects (allow/deny/review).",
    "input_schema": {
        "type": "object",
        "properties": {},
        "required": [],
    },
}

TOOL_CALCULATE_RISK_SCORE = {
    "name": "calculate_risk_score",
    "description": "Calculate the risk score for a given action based on plan tier, powerup tier, disk size, and other factors. Returns the numeric score and risk factors.",
    "input_schema": {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "description": "The action being evaluated (e.g., install_powerup, upgrade_vm)",
            },
            "plan_tier": {
                "type": "string",
                "enum": ["free", "pro", "scale"],
                "description": "The client's plan tier",
            },
            "powerup_tier": {
                "type": "string",
                "enum": ["basic", "advanced", "pro", "ultra"],
                "description": "The tier of the powerup being installed",
            },
            "disk_additional_gb": {
                "type": "integer",
                "description": "Additional disk space requested in GB",
            },
            "machine_type": {
                "type": "string",
                "description": "Target machine type (e.g., e2-micro, n1-standard-4)",
            },
        },
        "required": ["action", "plan_tier"],
    },
}

TOOL_CHECK_QUORUM = {
    "name": "check_quorum_requirements",
    "description": "Determine how many approvals are required for this action based on risk level and action type.",
    "input_schema": {
        "type": "object",
        "properties": {
            "risk_level": {
                "type": "string",
                "enum": ["low", "medium", "high"],
                "description": "The calculated risk level",
            },
            "risk_score": {
                "type": "integer",
                "description": "The numeric risk score",
            },
        },
        "required": ["risk_level", "risk_score"],
    },
}


# ─── Provisioning Tools ───

TOOL_FREE_TIER_PRECHECK = {
    "name": "free_tier_precheck",
    "description": "Check if the GCP project already has a free-tier VM. If yes, the new VM cannot be created under the free plan.",
    "input_schema": {
        "type": "object",
        "properties": {
            "env_id": {
                "type": "string",
                "description": "Environment ID to check",
            },
        },
        "required": ["env_id"],
    },
}

TOOL_TERRAFORM_APPLY = {
    "name": "terraform_apply",
    "description": "Run terraform init and terraform apply to create infrastructure for the environment. This creates the VM, network, and firewall rules.",
    "input_schema": {
        "type": "object",
        "properties": {
            "env_id": {
                "type": "string",
                "description": "Environment ID to provision",
            },
        },
        "required": ["env_id"],
    },
}

TOOL_TERRAFORM_DESTROY = {
    "name": "terraform_destroy",
    "description": "Run terraform destroy to remove all infrastructure for the environment. This deletes the VM and associated resources.",
    "input_schema": {
        "type": "object",
        "properties": {
            "env_id": {
                "type": "string",
                "description": "Environment ID to destroy",
            },
        },
        "required": ["env_id"],
    },
}

TOOL_FETCH_EXTERNAL_IP = {
    "name": "fetch_external_ip",
    "description": "Fetch the external IP address of a provisioned VM using gcloud.",
    "input_schema": {
        "type": "object",
        "properties": {
            "env_id": {
                "type": "string",
                "description": "Environment ID to get IP for",
            },
        },
        "required": ["env_id"],
    },
}


# ─── Power-up Tools ───

TOOL_CHECK_COMPATIBILITY = {
    "name": "check_compatibility",
    "description": "Check if a powerup is compatible with the current VM specs (machine type, disk size). Returns compatibility status and required upgrades if needed.",
    "input_schema": {
        "type": "object",
        "properties": {
            "env_id": {
                "type": "string",
                "description": "Environment ID",
            },
            "powerup_id": {
                "type": "string",
                "description": "Power-up to check compatibility for",
            },
        },
        "required": ["env_id", "powerup_id"],
    },
}

TOOL_INSTALL_POWERUP = {
    "name": "install_powerup",
    "description": "Install a power-up on the environment. Handles dependency resolution automatically.",
    "input_schema": {
        "type": "object",
        "properties": {
            "env_id": {
                "type": "string",
                "description": "Environment ID",
            },
            "powerup_id": {
                "type": "string",
                "description": "Power-up to install",
            },
        },
        "required": ["env_id", "powerup_id"],
    },
}

TOOL_UNINSTALL_POWERUP = {
    "name": "uninstall_powerup",
    "description": "Uninstall a power-up from the environment. Warns if other powerups depend on it.",
    "input_schema": {
        "type": "object",
        "properties": {
            "env_id": {
                "type": "string",
                "description": "Environment ID",
            },
            "powerup_id": {
                "type": "string",
                "description": "Power-up to uninstall",
            },
        },
        "required": ["env_id", "powerup_id"],
    },
}


# ─── VM Upgrade Tools ───

TOOL_UPGRADE_VM = {
    "name": "upgrade_vm",
    "description": "Upgrade a VM's machine type and/or disk size. Performs a safe sequence: stop → resize → start → verify.",
    "input_schema": {
        "type": "object",
        "properties": {
            "env_id": {
                "type": "string",
                "description": "Environment ID",
            },
            "new_machine_type": {
                "type": "string",
                "description": "Target machine type (e.g., e2-small, n1-standard-2)",
            },
            "additional_disk_gb": {
                "type": "integer",
                "description": "Additional disk space in GB",
            },
        },
        "required": ["env_id"],
    },
}


# ─── Budget Tools ───

TOOL_CONSUME_BUDGET = {
    "name": "consume_budget",
    "description": "Check and consume the daily operations budget for an environment. Prevents over-usage.",
    "input_schema": {
        "type": "object",
        "properties": {
            "env_id": {
                "type": "string",
                "description": "Environment ID",
            },
            "job_type": {
                "type": "string",
                "description": "Type of job consuming budget",
            },
        },
        "required": ["env_id", "job_type"],
    },
}


# ─── Environment Status Tools ───

TOOL_UPDATE_ENV = {
    "name": "update_environment_status",
    "description": "Update the status of an environment (e.g., to 'ready', 'stopped', 'failed').",
    "input_schema": {
        "type": "object",
        "properties": {
            "env_id": {
                "type": "string",
                "description": "Environment ID",
            },
            "status": {
                "type": "string",
                "description": "New status value",
            },
        },
        "required": ["env_id", "status"],
    },
}


# ─── Support Chatbot Tools (Challenge 6) ───

TOOL_GET_ENVIRONMENT_STATUS = {
    "name": "get_environment_status",
    "description": "Get the current status and details of a client's environment including VM specs, IP, installed powerups, and health.",
    "input_schema": {
        "type": "object",
        "properties": {
            "env_id": {
                "type": "string",
                "description": "Environment ID to check",
            },
        },
        "required": ["env_id"],
    },
}

TOOL_LIST_INSTALLED_POWERUPS = {
    "name": "list_installed_powerups",
    "description": "List all power-ups currently installed on an environment.",
    "input_schema": {
        "type": "object",
        "properties": {
            "env_id": {
                "type": "string",
                "description": "Environment ID",
            },
        },
        "required": ["env_id"],
    },
}

TOOL_LIST_AVAILABLE_POWERUPS = {
    "name": "list_available_powerups",
    "description": "List all power-ups available in the catalog with their requirements and descriptions.",
    "input_schema": {
        "type": "object",
        "properties": {},
        "required": [],
    },
}

TOOL_EXPLAIN_POLICY = {
    "name": "explain_policy",
    "description": "Explain the platform's policy rules for a specific action in plain language.",
    "input_schema": {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "description": "The action to explain policies for (e.g., install_powerup, upgrade_vm)",
            },
        },
        "required": ["action"],
    },
}


# ─── Schema groups per agent ───

POLICY_AGENT_TOOLS = [
    TOOL_READ_POLICY_RULES,
    TOOL_CALCULATE_RISK_SCORE,
    TOOL_CHECK_QUORUM,
]

PROVISIONING_AGENT_TOOLS = [
    TOOL_FREE_TIER_PRECHECK,
    TOOL_TERRAFORM_APPLY,
    TOOL_TERRAFORM_DESTROY,
    TOOL_FETCH_EXTERNAL_IP,
    TOOL_UPDATE_ENV,
]

POWERUP_AGENT_TOOLS = [
    TOOL_CHECK_COMPATIBILITY,
    TOOL_INSTALL_POWERUP,
    TOOL_UNINSTALL_POWERUP,
    TOOL_CONSUME_BUDGET,
]

UPGRADE_AGENT_TOOLS = [
    TOOL_UPGRADE_VM,
    TOOL_CONSUME_BUDGET,
    TOOL_UPDATE_ENV,
]

SUPPORT_CHATBOT_TOOLS = [
    TOOL_GET_ENVIRONMENT_STATUS,
    TOOL_LIST_INSTALLED_POWERUPS,
    TOOL_LIST_AVAILABLE_POWERUPS,
    TOOL_EXPLAIN_POLICY,
]


def get_tools_for_agent(agent_name: str) -> list[dict[str, Any]]:
    """Get the tool schemas for a given agent."""
    mapping = {
        "policy_evaluator": POLICY_AGENT_TOOLS,
        "vm_provisioner": PROVISIONING_AGENT_TOOLS,
        "powerup_installer": POWERUP_AGENT_TOOLS,
        "vm_upgrader": UPGRADE_AGENT_TOOLS,
        "support_chatbot": SUPPORT_CHATBOT_TOOLS,
    }
    return mapping.get(agent_name, [])
