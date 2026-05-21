"""Master Infrastructure Bridge — correlates Doris + Saone + Grafana."""

from .bridge import MasterBridge, get_master_bridge

__all__ = ["MasterBridge", "get_master_bridge"]
