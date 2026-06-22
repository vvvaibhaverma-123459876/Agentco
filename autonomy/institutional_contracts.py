"""
Institutional Contracts & Interdependencies

Defines explicit contracts between institutions.
Institutions negotiate based on:
- What they need (inputs)
- What they provide (outputs)
- How well they're performing (metrics)
- What resources they require
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Callable
from enum import Enum
from datetime import datetime


class ContractStatus(Enum):
    PROPOSED = "proposed"
    NEGOTIATING = "negotiating"
    ACTIVE = "active"
    EXPIRED = "expired"
    FAILED = "failed"


@dataclass
class ServiceRequirement:
    """What an institution needs from another."""
    name: str
    description: str
    provider: str  # Institution that provides this
    required: bool = True  # Can work without it?
    frequency: str = "continuous"  # How often needed
    minimum_quality: float = 0.5  # Minimum acceptable quality (0-1)


@dataclass
class ServiceProvision:
    """What an institution provides to others."""
    name: str
    description: str
    quality: float = 0.5  # Current quality (0-1)
    availability: float = 1.0  # How available (0-1)
    throughput: int = 0  # Units provided per cycle
    cost: float = 0.0  # Resource cost per unit


@dataclass
class PerformanceMetric:
    """How well an institution is performing."""
    name: str
    description: str
    unit: str
    current_value: float = 0.0
    historical_values: List[float] = field(default_factory=list)
    target_value: float = 1.0


class InstitutionalContract:
    """
    A contract between two institutions defining mutual obligations.
    """

    def __init__(self, institution_id: str, provider_id: str,
                 service_name: str, description: str):
        self.contract_id = f"{institution_id}←{provider_id}:{service_name}"
        self.institution_id = institution_id  # Consumer
        self.provider_id = provider_id
        self.service_name = service_name
        self.description = description
        self.status = ContractStatus.PROPOSED

        self.agreed_quality_level = 0.5  # Negotiated quality target
        self.agreed_frequency = "continuous"
        self.agreed_cost = 0.0  # Resource cost agreed upon

        self.performance_history: List[Dict] = []
        self.negotiation_history: List[Dict] = []
        self.breach_count = 0

        self.created_at = datetime.now()
        self.last_updated = datetime.now()

    def propose(self, required: bool = True, quality_target: float = 0.7):
        """Propose a contract."""
        self.status = ContractStatus.PROPOSED
        self.agreed_quality_level = quality_target

    def negotiate(self, provider_counter: Dict) -> bool:
        """
        Negotiate contract terms.
        Provider counters with their constraints.

        Returns: True if agreement reached
        """
        record = {
            'timestamp': datetime.now().isoformat(),
            'provider_counter': provider_counter
        }
        self.negotiation_history.append(record)

        # Simple negotiation: if provider can meet quality target, accept
        provider_quality = provider_counter.get('quality', 0.5)
        provider_cost = provider_counter.get('cost', 0.0)

        if provider_quality >= self.agreed_quality_level * 0.9:
            self.status = ContractStatus.ACTIVE
            self.agreed_cost = provider_cost
            return True

        return False

    def record_delivery(self, actual_quality: float, cost: float):
        """Record delivery of service."""
        record = {
            'timestamp': datetime.now().isoformat(),
            'agreed_quality': self.agreed_quality_level,
            'actual_quality': actual_quality,
            'agreed_cost': self.agreed_cost,
            'actual_cost': cost,
            'met_sla': actual_quality >= self.agreed_quality_level * 0.9
        }
        self.performance_history.append(record)

        if not record['met_sla']:
            self.breach_count += 1

        self.last_updated = datetime.now()

    def get_status(self) -> Dict:
        """Get contract status."""
        compliance_rate = 0.0
        if self.performance_history:
            met = sum(1 for p in self.performance_history if p['met_sla'])
            compliance_rate = met / len(self.performance_history)

        return {
            'contract_id': self.contract_id,
            'status': self.status.value,
            'institution': self.institution_id,
            'provider': self.provider_id,
            'service': self.service_name,
            'agreed_quality': self.agreed_quality_level,
            'compliance_rate': compliance_rate,
            'breaches': self.breach_count,
            'deliveries': len(self.performance_history)
        }


class InstitutionalCouncil:
    """
    Manages contracts between institutions.
    Handles negotiation and resource allocation.
    """

    def __init__(self):
        self.institutions: Dict[str, 'Institution'] = {}
        self.contracts: Dict[str, InstitutionalContract] = {}
        self.negotiation_queue: List[InstitutionalContract] = []
        self.resource_pool = 1000.0  # Total resources available

    def register_institution(self, institution_id: str,
                           services_provided: Dict[str, ServiceProvision],
                           services_needed: Dict[str, ServiceRequirement]):
        """Register an institution with the council."""
        self.institutions[institution_id] = {
            'id': institution_id,
            'provides': services_provided,
            'needs': services_needed,
            'performance': {}
        }

    def propose_contract(self, consumer_id: str, provider_id: str,
                        service_name: str, description: str) -> InstitutionalContract:
        """Propose a contract between institutions."""
        contract = InstitutionalContract(consumer_id, provider_id, service_name, description)
        self.contracts[contract.contract_id] = contract
        self.negotiation_queue.append(contract)
        return contract

    def process_negotiations(self) -> List[str]:
        """
        Process pending negotiations.
        Returns list of newly activated contracts.
        """
        activated = []

        for contract in self.negotiation_queue[:]:
            if contract.status == ContractStatus.PROPOSED:
                provider = self.institutions.get(contract.provider_id)
                if provider:
                    # Provider proposes their terms
                    service = provider['provides'].get(contract.service_name)
                    if service:
                        counter = {
                            'quality': service.quality,
                            'cost': service.cost,
                            'availability': service.availability
                        }

                        if contract.negotiate(counter):
                            activated.append(contract.contract_id)
                            self.negotiation_queue.remove(contract)

        return activated

    def allocate_resources(self):
        """
        Allocate resources based on contract compliance and institutional performance.
        Better-performing institutions get more resources.
        """
        performance_scores = {}

        # Calculate performance score for each institution
        for inst_id in self.institutions:
            contracts = [c for c in self.contracts.values()
                        if c.provider_id == inst_id]

            if not contracts:
                performance_scores[inst_id] = 0.5
            else:
                compliance_rates = []
                for contract in contracts:
                    status = contract.get_status()
                    compliance_rates.append(status['compliance_rate'])

                avg_compliance = sum(compliance_rates) / len(compliance_rates) if compliance_rates else 0.5
                performance_scores[inst_id] = avg_compliance

        # Allocate resources proportional to performance
        total_score = sum(performance_scores.values())
        if total_score > 0:
            for inst_id, score in performance_scores.items():
                allocated = (score / total_score) * self.resource_pool
                self.institutions[inst_id]['allocated_resources'] = allocated

    def get_council_status(self) -> Dict:
        """Get status of all contracts and institutions."""
        contracts_by_status = {}
        for contract in self.contracts.values():
            status = contract.status.value
            if status not in contracts_by_status:
                contracts_by_status[status] = []
            contracts_by_status[status].append(contract.get_status())

        institution_statuses = {}
        for inst_id, inst in self.institutions.items():
            contracts = [c for c in self.contracts.values()
                        if c.provider_id == inst_id or c.institution_id == inst_id]
            institution_statuses[inst_id] = {
                'contracts_as_provider': len([c for c in contracts if c.provider_id == inst_id]),
                'contracts_as_consumer': len([c for c in contracts if c.institution_id == inst_id]),
                'allocated_resources': inst.get('allocated_resources', 0)
            }

        return {
            'total_contracts': len(self.contracts),
            'contracts_by_status': contracts_by_status,
            'institutions': institution_statuses,
            'total_resources': self.resource_pool
        }


# Global instance
_council_instance = None

def get_council() -> InstitutionalCouncil:
    """Get the global institutional council."""
    global _council_instance
    if _council_instance is None:
        _council_instance = InstitutionalCouncil()
    return _council_instance
