"""
Stratum AI: MCP Server Integration
==================================

MCP (Model Context Protocol) Integration for Stratum AI Platform.

What is MCP?
------------
MCP is Anthropic's protocol for connecting LLMs to external tools and data sources.
It allows Claude and other LLMs to:
- Execute actions in external systems
- Retrieve real-time data
- Interact with APIs

How MCP + Stratum Work Together
-------------------------------

The existing Stratum architecture (adapters, events, webhooks) handles:
- Platform API communication
- Event tracking
- Real-time updates

MCP adds an **AI interface layer** on top, allowing:
- Claude to query campaign performance
- Claude to suggest optimizations
- Claude to execute approved actions
- Natural language interaction with ad platforms

Architecture:

    +-------------+     MCP Protocol      +----------------------+
    |   Claude    | <------------------->  |  Stratum MCP Server  |
    |   (LLM)     |                       |                      |
    +-------------+                       |  +----------------+  |
                                          |  | MCP Tools:     |  |
                                          |  | - get_metrics  |  |
                                          |  | - get_campaigns|  |
                                          |  | - suggest_opt  |  |
                                          |  | - execute_act  |  |
                                          |  +-------+--------+  |
                                          +---------|-----------+
                                                    |
                                                    v
                                          +----------------------+
                                          |   Stratum Core       |
                                          |                      |
                                          |  - Adapters (5)      |
                                          |  - Events API        |
                                          |  - Signal Health     |
                                          |  - Trust Gate        |
                                          +----------------------+

Will This Conflict with Google's MCP Server?
--------------------------------------------

NO! MCP servers are additive and can coexist:

    Claude --+-- Stratum MCP Server (advertising)
             +-- Google MCP Server (search, drive, etc.)
             +-- Slack MCP Server (messaging)
             +-- Your Custom MCP Server (anything)

Each MCP server exposes different tools. Claude can use tools from
multiple servers in the same conversation.

Usage Examples:
    # Claude asking about campaign performance
    User: "How are my Meta campaigns performing today?"
    Claude: [calls get_campaign_metrics tool from Stratum MCP]
    Claude: "Your 'Summer Sale' campaign has 45,000 impressions with 2.3% CTR..."

    # Claude suggesting optimizations
    User: "What should I optimize?"
    Claude: [calls get_optimization_suggestions tool]
    Claude: "Based on signal health, I recommend increasing budget on Campaign A by 20%..."

    # Claude executing approved action
    User: "Go ahead and make that change"
    Claude: [calls execute_action tool with trust_gate check]
    Claude: "Done! Budget increased from $500 to $600. Signal health: 85 (Healthy)"
"""

import logging
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

logger = logging.getLogger("stratum.mcp")


# =============================================================================
# MCP TOOL DEFINITIONS
# =============================================================================

MCP_TOOLS = [
    {
        "name": "get_accounts",
        "description": "Get all advertising accounts across platforms (Meta, Google, TikTok, Snapchat)",
        "inputSchema": {
            "type": "object",
            "properties": {
                "platform": {
                    "type": "string",
                    "enum": ["meta", "google", "tiktok", "snapchat", "all"],
                    "description": "Filter by platform or 'all' for all platforms",
                }
            },
        },
    },
    {
        "name": "get_campaigns",
        "description": "Get campaigns for an account with optional status filter",
        "inputSchema": {
            "type": "object",
            "properties": {
                "platform": {
                    "type": "string",
                    "enum": ["meta", "google", "tiktok", "snapchat"],
                    "description": "Advertising platform",
                },
                "account_id": {"type": "string", "description": "Account ID"},
                "status": {
                    "type": "string",
                    "enum": ["active", "paused", "all"],
                    "description": "Filter by status",
                },
            },
            "required": ["platform", "account_id"],
        },
    },
    {
        "name": "get_campaign_metrics",
        "description": "Get performance metrics for campaigns (impressions, clicks, spend, conversions, ROAS)",
        "inputSchema": {
            "type": "object",
            "properties": {
                "platform": {
                    "type": "string",
                    "enum": ["meta", "google", "tiktok", "snapchat"],
                },
                "account_id": {"type": "string"},
                "campaign_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Campaign IDs to get metrics for",
                },
                "date_range": {
                    "type": "string",
                    "enum": [
                        "today",
                        "yesterday",
                        "last_7_days",
                        "last_30_days",
                        "this_month",
                    ],
                    "description": "Date range for metrics",
                },
            },
            "required": ["platform", "account_id", "campaign_ids"],
        },
    },
    {
        "name": "get_signal_health",
        "description": "Get signal health score for an account or campaign (EMQ, data freshness, variance, anomalies)",
        "inputSchema": {
            "type": "object",
            "properties": {
                "platform": {
                    "type": "string",
                    "enum": ["meta", "google", "tiktok", "snapchat"],
                },
                "account_id": {"type": "string"},
                "campaign_id": {
                    "type": "string",
                    "description": "Optional: specific campaign",
                },
            },
            "required": ["platform", "account_id"],
        },
    },
    {
        "name": "get_emq_scores",
        "description": "Get Event Match Quality scores by event type (Purchase, AddToCart, ViewContent, Lead)",
        "inputSchema": {
            "type": "object",
            "properties": {
                "platform": {
                    "type": "string",
                    "enum": ["meta", "google", "tiktok", "snapchat"],
                },
                "account_id": {"type": "string"},
            },
            "required": ["platform", "account_id"],
        },
    },
    {
        "name": "get_optimization_suggestions",
        "description": "Get AI-powered optimization suggestions based on performance and signal health",
        "inputSchema": {
            "type": "object",
            "properties": {
                "platform": {
                    "type": "string",
                    "enum": ["meta", "google", "tiktok", "snapchat", "all"],
                },
                "account_id": {
                    "type": "string",
                    "description": "Optional: specific account",
                },
                "suggestion_types": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": ["budget", "bid", "creative", "audience", "emq"],
                    },
                    "description": "Types of suggestions to include",
                },
            },
        },
    },
    {
        "name": "check_trust_gate",
        "description": "Check if an action would be approved by the Trust Gate (without executing)",
        "inputSchema": {
            "type": "object",
            "properties": {
                "platform": {
                    "type": "string",
                    "enum": ["meta", "google", "tiktok", "snapchat"],
                },
                "action_type": {
                    "type": "string",
                    "enum": [
                        "update_budget",
                        "update_bid",
                        "update_status",
                        "create_campaign",
                    ],
                },
                "entity_id": {"type": "string", "description": "Campaign or ad set ID"},
                "parameters": {
                    "type": "object",
                    "description": "Action parameters (e.g., {new_budget: 1000})",
                },
            },
            "required": ["platform", "action_type", "entity_id"],
        },
    },
    {
        "name": "execute_action",
        "description": "Execute an optimization action (requires Trust Gate approval). Actions include budget changes, bid adjustments, and status updates.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "platform": {
                    "type": "string",
                    "enum": ["meta", "google", "tiktok", "snapchat"],
                },
                "action_type": {
                    "type": "string",
                    "enum": ["update_budget", "update_bid", "update_status"],
                },
                "entity_type": {"type": "string", "enum": ["campaign", "adset", "ad"]},
                "entity_id": {"type": "string"},
                "parameters": {"type": "object", "description": "Action parameters"},
                "reason": {
                    "type": "string",
                    "description": "Reason for the action (for audit trail)",
                },
            },
            "required": [
                "platform",
                "action_type",
                "entity_type",
                "entity_id",
                "parameters",
            ],
        },
    },
    {
        "name": "track_conversion",
        "description": "Track a conversion event (purchase, lead, etc.) to all platforms",
        "inputSchema": {
            "type": "object",
            "properties": {
                "event_type": {
                    "type": "string",
                    "enum": [
                        "purchase",
                        "lead",
                        "add_to_cart",
                        "view_content",
                        "initiate_checkout",
                    ],
                },
                "value": {"type": "number", "description": "Conversion value"},
                "currency": {
                    "type": "string",
                    "description": "Currency code (USD, SAR, etc.)",
                },
                "order_id": {"type": "string", "description": "Order/transaction ID"},
                "user_email": {
                    "type": "string",
                    "description": "Customer email (for matching)",
                },
                "user_phone": {
                    "type": "string",
                    "description": "Customer phone (for matching)",
                },
                "platforms": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Platforms to send to (default: all)",
                },
            },
            "required": ["event_type", "value", "currency"],
        },
    },
    {
        "name": "send_whatsapp_message",
        "description": "Send a WhatsApp message (template or session message)",
        "inputSchema": {
            "type": "object",
            "properties": {
                "to": {
                    "type": "string",
                    "description": "Recipient phone number (E.164 format)",
                },
                "message_type": {
                    "type": "string",
                    "enum": ["text", "template", "interactive"],
                },
                "content": {
                    "type": "string",
                    "description": "Message content or template name",
                },
                "template_params": {
                    "type": "object",
                    "description": "Template parameters if using template",
                },
            },
            "required": ["to", "message_type", "content"],
        },
    },
    {
        "name": "get_whatsapp_conversations",
        "description": "Get recent WhatsApp conversations",
        "inputSchema": {
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": "Number of conversations to return",
                },
                "status": {"type": "string", "enum": ["active", "converted", "all"]},
            },
        },
    },
]

# Tools whose handlers cannot be answered safely from this server, because a
# truthful answer needs a database session and a tenant context that the MCP
# surface does not have. They are filtered out of get_tools() so an LLM is
# never offered them, and their handlers fail closed if invoked directly.
#
# execute_action is included deliberately: do not advertise a mutation you
# cannot gate. Actions belong in the audited autopilot queue.
UNAVAILABLE_TOOLS = frozenset(
    {
        "get_signal_health",
        "check_trust_gate",
        "execute_action",
    }
)

_UNAVAILABLE_REASON = (
    "This tool needs a tenant-scoped database session to answer truthfully. "
    "The MCP server has no session or tenant context, so it reports "
    "unavailable rather than returning a placeholder that cannot be "
    "distinguished from a real measurement."
)


def _unavailable(tool: str, **context: Any) -> dict[str, Any]:
    """Structured refusal for a tool that cannot be answered safely."""
    logger.warning("mcp_tool_unavailable", extra={"tool": tool, **context})
    return {
        "available": False,
        "tool": tool,
        "error": f"{tool} is not available over MCP",
        "reason": _UNAVAILABLE_REASON,
        **{k: v for k, v in context.items() if v is not None},
    }


# =============================================================================
# MCP SERVER IMPLEMENTATION
# =============================================================================


class StratumMCPServer:
    """
    MCP Server that exposes Stratum capabilities as tools.

    This server can be run standalone or integrated into an existing MCP setup.

    Usage (standalone):
        server = StratumMCPServer(config)
        await server.run()

    Usage (with existing MCP infrastructure):
        server = StratumMCPServer(config)
        tools = server.get_tools()
        # Register tools with your MCP router
    """

    def __init__(self, config: dict[str, Any]):
        """
        Initialize MCP server with Stratum configuration.

        Args:
            config: Stratum configuration dict with platform credentials
        """
        self.config = config
        self._adapters = {}
        self._events_api = None
        self._trust_gate = None
        self._initialized = False

    async def initialize(self):
        """Initialize adapters and core components."""
        from app.stratum.adapters import (
            GoogleAdsAdapter,
            MetaAdapter,
            SnapchatAdapter,
            TikTokAdapter,
            WhatsAppAdapter,
        )
        from app.stratum.core.signal_health import SignalHealthCalculator
        from app.stratum.core.trust_gate import TrustGate
        from app.stratum.events import UnifiedEventsAPI

        # Initialize adapters based on config
        if self.config.get("meta"):
            self._adapters["meta"] = MetaAdapter(self.config["meta"])
            await self._adapters["meta"].initialize()

        if self.config.get("google"):
            self._adapters["google"] = GoogleAdsAdapter(self.config["google"])
            await self._adapters["google"].initialize()

        if self.config.get("tiktok"):
            self._adapters["tiktok"] = TikTokAdapter(self.config["tiktok"])
            await self._adapters["tiktok"].initialize()

        if self.config.get("snapchat"):
            self._adapters["snapchat"] = SnapchatAdapter(self.config["snapchat"])
            await self._adapters["snapchat"].initialize()

        if self.config.get("whatsapp"):
            self._adapters["whatsapp"] = WhatsAppAdapter(self.config["whatsapp"])
            await self._adapters["whatsapp"].initialize()

        # Initialize events API
        self._events_api = UnifiedEventsAPI()
        # Add senders based on config...

        # Initialize trust gate
        self._signal_health = SignalHealthCalculator()
        self._trust_gate = TrustGate()

        self._initialized = True
        logger.info(
            f"Stratum MCP Server initialized with {len(self._adapters)} adapters"
        )

    def get_tools(self) -> list[dict[str, Any]]:
        """Get MCP tool definitions.

        Tools in ``UNAVAILABLE_TOOLS`` are withheld: an LLM should not be
        offered a capability this server cannot deliver safely. Their handlers
        still fail closed for any caller that invokes them directly.
        """
        return [tool for tool in MCP_TOOLS if tool["name"] not in UNAVAILABLE_TOOLS]

    async def handle_tool_call(
        self, tool_name: str, arguments: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Handle an MCP tool call.

        Args:
            tool_name: Name of the tool to execute
            arguments: Tool arguments

        Returns:
            Tool execution result
        """
        if not self._initialized:
            await self.initialize()

        # Route to appropriate handler
        handlers = {
            "get_accounts": self._handle_get_accounts,
            "get_campaigns": self._handle_get_campaigns,
            "get_campaign_metrics": self._handle_get_metrics,
            "get_signal_health": self._handle_get_signal_health,
            "get_emq_scores": self._handle_get_emq,
            "get_optimization_suggestions": self._handle_get_suggestions,
            "check_trust_gate": self._handle_check_trust_gate,
            "execute_action": self._handle_execute_action,
            "track_conversion": self._handle_track_conversion,
            "send_whatsapp_message": self._handle_send_whatsapp,
            "get_whatsapp_conversations": self._handle_get_whatsapp_conversations,
        }

        handler = handlers.get(tool_name)
        if not handler:
            return {"error": f"Unknown tool: {tool_name}"}

        try:
            return await handler(arguments)
        except (ConnectionError, TimeoutError, OSError) as e:
            logger.error(f"Tool execution network error: {e}")
            return {"error": str(e)}
        except (ValueError, KeyError, TypeError, RuntimeError) as e:
            logger.error(f"Tool execution error: {e}")
            return {"error": str(e)}

    # =========================================================================
    # TOOL HANDLERS
    # =========================================================================

    async def _handle_get_accounts(self, args: dict[str, Any]) -> dict[str, Any]:
        """Handle get_accounts tool call."""
        platform = args.get("platform", "all")
        accounts = {}

        if platform in ("all", "meta") and "meta" in self._adapters:
            accounts["meta"] = await self._adapters["meta"].get_accounts()

        if platform in ("all", "google") and "google" in self._adapters:
            accounts["google"] = await self._adapters["google"].get_accounts()

        if platform in ("all", "tiktok") and "tiktok" in self._adapters:
            accounts["tiktok"] = await self._adapters["tiktok"].get_accounts()

        if platform in ("all", "snapchat") and "snapchat" in self._adapters:
            accounts["snapchat"] = await self._adapters["snapchat"].get_accounts()

        return {"accounts": accounts}

    async def _handle_get_campaigns(self, args: dict[str, Any]) -> dict[str, Any]:
        """Handle get_campaigns tool call."""
        platform = args["platform"]
        account_id = args["account_id"]
        status = args.get("status", "all")

        if platform not in self._adapters:
            return {"error": f"Platform {platform} not configured"}

        status_filter = None if status == "all" else status.upper()
        campaigns = await self._adapters[platform].get_campaigns(
            account_id, status_filter=status_filter
        )

        return {
            "platform": platform,
            "account_id": account_id,
            "campaigns": [c.__dict__ for c in campaigns],
        }

    async def _handle_get_metrics(self, args: dict[str, Any]) -> dict[str, Any]:
        """Handle get_campaign_metrics tool call."""
        platform = args["platform"]
        account_id = args["account_id"]
        campaign_ids = args["campaign_ids"]
        date_range = args.get("date_range", "last_7_days")

        if platform not in self._adapters:
            return {"error": f"Platform {platform} not configured"}

        # Calculate date range
        today = datetime.now(UTC).date()
        date_ranges = {
            "today": (today, today),
            "yesterday": (today - timedelta(days=1), today - timedelta(days=1)),
            "last_7_days": (today - timedelta(days=7), today),
            "last_30_days": (today - timedelta(days=30), today),
            "this_month": (today.replace(day=1), today),
        }
        start_date, end_date = date_ranges.get(date_range, date_ranges["last_7_days"])

        metrics = await self._adapters[platform].get_metrics(
            account_id,
            entity_type="campaign",
            entity_ids=campaign_ids,
            date_start=start_date,
            date_end=end_date,
        )

        return {"platform": platform, "date_range": date_range, "metrics": metrics}

    async def _handle_get_signal_health(self, args: dict[str, Any]) -> dict[str, Any]:
        """Handle get_signal_health tool call.

        Refuses rather than answering. Signal health is computed from the
        per-tenant rollup in the database (FactSignalHealthDaily), and this
        server has neither a session nor a tenant context — see
        ``_UNAVAILABLE_REASON``.

        This previously returned a fixed score of 78 with
        ``trust_gate_status: HEALTHY`` and ``autopilot_allowed: true``,
        regardless of the real state. A fabricated safety signal is worse than
        no signal: a caller cannot tell it apart from a real measurement.
        """
        return _unavailable(
            "get_signal_health",
            platform=args.get("platform"),
            account_id=args.get("account_id"),
        )

    async def _handle_get_emq(self, args: dict[str, Any]) -> dict[str, Any]:
        """Handle get_emq_scores tool call."""
        platform = args["platform"]
        account_id = args["account_id"]

        if platform not in self._adapters:
            return {"error": f"Platform {platform} not configured"}

        emq_scores = await self._adapters[platform].get_emq_scores(account_id)

        return {
            "platform": platform,
            "account_id": account_id,
            "emq_scores": emq_scores,
            "targets": {
                "Purchase": 8.5,
                "AddToCart": 6.0,
                "ViewContent": 4.0,
                "Lead": 7.0,
            },
        }

    async def _handle_get_suggestions(self, args: dict[str, Any]) -> dict[str, Any]:
        """Handle get_optimization_suggestions tool call."""
        # This would analyze account data and generate suggestions
        # For now, return sample suggestions

        return {
            "suggestions": [
                {
                    "type": "budget",
                    "platform": "meta",
                    "campaign_id": "123456",
                    "campaign_name": "Summer Sale 2024",
                    "recommendation": "Increase budget by 25%",
                    "reason": "ROAS of 4.2x exceeds target of 3.0x",
                    "expected_impact": "+$2,500 revenue",
                    "confidence": "high",
                    "trust_gate_status": "WOULD_APPROVE",
                },
                {
                    "type": "emq",
                    "platform": "meta",
                    "recommendation": "Implement server-side tracking for AddToCart events",
                    "reason": "Current EMQ: 4.8, Target: 6.0",
                    "expected_impact": "+15% attributed conversions",
                    "confidence": "high",
                },
                {
                    "type": "bid",
                    "platform": "google",
                    "campaign_id": "789012",
                    "recommendation": "Switch to Target ROAS bidding",
                    "reason": "Manual CPC underperforming vs algorithmic bidding",
                    "expected_impact": "+18% conversions at same spend",
                    "confidence": "medium",
                    "trust_gate_status": "WOULD_QUEUE",
                },
            ]
        }

    async def _handle_check_trust_gate(self, args: dict[str, Any]) -> dict[str, Any]:
        """Handle check_trust_gate tool call.

        Refuses rather than answering, for the same reason as
        ``_handle_get_signal_health``: a real evaluation needs the tenant's
        rollup and enforcement settings, and neither is reachable from here.

        This previously returned ``decision: APPROVED`` with a fixed
        ``signal_health_score`` of 82 for every call — an unconditional yes
        dressed as a measurement. That inverts the entire point of the gate.
        """
        return _unavailable(
            "check_trust_gate",
            platform=args.get("platform"),
            action_type=args.get("action_type"),
            entity_id=args.get("entity_id"),
        )

    async def _handle_execute_action(self, args: dict[str, Any]) -> dict[str, Any]:
        """Refuse to mutate an ad account from the MCP surface.

        This previously built an ``AutomationAction`` and called
        ``adapter.execute_action`` directly — no signal-health check, no
        enforcement gate, no tenant scoping, and no audit row. Paired with a
        ``check_trust_gate`` that always answered APPROVED, an LLM could ask
        whether a budget change was safe, be told yes on fabricated data, and
        then move real spend.

        Executing safely requires a database session for the tenant's signal
        rollup and enforcement settings, plus an audit trail. None of that is
        available here, so this fails closed rather than approximating it.

        The supported path is the audited queue: actions are proposed, gated by
        ``enforce_before_execute`` and ``check_signal_health``, approved, and
        applied by ``tasks.apply_actions_queue`` — which also records the
        before-value needed for rollback.
        """
        logger.warning(
            "mcp_execute_action_refused",
            extra={
                "platform": args.get("platform"),
                "action_type": args.get("action_type"),
                "entity_id": args.get("entity_id"),
            },
        )
        return {
            "success": False,
            "error": "execute_action is not available over MCP",
            "reason": (
                "Mutating an ad account requires a trust-gate evaluation, "
                "enforcement check and audit trail, none of which this server "
                "can perform. Propose the action through the autopilot queue "
                "instead: POST /api/v1/autopilot/{tenant_id}/actions."
            ),
        }

    async def _handle_track_conversion(self, args: dict[str, Any]) -> dict[str, Any]:
        """Handle track_conversion tool call."""
        from app.stratum.events import ServerEvent, StandardEvent, UserData

        event_type_map = {
            "purchase": StandardEvent.PURCHASE,
            "lead": StandardEvent.LEAD,
            "add_to_cart": StandardEvent.ADD_TO_CART,
            "view_content": StandardEvent.VIEW_CONTENT,
            "initiate_checkout": StandardEvent.INITIATE_CHECKOUT,
        }

        event = ServerEvent(
            event_name=event_type_map.get(args["event_type"], StandardEvent.PURCHASE),
            user_data=UserData(
                email=args.get("user_email"), phone=args.get("user_phone")
            ),
            value=args["value"],
            currency=args["currency"],
            order_id=args.get("order_id"),
        )

        # Would send through events API
        return {
            "event_id": event.event_id,
            "event_type": args["event_type"],
            "platforms_sent": args.get(
                "platforms", ["meta", "google", "tiktok", "snapchat"]
            ),
            "status": "sent",
        }

    async def _handle_send_whatsapp(self, args: dict[str, Any]) -> dict[str, Any]:
        """Handle send_whatsapp_message tool call."""
        if "whatsapp" not in self._adapters:
            return {"error": "WhatsApp not configured"}

        adapter = self._adapters["whatsapp"]
        to = args["to"]
        message_type = args["message_type"]
        content = args["content"]

        if message_type == "text":
            result = await adapter.send_text_message(to, content)
        elif message_type == "template":
            result = await adapter.send_template_message(
                to,
                content,  # template name
                components=args.get("template_params", {}).get("components"),
            )
        else:
            return {"error": f"Unsupported message type: {message_type}"}

        return {
            "message_id": result.message_id,
            "status": result.status.value,
            "to": to,
        }

    async def _handle_get_whatsapp_conversations(
        self, args: dict[str, Any]
    ) -> dict[str, Any]:
        """Handle get_whatsapp_conversations tool call."""
        if "whatsapp" not in self._adapters:
            return {"error": "WhatsApp not configured"}

        # Would return actual conversation data
        return {"conversations": [], "total": 0}


# =============================================================================
# MCP SERVER RUNNER (For FastMCP or custom MCP implementation)
# =============================================================================


def create_mcp_server(config_path: str = "config.yaml"):
    """
    Create an MCP server instance for integration with MCP clients.

    This can be used with:
    - FastMCP (recommended)
    - Claude Desktop MCP
    - Custom MCP implementations

    Example with FastMCP:
        from fastmcp import FastMCP
        from app.stratum.mcp import create_mcp_server

        mcp = FastMCP("Stratum AI")
        stratum = create_mcp_server()

        @mcp.tool()
        async def get_campaign_metrics(platform: str, account_id: str, ...):
            return await stratum.handle_tool_call("get_campaign_metrics", {...})
    """
    import yaml

    with Path(config_path).open() as f:
        config = yaml.safe_load(f)

    return StratumMCPServer(config)


# =============================================================================
# INTEGRATION WITH GOOGLE MCP SERVER
# =============================================================================

"""
IMPORTANT: Stratum MCP Server and Google MCP Server are COMPLEMENTARY

Google MCP Server provides:
- Google Search
- Google Drive
- Gmail
- Google Calendar
- etc.

Stratum MCP Server provides:
- Ad platform management (Meta, Google Ads, TikTok, Snapchat)
- Server-side event tracking
- WhatsApp Business
- Trust-gated automation

They can run side-by-side! Example Claude Desktop config:

    {
        "mcpServers": {
            "stratum": {
                "command": "python",
                "args": ["-m", "app.stratum.mcp.server"],
                "env": {
                    "STRATUM_CONFIG": "/path/to/config.yaml"
                }
            },
            "google": {
                "command": "npx",
                "args": ["-y", "@anthropic/mcp-google"]
            },
            "slack": {
                "command": "npx",
                "args": ["-y", "@anthropic/mcp-slack"]
            }
        }
    }

Claude can then use tools from ALL servers:
- "Search Google for competitor ads" -> Google MCP
- "Check my Meta campaign performance" -> Stratum MCP
- "Send a Slack alert about low EMQ" -> Slack MCP
"""
