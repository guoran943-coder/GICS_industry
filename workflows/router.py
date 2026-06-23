from .base import BaseWorkflow
from .software import SoftwareWorkflow
from .semiconductor import SemiconductorWorkflow
from .consumer import ConsumerWorkflow

# List of registered strategies
STRATEGIES = [
    SoftwareWorkflow,
    SemiconductorWorkflow,
    ConsumerWorkflow
]

def get_workflow_for_gics(gics_code: str) -> type:
    """
    Find the most specific workflow strategy matching the company's GICS code.
    """
    if not gics_code:
        return BaseWorkflow
        
    # Sort strategies by gics_prefix length descending to match the most specific prefix first
    sorted_strategies = sorted(STRATEGIES, key=lambda s: len(s.gics_prefix), reverse=True)
    
    for strategy in sorted_strategies:
        if gics_code.startswith(strategy.gics_prefix):
            return strategy
            
    return BaseWorkflow
